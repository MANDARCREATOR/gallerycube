"""
Batch HEIC Converter Dialog for HEIC Studio Pro.
Asynchronously converts folders of iPhone & Samsung HEIC/HEIF files to JPEG, PNG, or WebP.
"""
import os
import glob
import threading
from tkinter import filedialog
from typing import List
import customtkinter as ctk
from core.exporter import batch_convert_heic


class BatchConverterDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)

        self.title("Batch HEIC Photo Converter")
        self.geometry("560x580")
        self.resizable(False, False)
        self.configure(fg_color="#0f172a")

        self.transient(master)
        self.grab_set()

        self.selected_files: List[str] = []
        self.output_dir: str = ""
        self.is_converting = False

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=12)
        header.pack(fill="x", padx=16, pady=(16, 12))

        lbl_title = ctk.CTkLabel(
            header,
            text="⚡ Batch HEIC Converter",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f8fafc"
        )
        lbl_title.pack(anchor="w", padx=14, pady=(12, 2))

        lbl_sub = ctk.CTkLabel(
            header,
            text="Convert an entire album or folder of Apple/Samsung HEIC photos in seconds",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        lbl_sub.pack(anchor="w", padx=14, pady=(0, 12))

        # 1. Source Selection
        src_card = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10)
        src_card.pack(fill="x", padx=16, pady=4)

        lbl_src_title = ctk.CTkLabel(src_card, text="Source Files", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_src_title.pack(anchor="w", padx=12, pady=(10, 4))

        src_btn_row = ctk.CTkFrame(src_card, fg_color="transparent")
        src_btn_row.pack(fill="x", padx=12, pady=4)

        btn_pick_folder = ctk.CTkButton(
            src_btn_row,
            text="Select Source Folder",
            command=self._pick_source_folder,
            fg_color="#334155",
            hover_color="#475569",
            height=28
        )
        btn_pick_folder.pack(side="left", padx=(0, 6))

        btn_pick_files = ctk.CTkButton(
            src_btn_row,
            text="Select Files...",
            command=self._pick_source_files,
            fg_color="#334155",
            hover_color="#475569",
            height=28
        )
        btn_pick_files.pack(side="left")

        self.lbl_src_status = ctk.CTkLabel(
            src_card,
            text="No files selected",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.lbl_src_status.pack(anchor="w", padx=12, pady=(4, 10))

        # 2. Output Directory Selection
        dst_card = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10)
        dst_card.pack(fill="x", padx=16, pady=6)

        lbl_dst_title = ctk.CTkLabel(dst_card, text="Destination Folder", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_dst_title.pack(anchor="w", padx=12, pady=(10, 4))

        dst_btn_row = ctk.CTkFrame(dst_card, fg_color="transparent")
        dst_btn_row.pack(fill="x", padx=12, pady=4)

        btn_pick_dst = ctk.CTkButton(
            dst_btn_row,
            text="Choose Output Folder",
            command=self._pick_dst_folder,
            fg_color="#334155",
            hover_color="#475569",
            height=28
        )
        btn_pick_dst.pack(side="left")

        self.lbl_dst_status = ctk.CTkLabel(
            dst_card,
            text="No folder selected",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.lbl_dst_status.pack(anchor="w", padx=12, pady=(4, 10))

        # 3. Format & Settings Card
        settings_card = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=10)
        settings_card.pack(fill="x", padx=16, pady=4)

        settings_row = ctk.CTkFrame(settings_card, fg_color="transparent")
        settings_row.pack(fill="x", padx=12, pady=10)

        lbl_fmt = ctk.CTkLabel(settings_row, text="Target Format:", font=ctk.CTkFont(size=11))
        lbl_fmt.pack(side="left", padx=(0, 6))

        self.fmt_var = ctk.StringVar(value="JPEG")
        self.fmt_menu = ctk.CTkOptionMenu(
            settings_row,
            values=["JPEG", "PNG", "WEBP", "HEIF"],
            variable=self.fmt_var,
            width=90,
            height=28
        )
        self.fmt_menu.pack(side="left", padx=(0, 16))

        lbl_q = ctk.CTkLabel(settings_row, text="Quality:", font=ctk.CTkFont(size=11))
        lbl_q.pack(side="left", padx=(0, 6))

        self.slider_quality = ctk.CTkSlider(
            settings_row,
            from_=60,
            to=100,
            number_of_steps=40,
            width=110,
            command=self._on_quality_change
        )
        self.slider_quality.set(95)
        self.slider_quality.pack(side="left")

        self.lbl_q_val = ctk.CTkLabel(settings_row, text="95%", font=ctk.CTkFont(size=11, weight="bold"))
        self.lbl_q_val.pack(side="left", padx=6)

        self.check_exif = ctk.CTkCheckBox(
            settings_card,
            text="Preserve EXIF metadata (Camera, Date, GPS)",
            font=ctk.CTkFont(size=11),
            checkbox_height=18,
            checkbox_width=18
        )
        self.check_exif.select()
        self.check_exif.pack(anchor="w", padx=12, pady=(0, 10))

        # 4. Progress & Action
        self.progress_bar = ctk.CTkProgressBar(self, height=8, progress_color="#4f46e5")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=16, pady=(12, 4))

        self.lbl_progress = ctk.CTkLabel(
            self,
            text="Ready to convert",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.lbl_progress.pack(anchor="w", padx=16, pady=2)

        # Buttons
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(8, 16))

        self.btn_convert = ctk.CTkButton(
            footer,
            text="🚀 Start Batch Conversion",
            command=self._start_conversion,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_convert.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_cancel = ctk.CTkButton(
            footer,
            text="Close",
            command=self.destroy,
            fg_color="#334155",
            hover_color="#475569",
            height=36,
            width=80
        )
        btn_cancel.pack(side="right")

    def _on_quality_change(self, val):
        self.lbl_q_val.configure(text=f"{int(round(val))}%")

    def _pick_source_folder(self):
        folder = filedialog.askdirectory(title="Select Folder Containing HEIC Photos")
        if folder:
            # Find all .heic / .heif files
            exts = ["*.heic", "*.HEIC", "*.heif", "*.HEIF"]
            files = []
            for ext in exts:
                files.extend(glob.glob(os.path.join(folder, ext)))
            self.selected_files = sorted(list(set(files)))
            self.lbl_src_status.configure(
                text=f"Selected {len(self.selected_files)} HEIC files from: {os.path.basename(folder)}"
            )

    def _pick_source_files(self):
        file_paths = filedialog.askopenfilenames(
            title="Select HEIC Photos",
            filetypes=[("HEIC / HEIF Images", "*.heic;*.heif;*.HEIC;*.HEIF")]
        )
        if file_paths:
            self.selected_files = list(file_paths)
            self.lbl_src_status.configure(text=f"Selected {len(self.selected_files)} individual files")

    def _pick_dst_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_dir = folder
            self.lbl_dst_status.configure(text=f"Save to: {folder}")

    def _start_conversion(self):
        if self.is_converting:
            return
        if not self.selected_files:
            self.lbl_progress.configure(text="❌ Please select source HEIC files first!")
            return
        if not self.output_dir:
            self.lbl_progress.configure(text="❌ Please choose destination folder!")
            return

        self.is_converting = True
        self.btn_convert.configure(state="disabled", text="Converting...")
        self.progress_bar.set(0)

        target_fmt = self.fmt_var.get()
        quality = int(round(self.slider_quality.get()))
        preserve_exif = bool(self.check_exif.get())

        thread = threading.Thread(
            target=self._run_batch_worker,
            args=(target_fmt, quality, preserve_exif),
            daemon=True
        )
        thread.start()

    def _run_batch_worker(self, target_fmt: str, quality: int, preserve_exif: bool):
        total = len(self.selected_files)

        def progress(curr, tot, fname):
            frac = curr / tot
            self.after(0, lambda: self._update_progress_ui(frac, f"Converting ({curr}/{tot}): {fname}"))

        succ, fail, errs = batch_convert_heic(
            file_list=self.selected_files,
            output_directory=self.output_dir,
            target_format=target_fmt,
            quality=quality,
            preserve_exif=preserve_exif,
            progress_callback=progress
        )

        self.after(0, lambda: self._finish_conversion(succ, fail))

    def _update_progress_ui(self, fraction: float, msg: str):
        self.progress_bar.set(fraction)
        self.lbl_progress.configure(text=msg)

    def _finish_conversion(self, succ: int, fail: int):
        self.is_converting = False
        self.btn_convert.configure(state="normal", text="🚀 Start Batch Conversion")
        self.progress_bar.set(1.0)
        self.lbl_progress.configure(
            text=f"✅ Finished! Successfully converted {succ} photos. (Failed: {fail})"
        )

