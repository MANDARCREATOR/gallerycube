"""
Horizontal Filmstrip Carousel for Gallery Cube 🧊.
Displays nearby photos & videos in a sleek horizontal preview pane with instant jumping.
Ultra-high performance: utilizes background thumbnail caching and a sliding window for 10,000+ files.
"""
import os
import queue
import threading
from typing import List, Callable, Optional, Dict
from PIL import Image, ImageOps
import customtkinter as ctk

from core.image_engine import SUPPORTED_EXTENSIONS
from core.video_engine import SUPPORTED_VIDEO_EXTENSIONS

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class FilmstripView(ctk.CTkFrame):
    def __init__(self, master, on_select: Callable[[str], None], **kwargs):
        super().__init__(master, height=94, fg_color="#090d16", corner_radius=0, **kwargs)
        self.pack_propagate(False)
        self.on_select = on_select

        self.files: List[str] = []
        self.active_index: int = -1
        self.window_size: int = 17  # Number of visible thumbnails in sliding window
        self.window_offset: int = 0

        # Memory cache for thumbnails & thread-safe ready queue
        self._thumb_cache: Dict[str, ctk.CTkImage] = {}
        self._loading_threads = set()
        self._ready_queue = queue.Queue()

        self._build_ui()
        self._poll_ready_queue()

    def _poll_ready_queue(self):
        has_new = False
        try:
            while not self._ready_queue.empty():
                fpath, ctk_img = self._ready_queue.get_nowait()
                self._thumb_cache[fpath] = ctk_img
                has_new = True
        except Exception:
            pass
        if has_new:
            self._render_strip()
        if self.winfo_exists():
            self.after(100, self._poll_ready_queue)

    def _build_ui(self):
        # 1. Pan Left Button
        self.btn_pan_left = ctk.CTkButton(
            self,
            text="◀",
            width=28,
            height=78,
            command=self.pan_left,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_pan_left.pack(side="left", padx=(6, 4), pady=8)

        # 2. Main Scrollable Container for Horizontal Cards
        self.strip_frame = ctk.CTkScrollableFrame(
            self,
            orientation="horizontal",
            fg_color="transparent",
            height=82
        )
        self.strip_frame.pack(side="left", fill="both", expand=True, pady=4)

        # Bind mousewheel over strip
        self.strip_frame.bind("<MouseWheel>", self._on_mousewheel)

        # 3. Pan Right Button
        self.btn_pan_right = ctk.CTkButton(
            self,
            text="▶",
            width=28,
            height=78,
            command=self.pan_right,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_pan_right.pack(side="right", padx=(4, 6), pady=8)

    def set_files(self, files: List[str], active_index: int):
        self.files = files
        self.active_index = active_index
        # Center sliding window around active item
        half = self.window_size // 2
        self.window_offset = max(0, min(active_index - half, max(0, len(self.files) - self.window_size)))
        self._render_strip()

    def set_active_index(self, active_index: int):
        if not self.files:
            return
        self.active_index = active_index
        # Check if active item is outside current visible sliding window
        half = self.window_size // 2
        if active_index < self.window_offset or active_index >= self.window_offset + self.window_size:
            self.window_offset = max(0, min(active_index - half, max(0, len(self.files) - self.window_size)))
        self._render_strip()

    def pan_left(self):
        if not self.files:
            return
        step = max(1, self.window_size // 3)
        self.window_offset = max(0, self.window_offset - step)
        self._render_strip()

    def pan_right(self):
        if not self.files:
            return
        step = max(1, self.window_size // 3)
        max_offset = max(0, len(self.files) - self.window_size)
        self.window_offset = min(max_offset, self.window_offset + step)
        self._render_strip()

    def _on_mousewheel(self, event):
        if event.delta > 0:
            self.pan_left()
        else:
            self.pan_right()

    def _render_strip(self):
        # Clear existing item cards in strip
        for widget in self.strip_frame.winfo_children():
            widget.destroy()

        if not self.files:
            lbl = ctk.CTkLabel(
                self.strip_frame,
                text="No photos or videos in current album",
                font=ctk.CTkFont(size=11),
                text_color="#64748b"
            )
            lbl.pack(padx=20, pady=25)
            return

        start = self.window_offset
        end = min(len(self.files), start + self.window_size)

        for idx in range(start, end):
            fpath = self.files[idx]
            is_active = (idx == self.active_index)
            is_video = any(fpath.lower().endswith(ext) for ext in SUPPORTED_VIDEO_EXTENSIONS)
            fname = os.path.basename(fpath)

            # Card container
            card = ctk.CTkFrame(
                self.strip_frame,
                width=72,
                height=76,
                fg_color="#312e81" if is_active else "#1e293b",
                corner_radius=8,
                border_width=2 if is_active else 1,
                border_color="#818cf8" if is_active else "#334155"
            )
            card.pack(side="left", padx=3, pady=2)
            card.pack_propagate(False)

            # Make card clickable
            card.bind("<Button-1>", lambda e, p=fpath: self.on_select(p))

            # Thumbnail Image or Placeholder
            thumb_img = self._get_or_load_thumbnail(fpath, is_video)

            img_lbl = ctk.CTkLabel(
                card,
                text="" if thumb_img else ("▶ Video" if is_video else "🖼 Photo"),
                image=thumb_img,
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color="#94a3b8",
                width=62,
                height=48
            )
            img_lbl.pack(pady=(4, 0))
            img_lbl.bind("<Button-1>", lambda e, p=fpath: self.on_select(p))

            # Truncated filename below
            short_name = fname
            if len(short_name) > 10:
                short_name = short_name[:7] + "..."

            name_lbl = ctk.CTkLabel(
                card,
                text=short_name,
                font=ctk.CTkFont(size=8, weight="bold" if is_active else "normal"),
                text_color="#ffffff" if is_active else "#94a3b8"
            )
            name_lbl.pack(pady=(0, 2))
            name_lbl.bind("<Button-1>", lambda e, p=fpath: self.on_select(p))

    def _get_or_load_thumbnail(self, fpath: str, is_video: bool) -> Optional[ctk.CTkImage]:
        if fpath in self._thumb_cache:
            return self._thumb_cache[fpath]

        # Trigger background generation if not already loading
        if fpath not in self._loading_threads:
            self._loading_threads.add(fpath)
            threading.Thread(target=self._async_generate_thumbnail, args=(fpath, is_video), daemon=True).start()

        return None

    def _async_generate_thumbnail(self, fpath: str, is_video: bool):
        try:
            pil_img = None
            if is_video and HAS_CV2:
                cap = cv2.VideoCapture(fpath)
                ret, frame = cap.read()
                cap.release()
                if ret:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb)
            elif not is_video:
                # Open image header and generate fast thumbnail
                with Image.open(fpath) as im:
                    # Convert to RGB if needed
                    if im.mode not in ("RGB", "RGBA"):
                        im = im.convert("RGB")
                    im.thumbnail((60, 48), Image.Resampling.LANCZOS)
                    pil_img = im.copy()

            if pil_img:
                # Center crop to 60x46 for clean uniform look
                pil_img.thumbnail((60, 46), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                self._ready_queue.put((fpath, ctk_img))
        except Exception:
            pass
        finally:
            self._loading_threads.discard(fpath)
