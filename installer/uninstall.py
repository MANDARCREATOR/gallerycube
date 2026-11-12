"""
Uninstall Program for Gallery Cube 🧊
Publisher: rmscube
Cleans up shortcuts, file associations in Windows Registry, and removes installed files.
"""
import sys
import os
import winreg
import ctypes
import subprocess
import tkinter as tk
from tkinter import messagebox

ALL_EXTENSIONS = [
    ".heic", ".heif", ".hif", ".jpg", ".jpeg", ".jpe", ".jfif",
    ".png", ".apng", ".webp", ".bmp", ".dib", ".tif", ".tiff",
    ".gif", ".ico", ".avif", ".tga", ".dng", ".psd",
    ".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".3gp"
]


def remove_registry_tree(root, subkey):
    try:
        hkey = winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS)
    except FileNotFoundError:
        return
    except PermissionError:
        return

    while True:
        try:
            sub = winreg.EnumKey(hkey, 0)
            remove_registry_tree(root, f"{subkey}\\{sub}")
        except OSError:
            break
    winreg.CloseKey(hkey)
    try:
        winreg.DeleteKey(root, subkey)
    except OSError:
        pass


def get_desktop_dir() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
            val, _ = winreg.QueryValueEx(k, "Desktop")
            expanded = os.path.expandvars(val)
            if os.path.exists(expanded):
                return expanded
    except Exception:
        pass
    p = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    if os.path.exists(p):
        return p
    return os.path.expanduser("~/Desktop")


def run_uninstaller():
    root = tk.Tk()
    root.withdraw()

    confirm = messagebox.askyesno(
        "Uninstall Gallery Cube",
        "Are you sure you want to completely remove Gallery Cube 🧊\nand all its components from your computer?",
        icon="warning"
    )
    if not confirm:
        return

    # 1. Kill any active GalleryCube process
    try:
        subprocess.run(["taskkill", "/F", "/IM", "GalleryCube.exe"], capture_output=True)
    except Exception:
        pass

    # Determine install directory
    install_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

    # Unregister WIC HEIC shell extension
    wic_dll = os.path.join(install_dir, "wic_heic.dll")
    if os.path.exists(wic_dll):
        try:
            subprocess.run(["regsvr32.exe", "/u", "/s", wic_dll], capture_output=True, timeout=10)
        except Exception:
            pass

    # 2. Remove Desktop shortcut
    user_desktop = os.path.join(get_desktop_dir(), "Gallery Cube.lnk")
    if os.path.exists(user_desktop):
        try:
            os.remove(user_desktop)
        except Exception:
            pass

    # 3. Remove Start Menu shortcuts
    appdata = os.environ.get("APPDATA", "")
    start_menu_folder = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Gallery Cube")
    if os.path.exists(start_menu_folder):
        try:
            for f in os.listdir(start_menu_folder):
                os.remove(os.path.join(start_menu_folder, f))
            os.rmdir(start_menu_folder)
        except Exception:
            pass

    # 4. Remove File Associations from HKCU
    for ext in ALL_EXTENSIONS:
        # Check if default was GalleryCube.Media
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}", 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(k, "")
            winreg.CloseKey(k)
            if val == "GalleryCube.Media":
                k_w = winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}", 0, winreg.KEY_WRITE)
                winreg.DeleteValue(k_w, "")
                winreg.CloseKey(k_w)
        except Exception:
            pass

        # Remove from OpenWithProgids
        try:
            ow = winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}\\OpenWithProgids", 0, winreg.KEY_WRITE)
            winreg.DeleteValue(ow, "GalleryCube.Media")
            winreg.CloseKey(ow)
        except Exception:
            pass

    remove_registry_tree(winreg.HKEY_CURRENT_USER, r"Software\Classes\GalleryCube.Media")
    remove_registry_tree(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\GalleryCube")

    # 5. Notify Windows Shell of association refresh
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except Exception:
        pass

    # 6. Schedule self-deletion of installation directory
    cmd = f'ping 127.0.0.1 -n 3 > nul & rmdir /s /q "{install_dir}"'
    subprocess.Popen(cmd, shell=True, creationflags=0x08000000)

    messagebox.showinfo(
        "Uninstall Complete",
        "Gallery Cube has been successfully removed from your computer.\n\nThank you for using Gallery Cube by rmscube!"
    )


if __name__ == "__main__":
    run_uninstaller()

