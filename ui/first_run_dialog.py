"""
First-Run File Association Wizard for Gallery Cube 🧊.
Allows user to select which image & video formats Gallery Cube handles by default on double-click.
"""
from typing import Dict, List, Callable, Optional
import customtkinter as ctk

from core.config_manager import register_file_associations, mark_first_run_done


PHOTO_FORMATS = [
    (".heic", "HEIC / HEIF (Apple & Samsung Flagship)"),
    (".jpg", "JPEG / JPG (Standard Camera Photos)"),
    (".png", "PNG (Lossless & Alpha Transparency)"),
    (".webp", "WebP (Google Web Format)"),
    (".bmp", "BMP / DIB (Windows Bitmaps)"),
    (".tiff", "TIFF / TIF (High-Bit Depth Scans)"),
    (".gif", "GIF (Animations & Clips)"),
    (".ico", "ICO (Windows Icons)"),
    (".avif", "AVIF (Next-Gen Format)"),
    (".dng", "DNG (Digital Camera RAW)")
]

VIDEO_FORMATS = [
    (".mp4", "MP4 (Samsung & Universal HD/4K/8K)"),
    (".mov", "MOV (Apple QuickTime & ProRes)"),
    (".mkv", "MKV (Matroska HD Video)"),
    (".webm", "WebM (Web Video)"),
    (".avi", "AVI (Audio Video Interleaved)"),
    (".m4v", "M4V (Apple Video)"),
    (".3gp", "3GP (Mobile Phone Video)")
]


class FirstRunDialog(ctk.CTkToplevel):
    def __init__(self, master, on_applied: Optional[Callable[[int], None]] = None):
        super().__init__(master)
        self.on_applied = on_applied

        self.title("Gallery Cube 🧊 — Default File Association Setup")
        self.geometry("640x700")
        self.minsize(580, 620)
        self.configure(fg_color="#0f172a")

        self.transient(master)
        self.grab_set()

        self.checkbox_vars: Dict[str, ctk.BooleanVar] = {}

        self._build_ui()

    def _build_ui(self):
        # 1. Header
        header = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=12)
        header.pack(fill="x", padx=18, pady=(18, 12))

        lbl_title = ctk.CTkLabel(
            header,
            text="🧊 Set Gallery Cube as Your Default Viewer",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f8fafc"
        )
        lbl_title.pack(anchor="w", padx=16, pady=(14, 4))

        lbl_sub = ctk.CTkLabel(
            header,
            text="Select which image and video formats should automatically open in Gallery Cube\nwhen you double-click them in Windows File Explorer.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="left"
        )
        lbl_sub.pack(anchor="w", padx=16, pady=(0, 14))

        # 2. Quick Selection Presets Bar
        presets_bar = ctk.CTkFrame(self, fg_color="transparent")
        presets_bar.pack(fill="x", padx=18, pady=(0, 8))

        btn_all = ctk.CTkButton(
            presets_bar,
            text="✓ Select All (Recommended)",
            command=self.select_all,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            height=28,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        btn_all.pack(side="left", padx=(0, 6))

        btn_photos = ctk.CTkButton(
            presets_bar,
            text="Photos Only",
            command=self.select_photos_only,
            fg_color="#1e293b",
            hover_color="#334155",
            height=28,
            font=ctk.CTkFont(size=11)
        )
        btn_photos.pack(side="left", padx=3)

        btn_videos = ctk.CTkButton(
            presets_bar,
            text="Videos Only",
            command=self.select_videos_only,
            fg_color="#1e293b",
            hover_color="#334155",
            height=28,
            font=ctk.CTkFont(size=11)
        )
        btn_videos.pack(side="left", padx=3)

        btn_none = ctk.CTkButton(
            presets_bar,
            text="Clear",
            command=self.clear_all,
            fg_color="#1e293b",
            hover_color="#334155",
            height=28,
            width=55,
            font=ctk.CTkFont(size=11)
        )
        btn_none.pack(side="left", padx=3)

        # 3. Formats Checklist (Scrollable Frame)
        scroll = ctk.CTkScrollableFrame(self, fg_color="#1e293b", corner_radius=12)
        scroll.pack(fill="both", expand=True, padx=18, pady=4)

        # Group 1: Photos & Images
        lbl_photo_sec = ctk.CTkLabel(
            scroll,
            text="📸 Photos & Images",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#818cf8"
        )
        lbl_photo_sec.pack(anchor="w", padx=12, pady=(8, 6))

        for ext, desc in PHOTO_FORMATS:
            var = ctk.BooleanVar(value=True)  # Pre-selected by default!
            self.checkbox_vars[ext] = var
            chk = ctk.CTkCheckBox(
                scroll,
                text=f"{ext.upper()}  —  {desc}",
                variable=var,
                font=ctk.CTkFont(size=11),
                checkbox_height=18,
                checkbox_width=18,
                border_color="#475569",
                hover_color="#4f46e5"
            )
            chk.pack(anchor="w", padx=16, pady=3)

        # Group 2: Videos & Motion Clips
        sep = ctk.CTkFrame(scroll, height=1, fg_color="#334155")
        sep.pack(fill="x", padx=12, pady=12)

        lbl_video_sec = ctk.CTkLabel(
            scroll,
            text="🎬 Mobile & Flagship Videos",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f43f5e"
        )
        lbl_video_sec.pack(anchor="w", padx=12, pady=(4, 6))

        for ext, desc in VIDEO_FORMATS:
            var = ctk.BooleanVar(value=True)  # Pre-selected by default!
            self.checkbox_vars[ext] = var
            chk = ctk.CTkCheckBox(
                scroll,
                text=f"{ext.upper()}  —  {desc}",
                variable=var,
                font=ctk.CTkFont(size=11),
                checkbox_height=18,
                checkbox_width=18,
                border_color="#475569",
                hover_color="#e11d48"
            )
            chk.pack(anchor="w", padx=16, pady=3)

        # 4. Action Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=18, pady=(12, 18))

        btn_apply = ctk.CTkButton(
            footer,
            text="🚀 Apply & Set as Default Double-Click Viewer",
            command=self.apply_associations,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            height=38,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        btn_apply.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_skip = ctk.CTkButton(
            footer,
            text="Skip for Now",
            command=self._on_skip,
            fg_color="#334155",
            hover_color="#475569",
            height=38,
            width=100,
            font=ctk.CTkFont(size=11)
        )
        btn_skip.pack(side="right")

    def select_all(self):
        for var in self.checkbox_vars.values():
            var.set(True)

    def clear_all(self):
        for var in self.checkbox_vars.values():
            var.set(False)

    def select_photos_only(self):
        photo_exts = {ext for ext, _ in PHOTO_FORMATS}
        for ext, var in self.checkbox_vars.items():
            var.set(ext in photo_exts)

    def select_videos_only(self):
        video_exts = {ext for ext, _ in VIDEO_FORMATS}
        for ext, var in self.checkbox_vars.items():
            var.set(ext in video_exts)

    def apply_associations(self):
        selected = [ext for ext, var in self.checkbox_vars.items() if var.get()]
        if not selected:
            self._on_skip()
            return

        # Register in Windows HKCU
        count, msg = register_file_associations(selected)
        mark_first_run_done(selected)

        if self.on_applied:
            self.on_applied(count)

        self.destroy()

    def _on_skip(self):
        mark_first_run_done([])
        self.destroy()

