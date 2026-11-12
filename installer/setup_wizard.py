"""
Windows Setup Wizard for Gallery Cube 🧊.
Universal Media Studio for Photos and Videos.
Publisher: rmscube

Installs Gallery Cube to %LOCALAPPDATA%\\Programs\\GalleryCube,
creates Desktop and Start Menu shortcuts, registers Windows file associations,
and adds entry to Windows Installed Apps with an Uninstaller.
"""
import sys
import os
import shutil
import zipfile
import winreg
import ctypes
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_NAME = "Gallery Cube"
PUBLISHER = "rmscube"
VERSION = "1.0.0"

PHOTO_EXTS = [
    ".heic", ".heif", ".hif", ".jpg", ".jpeg", ".jpe", ".jfif",
    ".png", ".apng", ".webp", ".bmp", ".dib", ".tif", ".tiff",
    ".gif", ".ico", ".avif", ".tga", ".dng", ".psd"
]

VIDEO_EXTS = [
    ".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".3gp"
]


def get_default_install_dir() -> str:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        local_app_data = os.path.expanduser(r"~\AppData\Local")
    return os.path.join(local_app_data, "Programs", "GalleryCube")


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


def get_payload_path() -> str:
    # Check PyInstaller bundle temp path
    if hasattr(sys, "_MEIPASS"):
        p = os.path.join(sys._MEIPASS, "payload.zip")
        if os.path.exists(p):
            return p
    # Check relative to script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(script_dir, "payload.zip")
    if os.path.exists(p):
        return p
    # Check parent dir
    p = os.path.join(os.path.dirname(script_dir), "installer", "payload.zip")
    if os.path.exists(p):
        return p
    return ""


def create_windows_shortcut(target_exe: str, shortcut_path: str, icon_path: str, description: str):
    """Creates a Windows .lnk shortcut using powershell / WScript.Shell without extra dependencies."""
    ps_cmd = (
        f"$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{shortcut_path}'); "
        f"$s.TargetPath = '{target_exe}'; "
        f"$s.IconLocation = '{icon_path},0'; "
        f"$s.Description = '{description}'; "
        f"$s.Save()"
    )
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True)


def register_associations(install_dir: str, photo: bool, video: bool):
    exe_path = os.path.join(install_dir, "GalleryCube.exe")
    cmd = f'"{exe_path}" "%1"'
    icon_path = f"{exe_path},0"

    # 1. Create ProgID: GalleryCube.Media
    PHOTO_THUMB_CLSID = "{C7657C4A-9F68-40fa-A4DF-96BC08EB3551}"
    EXTRACT_IMAGE_CLSID = "{3F30C968-480A-4C6C-862D-EFC0897BB84B}"

    progid_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\GalleryCube.Media")
    winreg.SetValueEx(progid_key, "", 0, winreg.REG_SZ, "Gallery Cube Media")
    winreg.SetValueEx(progid_key, "PerceivedType", 0, winreg.REG_SZ, "image")
    winreg.SetValueEx(progid_key, "Treatment", 0, winreg.REG_DWORD, 2)
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

    target_exts = []
    if photo:
        target_exts.extend(PHOTO_EXTS)
    if video:
        target_exts.extend(VIDEO_EXTS)

    for ext in target_exts:
        try:
            # Set default ProgID & PerceivedType
            ext_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}")
            winreg.SetValueEx(ext_key, "", 0, winreg.REG_SZ, "GalleryCube.Media")
            is_pic = ext in PHOTO_EXTS
            winreg.SetValueEx(ext_key, "PerceivedType", 0, winreg.REG_SZ, "image" if is_pic else "video")
            winreg.CloseKey(ext_key)

            if is_pic:
                ext_thumb = winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}\\ShellEx\\{{e357fccd-a995-4576-b01f-234630154e96}}")
                winreg.SetValueEx(ext_thumb, "", 0, winreg.REG_SZ, PHOTO_THUMB_CLSID)
                winreg.CloseKey(ext_thumb)

                ext_extract = winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}\\ShellEx\\{{BB2E617C-0920-11d1-9A0B-00C04FC2D6C1}}")
                winreg.SetValueEx(ext_extract, "", 0, winreg.REG_SZ, EXTRACT_IMAGE_CLSID)
                winreg.CloseKey(ext_extract)

            # Register in OpenWithProgids
            ow_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}\\OpenWithProgids")
            winreg.SetValueEx(ow_key, "GalleryCube.Media", 0, winreg.REG_NONE, b"")
            winreg.CloseKey(ow_key)
        except Exception:
            pass

    # Notify Windows Shell
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except Exception:
        pass


