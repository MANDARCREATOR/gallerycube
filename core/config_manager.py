"""
Configuration & Windows File Association Manager for Gallery Cube.
Handles first-run detection, config persistence, and HKCU Windows file association registration.
"""
import os
import sys
import json
import winreg
import ctypes
from typing import List, Tuple, Dict, Any

CONFIG_FILE_NAME = "config.json"


def get_config_path() -> str:
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(app_dir, CONFIG_FILE_NAME)


def load_config() -> Dict[str, Any]:
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"first_run_completed": False, "associated_extensions": []}


def save_config(cfg: Dict[str, Any]):
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print("Config save error:", e)


def is_first_run() -> bool:
    cfg = load_config()
    return not cfg.get("first_run_completed", False)


def mark_first_run_done(extensions: List[str]):
    cfg = load_config()
    cfg["first_run_completed"] = True
    cfg["associated_extensions"] = extensions
    save_config(cfg)


def register_file_associations(extensions: List[str]) -> Tuple[int, str]:
    """
    Registers the specified file extensions in HKCU so double-clicking
    in Windows File Explorer automatically opens Gallery Cube.
    Does NOT require administrator privileges.
    """
    try:
        # Determine launch command (pythonw.exe main.py "%1" or GalleryCube.exe "%1")
        if getattr(sys, "frozen", False):
            # Running as compiled PyInstaller executable
            exe_path = sys.executable
            cmd = f'"{exe_path}" "%1"'
            icon_path = f"{exe_path},0"
        else:
            # Running as Python script
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            main_py = os.path.join(app_dir, "main.py")
            
            # Prefer pythonw.exe so no console pops up
            python_exe = sys.executable
            python_dir = os.path.dirname(python_exe)
            pythonw = os.path.join(python_dir, "pythonw.exe")
            target_python = pythonw if os.path.exists(pythonw) else python_exe

            cmd = f'"{target_python}" "{main_py}" "%1"'
            icon_path = f"{target_python},0"

        # 1. Create ProgID: GalleryCube.Media with ShellEx Thumbnail Providers
        PHOTO_THUMB_CLSID = "{C7657C4A-9F68-40fa-A4DF-96BC08EB3551}"
        EXTRACT_IMAGE_CLSID = "{3F30C968-480A-4C6C-862D-EFC0897BB84B}"

        progid_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\GalleryCube.Media")
        winreg.SetValueEx(progid_key, "", 0, winreg.REG_SZ, "Gallery Cube Media")
        winreg.SetValueEx(progid_key, "PerceivedType", 0, winreg.REG_SZ, "image")
        winreg.CloseKey(progid_key)

        sx_thumb = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\GalleryCube.Media\ShellEx\{e357fccd-a995-4576-b01f-234630154e96}")
        winreg.SetValueEx(sx_thumb, "", 0, winreg.REG_SZ, PHOTO_THUMB_CLSID)
        winreg.CloseKey(sx_thumb)

        sx_extract = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\GalleryCube.Media\ShellEx\{BB2E617C-0920-11d1-9A0B-00C04FC2D6C1}")
        winreg.SetValueEx(sx_extract, "", 0, winreg.REG_SZ, EXTRACT_IMAGE_CLSID)
        winreg.CloseKey(sx_extract)

        icon_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\GalleryCube.Media\DefaultIcon")
        winreg.SetValueEx(icon_key, "", 0, winreg.REG_SZ, icon_path)
        winreg.CloseKey(icon_key)

        shell_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\GalleryCube.Media\shell\open\command")
        winreg.SetValueEx(shell_key, "", 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(shell_key)

        # 2. Register each selected extension
        success_count = 0
        for ext in extensions:
            ext_clean = ext.lower().strip()
            if not ext_clean.startswith("."):
                ext_clean = f".{ext_clean}"

            # Set default ProgID & PerceivedType
            ext_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext_clean}")
            winreg.SetValueEx(ext_key, "", 0, winreg.REG_SZ, "GalleryCube.Media")
            winreg.SetValueEx(ext_key, "PerceivedType", 0, winreg.REG_SZ, "image")
            winreg.CloseKey(ext_key)

            # Preserve thumbnail provider on the extension itself
            ext_thumb = winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext_clean}\\ShellEx\\{{e357fccd-a995-4576-b01f-234630154e96}}")
            winreg.SetValueEx(ext_thumb, "", 0, winreg.REG_SZ, PHOTO_THUMB_CLSID)
            winreg.CloseKey(ext_thumb)

            # Register in OpenWithProgids
            ow_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext_clean}\\OpenWithProgids")
            winreg.SetValueEx(ow_key, "GalleryCube.Media", 0, winreg.REG_NONE, b"")
            winreg.CloseKey(ow_key)

            success_count += 1

        # 3. Notify Windows Shell of association change
        # SHCNE_ASSOCCHANGED = 0x08000000, SHCNF_IDLIST = 0
        try:
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
        except Exception:
            pass

        return success_count, "Successfully registered associations"
    except Exception as e:
        return 0, str(e)