def register_uninstall_entry(install_dir: str):
    uninstall_exe = os.path.join(install_dir, "Uninstall.exe")
    app_exe = os.path.join(install_dir, "GalleryCube.exe")

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\GalleryCube"
    un_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)

    winreg.SetValueEx(un_key, "DisplayName", 0, winreg.REG_SZ, "Gallery Cube")
    winreg.SetValueEx(un_key, "DisplayVersion", 0, winreg.REG_SZ, VERSION)
    winreg.SetValueEx(un_key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
    winreg.SetValueEx(un_key, "DisplayIcon", 0, winreg.REG_SZ, f"{app_exe},0")
    winreg.SetValueEx(un_key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
    winreg.SetValueEx(un_key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstall_exe}"')
    winreg.SetValueEx(un_key, "URLInfoAbout", 0, winreg.REG_SZ, "https://rmscube.com")
    winreg.SetValueEx(un_key, "EstimatedSize", 0, winreg.REG_DWORD, 95000)
    winreg.SetValueEx(un_key, "NoModify", 0, winreg.REG_DWORD, 1)
    winreg.SetValueEx(un_key, "NoRepair", 0, winreg.REG_DWORD, 1)

    winreg.CloseKey(un_key)


def perform_silent_install():
    install_dir = get_default_install_dir()
    payload_zip = get_payload_path()
    if not payload_zip or not os.path.exists(payload_zip):
        sys.exit(1)

    # Terminate running instance if updating
    try:
        subprocess.run(["taskkill", "/F", "/IM", "GalleryCube.exe"], capture_output=True)
    except Exception:
        pass

    os.makedirs(install_dir, exist_ok=True)
    with zipfile.ZipFile(payload_zip, "r") as zf:
        zf.extractall(install_dir)

    target_exe = os.path.join(install_dir, "GalleryCube.exe")
    un_exe = os.path.join(install_dir, "Uninstall.exe")

    # Register WIC HEIC 64-bit shell extension for Explorer thumbnail and preview
    wic_dll = os.path.join(install_dir, "wic_heic.dll")
    if os.path.exists(wic_dll):
        try:
            subprocess.run(["regsvr32.exe", "/s", wic_dll], capture_output=True, timeout=10)
        except Exception:
            pass

    # Shortcuts
    user_desktop = os.path.join(get_desktop_dir(), "Gallery Cube.lnk")
    create_windows_shortcut(target_exe, user_desktop, target_exe, "Gallery Cube 🧊 — Universal Media Studio by rmscube")

    start_menu_folder = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Gallery Cube")
    os.makedirs(start_menu_folder, exist_ok=True)
    create_windows_shortcut(target_exe, os.path.join(start_menu_folder, "Gallery Cube.lnk"), target_exe, "Gallery Cube 🧊 by rmscube")
    create_windows_shortcut(un_exe, os.path.join(start_menu_folder, "Uninstall Gallery Cube.lnk"), target_exe, "Uninstall Gallery Cube")

    # Associations
    register_associations(install_dir, photo=True, video=True)
    register_uninstall_entry(install_dir)


class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gallery Cube 🧊 Setup — rmscube")
        self.geometry("640x530")
        self.minsize(640, 530)
        self.resizable(False, False)
        self.configure(bg="#0f172a")

        # High DPI awareness
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.install_dir_var = tk.StringVar(value=get_default_install_dir())
        self.chk_desktop_var = tk.BooleanVar(value=True)
        self.chk_start_var = tk.BooleanVar(value=True)
        self.chk_photos_var = tk.BooleanVar(value=True)
        self.chk_videos_var = tk.BooleanVar(value=True)
        self.chk_launch_var = tk.BooleanVar(value=True)

        self.current_page = 0
        self.pages = []

        self._build_header()
        self._build_content_area()
        self._build_footer()

        self._show_page(0)

    def _build_header(self):
        header = tk.Frame(self, bg="#1e293b", height=70)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        lbl_logo = tk.Label(
            header,
            text="🧊 Gallery Cube",
            font=("Segoe UI", 16, "bold"),
            bg="#1e293b",
            fg="#f8fafc"
        )
        lbl_logo.pack(anchor="w", padx=20, pady=(12, 0))

        lbl_sub = tk.Label(
            header,
            text="Universal Media Studio Setup Wizard  •  Publisher: rmscube",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8"
        )
        lbl_sub.pack(anchor="w", padx=20, pady=(2, 10))

    def _build_content_area(self):
        self.content_frame = tk.Frame(self, bg="#0f172a")
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=16)

        # Build individual page frames
        self.p_welcome = self._create_page_welcome()
        self.p_options = self._create_page_options()
        self.p_installing = self._create_page_installing()
        self.p_finish = self._create_page_finish()

        self.pages = [self.p_welcome, self.p_options, self.p_installing, self.p_finish]

    def _build_footer(self):
        self.footer = tk.Frame(self, bg="#1e293b", height=54)
        self.footer.pack(fill="x", side="bottom")
        self.footer.pack_propagate(False)

        self.btn_cancel = tk.Button(
            self.footer,
            text="Cancel",
            command=self.destroy,
            bg="#334155",
            fg="#ffffff",
            activebackground="#475569",
            activeforeground="#ffffff",
            bd=0,
            padx=14,
            pady=6,
            font=("Segoe UI", 10)
        )
        self.btn_cancel.pack(side="right", padx=(6, 20), pady=12)

        self.btn_next = tk.Button(
            self.footer,
            text="Next >",
            command=self._on_next_clicked,
            bg="#4f46e5",
            fg="#ffffff",
            activebackground="#4338ca",
            activeforeground="#ffffff",
            bd=0,
            padx=20,
            pady=6,
            font=("Segoe UI", 10, "bold")
        )
        self.btn_next.pack(side="right", padx=6, pady=12)

        self.btn_back = tk.Button(
            self.footer,
            text="< Back",
            command=self._on_back_clicked,
            bg="#334155",
            fg="#ffffff",
            activebackground="#475569",
            activeforeground="#ffffff",
            bd=0,
            padx=14,
            pady=6,
            font=("Segoe UI", 10)
        )
        self.btn_back.pack(side="right", padx=6, pady=12)

    def _create_page_welcome(self):
        frame = tk.Frame(self.content_frame, bg="#0f172a")

        lbl_w = tk.Label(
            frame,
            text="Welcome to the Gallery Cube Setup Wizard",
            font=("Segoe UI", 14, "bold"),
            bg="#0f172a",
            fg="#f8fafc",
            anchor="w"
        )
        lbl_w.pack(fill="x", pady=(10, 8))

        desc = (
            "This wizard will install Gallery Cube 🧊 on your computer.\n\n"
            "Gallery Cube is the premier universal media studio for Windows, designed to replace "
            "all legacy image and video viewers with effortless speed and zero lag.\n\n"
            "Key Features:\n"
            "  • Instant Apple HEIC/HEIF photo decoding with live color grading & EXIF\n"
            "  • Ultra-smooth 4K/8K mobile video playback (MP4, MOV, ProRes, MKV, WebM)\n"
            "  • Zero-Lag Navigation: effortlessly handles folders with 10,000+ photos in milliseconds\n"
            "  • Privacy First: 100% offline software with ZERO tracking or telemetry\n"
            "  • Fully compliant with Indian (DPDP Act, IT Act) & International (GDPR, CCPA) laws\n"
            "  • Publisher: rmscube\n\n"
            "Click Next to choose your installation options."
        )
        lbl_desc = tk.Label(
            frame,
            text=desc,
            font=("Segoe UI", 10),
            bg="#0f172a",
            fg="#cbd5e1",
            justify="left",
            anchor="w"
        )
        lbl_desc.pack(fill="x", pady=4)
        return frame

    def _create_page_options(self):
        frame = tk.Frame(self.content_frame, bg="#0f172a")

        lbl_t = tk.Label(
            frame,
            text="Choose Install Location and File Associations",
            font=("Segoe UI", 13, "bold"),
            bg="#0f172a",
            fg="#f8fafc",
            anchor="w"
        )
        lbl_t.pack(fill="x", pady=(4, 10))

        # Destination Folder
        lbl_dest = tk.Label(frame, text="Destination Folder:", font=("Segoe UI", 10, "bold"), bg="#0f172a", fg="#94a3b8", anchor="w")
        lbl_dest.pack(fill="x")

        box_f = tk.Frame(frame, bg="#0f172a")
        box_f.pack(fill="x", pady=(4, 12))

        entry_dir = tk.Entry(box_f, textvariable=self.install_dir_var, font=("Segoe UI", 10), bg="#1e293b", fg="#ffffff", insertbackground="white", bd=1)
        entry_dir.pack(side="left", fill="x", expand=True, ipady=4)

        btn_browse = tk.Button(box_f, text="Browse...", command=self._browse_dir, bg="#334155", fg="#ffffff", bd=0, padx=10, font=("Segoe UI", 9))
        btn_browse.pack(side="right", padx=(8, 0))

        # Options Checkboxes
        lbl_opts = tk.Label(frame, text="Integration Options:", font=("Segoe UI", 10, "bold"), bg="#0f172a", fg="#94a3b8", anchor="w")
        lbl_opts.pack(fill="x", pady=(6, 4))

        cb1 = tk.Checkbutton(frame, text="Create Desktop Shortcut", variable=self.chk_desktop_var, font=("Segoe UI", 10), bg="#0f172a", fg="#ffffff", selectcolor="#1e293b", activebackground="#0f172a", activeforeground="#ffffff")
        cb1.pack(anchor="w", pady=2)

        cb2 = tk.Checkbutton(frame, text="Create Start Menu Shortcuts (with Uninstaller)", variable=self.chk_start_var, font=("Segoe UI", 10), bg="#0f172a", fg="#ffffff", selectcolor="#1e293b", activebackground="#0f172a", activeforeground="#ffffff")
        cb2.pack(anchor="w", pady=2)

        cb3 = tk.Checkbutton(frame, text="Set as Default Double-Click Viewer for Photos (HEIC, JPG, PNG, WebP, BMP, TIFF, AVIF, DNG)", variable=self.chk_photos_var, font=("Segoe UI", 10), bg="#0f172a", fg="#818cf8", selectcolor="#1e293b", activebackground="#0f172a", activeforeground="#818cf8")
        cb3.pack(anchor="w", pady=2)

        cb4 = tk.Checkbutton(frame, text="Set as Default Double-Click Player for Videos (MP4, MOV, MKV, WebM, AVI)", variable=self.chk_videos_var, font=("Segoe UI", 10), bg="#0f172a", fg="#f43f5e", selectcolor="#1e293b", activebackground="#0f172a", activeforeground="#f43f5e")
        cb4.pack(anchor="w", pady=2)

        # Space summary
        self.lbl_space = tk.Label(frame, text="Space required: ~95 MB", font=("Segoe UI", 9), bg="#0f172a", fg="#64748b", anchor="w")
        self.lbl_space.pack(fill="x", pady=(12, 0))

        return frame

    def _create_page_installing(self):
        frame = tk.Frame(self.content_frame, bg="#0f172a")

        lbl_i = tk.Label(
            frame,
            text="Installing Gallery Cube...",
            font=("Segoe UI", 14, "bold"),
            bg="#0f172a",
            fg="#f8fafc",
            anchor="w"
        )
        lbl_i.pack(fill="x", pady=(20, 16))

        self.lbl_install_status = tk.Label(
            frame,
            text="Preparing installation...",
            font=("Segoe UI", 10),
            bg="#0f172a",
            fg="#94a3b8",
            anchor="w"
        )
        self.lbl_install_status.pack(fill="x", pady=(0, 8))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Indigo.Horizontal.TProgressbar", foreground="#4f46e5", background="#4f46e5", troughcolor="#1e293b")

        self.progress_bar = ttk.Progressbar(frame, style="Indigo.Horizontal.TProgressbar", mode="indeterminate", length=580)
        self.progress_bar.pack(fill="x", pady=6)

        return frame

    def _create_page_finish(self):
        frame = tk.Frame(self.content_frame, bg="#0f172a")

        lbl_f = tk.Label(
            frame,
            text="Installation Complete! 🎉",
            font=("Segoe UI", 16, "bold"),
            bg="#0f172a",
            fg="#34d399",
            anchor="w"
        )
        lbl_f.pack(fill="x", pady=(20, 10))

        summary = (
            "Gallery Cube 🧊 by rmscube has been successfully installed on your computer!\n\n"
            "What was configured:\n"
            "  ✓ Application files installed cleanly\n"
            "  ✓ Desktop and Start Menu shortcuts created\n"
            "  ✓ Windows file associations registered (double-click opens directly)\n"
            "  ✓ Registered in Windows Installed Apps (with Clean Uninstaller)\n\n"
            "Click Finish to exit setup and start using Gallery Cube."
        )
        lbl_s = tk.Label(frame, text=summary, font=("Segoe UI", 10), bg="#0f172a", fg="#cbd5e1", justify="left", anchor="w")
        lbl_s.pack(fill="x", pady=6)

        cb_launch = tk.Checkbutton(
            frame,
            text="Launch Gallery Cube now",
            variable=self.chk_launch_var,
            font=("Segoe UI", 11, "bold"),
            bg="#0f172a",
            fg="#ffffff",
            selectcolor="#1e293b",
            activebackground="#0f172a",
            activeforeground="#ffffff"
        )
        cb_launch.pack(anchor="w", pady=(14, 0))

        return frame

    def _browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.install_dir_var.get(), title="Select Destination Folder")
        if d:
            self.install_dir_var.set(os.path.join(d, "GalleryCube"))

    def _show_page(self, index: int):
        self.current_page = index
        for i, p in enumerate(self.pages):
            if i == index:
                p.pack(fill="both", expand=True)
            else:
                p.pack_forget()

        if index == 0:
            self.btn_back.configure(state="disabled")
            self.btn_next.configure(text="Next >", state="normal")
            self.btn_cancel.configure(state="normal")
        elif index == 1:
            self.btn_back.configure(state="normal")
            self.btn_next.configure(text="Install", state="normal")
            self.btn_cancel.configure(state="normal")
        elif index == 2:
            self.btn_back.configure(state="disabled")
            self.btn_next.configure(state="disabled")
            self.btn_cancel.configure(state="disabled")
            self.progress_bar.start(10)
            threading.Thread(target=self._run_install_worker, daemon=True).start()
        elif index == 3:
            self.btn_back.configure(state="disabled")
            self.btn_cancel.pack_forget()
            self.btn_next.configure(text="Finish", state="normal")

    def _on_next_clicked(self):
        if self.current_page == 0:
            self._show_page(1)
        elif self.current_page == 1:
            self._show_page(2)
        elif self.current_page == 3:
            # Finish
            if self.chk_launch_var.get():
                target_exe = os.path.join(self.install_dir_var.get(), "GalleryCube.exe")
                if os.path.exists(target_exe):
                    subprocess.Popen([target_exe])
            self.destroy()

    def _on_back_clicked(self):
        if self.current_page == 1:
            self._show_page(0)

    def _run_install_worker(self):
        target_dir = self.install_dir_var.get()
        payload_zip = get_payload_path()

        try:
            self._update_status("Closing active instances...")
            try:
                subprocess.run(["taskkill", "/F", "/IM", "GalleryCube.exe"], capture_output=True)
            except Exception:
                pass

            self._update_status("Extracting application binaries...")
            os.makedirs(target_dir, exist_ok=True)

            if payload_zip and os.path.exists(payload_zip):
                with zipfile.ZipFile(payload_zip, "r") as zf:
                    zf.extractall(target_dir)
            else:
                raise FileNotFoundError("Installation payload package could not be located.")

            target_exe = os.path.join(target_dir, "GalleryCube.exe")
            un_exe = os.path.join(target_dir, "Uninstall.exe")

            # Register WIC HEIC shell extension for Windows Explorer thumbnails and previews
            self._update_status("Registering Windows Explorer preview & thumbnail codec...")
            wic_dll = os.path.join(target_dir, "wic_heic.dll")
            if os.path.exists(wic_dll):
                try:
                    subprocess.run(["regsvr32.exe", "/s", wic_dll], capture_output=True, timeout=10)
                except Exception:
                    pass

            # Shortcuts
            self._update_status("Creating desktop & start menu shortcuts...")
            if self.chk_desktop_var.get():
                user_desktop = os.path.join(get_desktop_dir(), "Gallery Cube.lnk")
                create_windows_shortcut(target_exe, user_desktop, target_exe, "Gallery Cube 🧊 — Universal Media Studio by rmscube")

            if self.chk_start_var.get():
                start_menu_folder = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Gallery Cube")
                os.makedirs(start_menu_folder, exist_ok=True)
                create_windows_shortcut(target_exe, os.path.join(start_menu_folder, "Gallery Cube.lnk"), target_exe, "Gallery Cube 🧊 by rmscube")
                create_windows_shortcut(un_exe, os.path.join(start_menu_folder, "Uninstall Gallery Cube.lnk"), target_exe, "Uninstall Gallery Cube")

            # File associations
            self._update_status("Registering file associations in Windows...")
            register_associations(target_dir, photo=self.chk_photos_var.get(), video=self.chk_videos_var.get())

            # Windows Installed Apps
            self._update_status("Registering uninstaller in Windows Settings...")
            register_uninstall_entry(target_dir)

            self.after(300, lambda: self._show_page(3))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Installation Error", f"Installation failed:\n\n{str(e)}"))
            self.after(0, self.destroy)

    def _update_status(self, text: str):
        self.after(0, lambda: self.lbl_install_status.configure(text=text))


def main():
    if any(arg.lower() in ("/s", "-s", "--silent") for arg in sys.argv):
        perform_silent_install()
        sys.exit(0)

    app = SetupWizard()
    app.mainloop()


if __name__ == "__main__":
    main()

