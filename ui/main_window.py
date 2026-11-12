"""
Main Application Window for Gallery Cube 🧊.
Universal Media Studio: The Ultimate Photo & Video Viewer for Windows.
Features:
- Native Windows Drag & Drop (windnd)
- Full-Screen Immersive Mode (F11 / Double-click)
- Zen / Cinema Mode (Tab key toggles all toolbars for edge-to-edge viewing)
- Copy Image to Clipboard (Ctrl+C)
- Safe Delete to Windows Recycle Bin (Delete key)
- Hands-Free Slideshow Mode (F5)
- Floating Modern Toast Alerts
- Seamless Switching between Flagship HEIC/Photos & 4K/8K Videos
"""
import os
import glob
from tkinter import filedialog, messagebox
from typing import List, Optional
from PIL import Image
import customtkinter as ctk
import windnd

from core.image_engine import ImageEngine, SUPPORTED_EXTENSIONS
from core.video_engine import VideoEngine, SUPPORTED_VIDEO_EXTENSIONS
from core.exif_reader import parse_exif_metadata
from core.exporter import export_image
from core.win_utils import copy_image_to_clipboard, send_to_recycle_bin
from core.config_manager import is_first_run
from ui.canvas_view import CanvasView
from ui.video_player_view import VideoPlayerView
from ui.sidebar_adjustments import SidebarAdjustments
from ui.sidebar_transforms import SidebarTransforms
from ui.sidebar_filters import SidebarFilters
from ui.exif_dialog import ExifDialog
from ui.batch_dialog import BatchConverterDialog
from ui.first_run_dialog import FirstRunDialog
from ui.filmstrip_view import FilmstripView

ALL_SUPPORTED_MEDIA = SUPPORTED_EXTENSIONS + SUPPORTED_VIDEO_EXTENSIONS
ALL_SUPPORTED_EXTS_SET = {ext.lower() for ext in ALL_SUPPORTED_MEDIA}


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("Gallery Cube 🧊 — Universal Media Studio")
        self.geometry("1340x860")
        self.minsize(980, 660)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Core engines
        self.image_engine = ImageEngine()
        self.current_media_type = "photo"  # "photo" or "video"
        self.current_file_path: Optional[str] = None
        self.metadata = {}

        # Viewport display & panel visibility state
        self.is_fullscreen = False
        self.is_zen_mode = False
        self.is_slideshow = False
        self.is_edit_panel_visible = False  # Hidden by default for clean edge-to-edge view
        self.is_filmstrip_visible = True    # Nearby media horizontal carousel in footer
        self._slideshow_timer = None
        self._toast_timer = None

        # Folder album navigation state (Ultra-responsive pagination for 10,000+ files)
        self.album_files: List[str] = []
        self.album_index: int = -1
        self._current_album_dir: Optional[str] = None
        self.album_page: int = 0
        self.ALBUM_PAGE_SIZE: int = 50
        self._search_filter_text: str = ""

        self._build_layout()
        self._bind_shortcuts()
        self._setup_drag_and_drop()

        # Non-intrusive background check for updates from rmscube.com (runs 5 seconds after startup)
        self.after(5000, self._check_updates_quietly)

    def _build_layout(self):
        # 1. Top Ribbon Toolbar
        self.toolbar = ctk.CTkFrame(self, height=48, fg_color="#1e293b", corner_radius=0)
        self.toolbar.pack(fill="x", side="top")
        self._populate_toolbar()

        # 2. Main Central Work Area (Sidebar + Viewport)
        self.workspace = ctk.CTkFrame(self, fg_color="transparent")
        self.workspace.pack(fill="both", expand=True)

        # Left Sidebar (Tabview for Adjustments, Filters, Transforms, Album/Preview)
        # Built un-packed so user enjoys full edge-to-edge view by default
        self._build_sidebar()

        # Viewport Container (holds CanvasView & VideoPlayerView)
        self.viewport_container = ctk.CTkFrame(self.workspace, fg_color="#050811")
        self.viewport_container.pack(side="left", fill="both", expand=True)

        # Viewport: Photo Canvas & Video Player
        self.canvas_view = CanvasView(self.viewport_container)
        self.canvas_view.pack(fill="both", expand=True)

        # Double-click on canvas toggles Full-screen
        self.canvas_view.canvas.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())

        self.video_player = VideoPlayerView(self.viewport_container, on_edit_frame=self.open_extracted_frame)
        self.video_player.canvas.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())

        # 3. Horizontal Filmstrip Carousel in Footer (Nearby Photos & Videos)
        self.filmstrip = FilmstripView(self, on_select=self._on_filmstrip_item_clicked)
        self.filmstrip.pack(fill="x", side="bottom")

        # 4. Floating Modern Toast Alert (Hidden by default)
        self.toast_banner = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#4f46e5",
            text_color="#ffffff",
            corner_radius=20,
            height=34,
            padx=20
        )

        # 5. Bottom Status Bar
        self.status_bar = ctk.CTkFrame(self, height=36, fg_color="#1e293b", corner_radius=0)
        self.status_bar.pack(fill="x", side="bottom")
        self._populate_status_bar()

    def _populate_toolbar(self):
        # App Brand & Icon
        brand_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        brand_frame.pack(side="left", padx=(12, 14))

        lbl_logo = ctk.CTkLabel(
            brand_frame,
            text="🧊 Gallery Cube",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#f8fafc"
        )
        lbl_logo.pack(side="left")

        # Group 1: File Operations
        btn_open = ctk.CTkButton(
            self.toolbar,
            text="📁 Open",
            command=self.open_file_dialog,
            fg_color="#334155",
            hover_color="#475569",
            height=30,
            width=70,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        btn_open.pack(side="left", padx=2)

        btn_folder = ctk.CTkButton(
            self.toolbar,
            text="📂 Folder",
            command=self.open_folder_dialog,
            fg_color="#334155",
            hover_color="#475569",
            height=30,
            width=75,
            font=ctk.CTkFont(size=11)
        )
        btn_folder.pack(side="left", padx=2)

        btn_save = ctk.CTkButton(
            self.toolbar,
            text="💾 Save As",
            command=self.save_as_dialog,
            fg_color="#334155",
            hover_color="#475569",
            height=30,
            width=75,
            font=ctk.CTkFont(size=11)
        )
        btn_save.pack(side="left", padx=2)

        btn_quick_jpg = ctk.CTkButton(
            self.toolbar,
            text="⚡ Quick JPG",
            command=self.quick_export_jpg,
            fg_color="#059669",
            hover_color="#047857",
            height=30,
            width=85,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        btn_quick_jpg.pack(side="left", padx=2)

        # Separator
        sep1 = ctk.CTkFrame(self.toolbar, width=1, height=22, fg_color="#475569")
        sep1.pack(side="left", padx=6)

        # Group 2: Edit & Studio Tools Toggle
        self.btn_toggle_edit = ctk.CTkButton(
            self.toolbar,
            text="🎨 Edit Tools (E)",
            command=self.toggle_edit_panel,
            fg_color="#334155",
            hover_color="#4f46e5",
            height=30,
            width=105,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_toggle_edit.pack(side="left", padx=3)

        self.btn_undo = ctk.CTkButton(
            self.toolbar,
            text="↶ Undo",
            command=self.handle_undo,
            fg_color="#334155",
            hover_color="#475569",
            height=30,
            width=60,
            font=ctk.CTkFont(size=11)
        )
        self.btn_undo.pack(side="left", padx=2)

        self.btn_redo = ctk.CTkButton(
            self.toolbar,
            text="↷ Redo",
            command=self.handle_redo,
            fg_color="#334155",
            hover_color="#475569",
            height=30,
            width=60,
            font=ctk.CTkFont(size=11)
        )
        self.btn_redo.pack(side="left", padx=2)

        # Separator
        sep2 = ctk.CTkFrame(self.toolbar, width=1, height=22, fg_color="#475569")
        sep2.pack(side="left", padx=6)

        # Group 3: View Toggles (Filmstrip, Cinema, Fullscreen)
        self.btn_toggle_filmstrip = ctk.CTkButton(
            self.toolbar,
            text="🎞 Filmstrip",
            command=self.toggle_filmstrip,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            height=30,
            width=85,
            font=ctk.CTkFont(size=11)
        )
        self.btn_toggle_filmstrip.pack(side="left", padx=2)

        btn_zen = ctk.CTkButton(
            self.toolbar,
            text="👁 Cinema (Tab)",
            command=self.toggle_zen_mode,
            fg_color="#334155",
            hover_color="#475569",
            height=30,
            width=105,
            font=ctk.CTkFont(size=11)
        )
        btn_zen.pack(side="left", padx=2)

        # Right-side utilities
        btn_fs = ctk.CTkButton(
            self.toolbar,
            text="⛶ Fullscreen (F11)",
            command=self.toggle_fullscreen,
            fg_color="#334155",
            hover_color="#475569",
            height=30,
            width=115,
            font=ctk.CTkFont(size=11)
        )
        btn_fs.pack(side="right", padx=(4, 12))

        btn_batch = ctk.CTkButton(
            self.toolbar,
            text="⚡ Batch Tool",
            command=self.open_batch_dialog,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            height=30,
            width=90,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        btn_batch.pack(side="right", padx=3)

        btn_exif = ctk.CTkButton(
            self.toolbar,
            text="ℹ Info & Map",
            command=self.open_exif_dialog,
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=30,
            width=95,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        btn_exif.pack(side="right", padx=3)

        btn_formats = ctk.CTkButton(
            self.toolbar,
            text="⚙️ Formats",
            command=self.open_first_run_dialog,
            fg_color="#334155",
            hover_color="#475569",
            height=30,
            width=78,
            font=ctk.CTkFont(size=11)
        )
        btn_formats.pack(side="right", padx=3)

        btn_rate = ctk.CTkButton(
            self.toolbar,
            text="⭐ Rate / Feedback",
            command=self.open_rmscube_feedback,
            fg_color="#f59e0b",
            hover_color="#d97706",
            text_color="#0f172a",
            height=30,
            width=115,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        btn_rate.pack(side="right", padx=3)

    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self.workspace, width=310, fg_color="#0f172a", corner_radius=0)
        # Note: Starts hidden for full edge-to-edge view by default
        self.sidebar_frame.pack_propagate(False)

        # Header with Title & Close Button
        header_bar = ctk.CTkFrame(self.sidebar_frame, fg_color="#1e293b", height=38, corner_radius=0)
        header_bar.pack(fill="x", side="top")
        header_bar.pack_propagate(False)

        lbl_hdr = ctk.CTkLabel(
            header_bar,
            text="🎨 Image Studio & Editor",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f8fafc"
        )
        lbl_hdr.pack(side="left", padx=12, pady=6)

        btn_close_sb = ctk.CTkButton(
            header_bar,
            text="✕ Close",
            command=self.toggle_edit_panel,
            fg_color="#334155",
            hover_color="#ef4444",
            height=26,
            width=65,
            font=ctk.CTkFont(size=10, weight="bold")
        )
        btn_close_sb.pack(side="right", padx=8, pady=6)

        # Tabview
        self.tabview = ctk.CTkTabview(self.sidebar_frame, fg_color="#1e293b", command=self._on_tabview_change)
        self.tabview.pack(fill="both", expand=True, padx=6, pady=(4, 6))
        self._album_dirty = True

        tab_adjust = self.tabview.add("Adjust")
        tab_filters = self.tabview.add("Filters")
        tab_transform = self.tabview.add("Transform")
        tab_album = self.tabview.add("Album & Thumbnails")

        # 1. Adjustments Panel
        self.panel_adjustments = SidebarAdjustments(
            tab_adjust,
            on_change=self.on_adjustment_change,
            on_reset=self.on_adjustment_reset,
            fg_color="transparent"
        )
        self.panel_adjustments.pack(fill="both", expand=True)

        # 2. Filters Panel
        self.panel_filters = SidebarFilters(
            tab_filters,
            on_select_preset=self.on_select_preset,
            fg_color="transparent"
        )
        self.panel_filters.pack(fill="both", expand=True)

        # 3. Transforms Panel
        self.panel_transforms = SidebarTransforms(
            tab_transform,
            on_rotate=self.on_rotate,
            on_flip=self.on_flip,
            on_start_crop=self.on_start_crop,
            on_apply_crop=self.on_apply_crop,
            on_cancel_crop=self.on_cancel_crop,
            on_resize=self.on_resize,
            fg_color="transparent"
        )
        self.panel_transforms.pack(fill="both", expand=True)

        # 4. Folder Album & Responsive Virtual List Panel
        self._build_album_tab(tab_album)

    def _build_album_tab(self, parent):
        # 1. Top Bar: Folder info & real-time filter
        top_bar = ctk.CTkFrame(parent, fg_color="transparent")
        top_bar.pack(fill="x", padx=4, pady=(2, 6))

        self.lbl_album_info = ctk.CTkLabel(
            top_bar,
            text="📁 No folder loaded",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#94a3b8",
            anchor="w"
        )
        self.lbl_album_info.pack(fill="x", padx=4, pady=(2, 4))

        self.album_search_entry = ctk.CTkEntry(
            top_bar,
            placeholder_text="🔍 Search file name...",
            height=28,
            font=ctk.CTkFont(size=11)
        )
        self.album_search_entry.pack(fill="x", padx=4, pady=(0, 4))
        self.album_search_entry.bind("<KeyRelease>", self._on_album_search_changed)

        # 2. Pagination Navigation Bar (Ultra-fast handling of 10,000+ files)
        nav_bar = ctk.CTkFrame(parent, fg_color="#1e293b", height=32, corner_radius=6)
        nav_bar.pack(fill="x", padx=4, pady=(0, 6))

        self.btn_album_prev_page = ctk.CTkButton(
            nav_bar,
            text="◀",
            width=28,
            height=24,
            command=self._prev_album_page,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_album_prev_page.pack(side="left", padx=4, pady=4)

        self.lbl_album_page = ctk.CTkLabel(
            nav_bar,
            text="Page 0 / 0",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#cbd5e1"
        )
        self.lbl_album_page.pack(side="left", expand=True)

        self.btn_album_next_page = ctk.CTkButton(
            nav_bar,
            text="▶",
            width=28,
            height=24,
            command=self._next_album_page,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_album_next_page.pack(side="right", padx=4, pady=4)

        self.btn_jump_active = ctk.CTkButton(
            nav_bar,
            text="🎯 Active",
            width=58,
            height=24,
            command=self._jump_to_current_page,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            font=ctk.CTkFont(size=10, weight="bold")
        )
        self.btn_jump_active.pack(side="right", padx=2, pady=4)

        # 3. Virtual Item List Container (Renders only current page of 50 items for instant speed)
        self.album_items_container = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.album_items_container.pack(fill="both", expand=True)

        self.lbl_album_empty = ctk.CTkLabel(
            self.album_items_container,
            text="Drag & drop any photo/video\nor click 'Folder' to browse.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.lbl_album_empty.pack(pady=20)

    def _on_album_search_changed(self, event=None):
        self._search_filter_text = self.album_search_entry.get().strip().lower()
        self.album_page = 0
        self._render_album_page()

    def _prev_album_page(self):
        if self.album_page > 0:
            self.album_page -= 1
            self._render_album_page()

    def _next_album_page(self):
        display_list = self._get_filtered_album_files()
        total_items = len(display_list)
        total_pages = max(1, (total_items + self.ALBUM_PAGE_SIZE - 1) // self.ALBUM_PAGE_SIZE)
        if self.album_page < total_pages - 1:
            self.album_page += 1
            self._render_album_page()

    def _jump_to_current_page(self):
        if not self.album_files or self.album_index < 0:
            return
        if self._search_filter_text:
            self._search_filter_text = ""
            self.album_search_entry.delete(0, "end")
        self.album_page = max(0, self.album_index // self.ALBUM_PAGE_SIZE)
        self._render_album_page()

    def _get_filtered_album_files(self) -> List[str]:
        if not self._search_filter_text:
            return self.album_files
        return [p for p in self.album_files if self._search_filter_text in os.path.basename(p).lower()]

    def _on_tabview_change(self):
        if self.tabview.get() == "Album & Thumbnails" and getattr(self, "_album_dirty", False):
            self._render_album_page(force=True)

    def _render_album_page(self, force: bool = False):
        if not force and hasattr(self, "tabview") and self.tabview.get() != "Album & Thumbnails":
            self._album_dirty = True
            return

        self._album_dirty = False
        for child in self.album_items_container.winfo_children():
            child.destroy()

        display_list = self._get_filtered_album_files()
        total_items = len(display_list)

        if total_items == 0:
            msg = "No files match search filter." if self._search_filter_text else "No photos or videos found in folder."
            lbl = ctk.CTkLabel(
                self.album_items_container,
                text=msg,
                font=ctk.CTkFont(size=11),
                text_color="#94a3b8"
            )
            lbl.pack(pady=20)
            self.lbl_album_info.configure(text="📁 0 media files")
            self.lbl_album_page.configure(text="Page 0 / 0")
            return

        total_pages = max(1, (total_items + self.ALBUM_PAGE_SIZE - 1) // self.ALBUM_PAGE_SIZE)
        self.album_page = max(0, min(self.album_page, total_pages - 1))

        folder_name = os.path.basename(self._current_album_dir) if self._current_album_dir else "Folder"
        self.lbl_album_info.configure(text=f"📁 {folder_name} ({total_items:,} files)")
        self.lbl_album_page.configure(text=f"Page {self.album_page + 1} / {total_pages}")

        start_idx = self.album_page * self.ALBUM_PAGE_SIZE
        end_idx = min(start_idx + self.ALBUM_PAGE_SIZE, total_items)
        page_items = display_list[start_idx:end_idx]

        for fpath in page_items:
            fname = os.path.basename(fpath)
            ext = os.path.splitext(fname)[1].lower().replace(".", "").upper()
            is_vid = f".{ext.lower()}" in SUPPORTED_VIDEO_EXTENSIONS
            is_active = (fpath == self.current_file_path)

            row_frame = ctk.CTkFrame(
                self.album_items_container,
                fg_color="#312e81" if is_active else "#1e293b",
                border_width=1 if is_active else 0,
                border_color="#818cf8" if is_active else "#1e293b",
                corner_radius=6
            )
            row_frame.pack(fill="x", pady=2)

            badge_color = "#e11d48" if is_vid else ("#4f46e5" if "HEIC" in ext else "#334155")
            lbl_badge = ctk.CTkLabel(
                row_frame,
                text=f"{'🎬' if is_vid else ''}{ext[:4]}",
                font=ctk.CTkFont(size=9, weight="bold"),
                fg_color=badge_color,
                corner_radius=4,
                width=38,
                height=18
            )
            lbl_badge.pack(side="left", padx=(4, 6), pady=4)

            btn = ctk.CTkButton(
                row_frame,
                text=fname,
                command=lambda p=fpath: self._on_album_item_clicked(p),
                fg_color="transparent",
                hover_color="#475569",
                height=26,
                anchor="w",
                font=ctk.CTkFont(size=11, weight="bold" if is_active else "normal"),
                text_color="#ffffff" if is_active else "#cbd5e1"
            )
            btn.pack(side="left", fill="x", expand=True)

    def _populate_status_bar(self):
        # Left: Resolution & Specs
        self.lbl_status_res = ctk.CTkLabel(
            self.status_bar,
            text="Gallery Cube • Drag & drop photos or videos anywhere",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.lbl_status_res.pack(side="left", padx=12)

        # Center: Album Navigation & Delete
        self.album_nav_frame = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        self.album_nav_frame.pack(side="left", expand=True)

        self.btn_prev = ctk.CTkButton(
            self.album_nav_frame,
            text="◀ Prev",
            command=self.prev_photo,
            width=50,
            height=24,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=10)
        )
        self.btn_prev.pack(side="left", padx=4)

        self.lbl_album_counter = ctk.CTkLabel(
            self.album_nav_frame,
            text="— / —",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#e2e8f0"
        )
        self.lbl_album_counter.pack(side="left", padx=8)

        self.btn_next = ctk.CTkButton(
            self.album_nav_frame,
            text="Next ▶",
            command=self.next_photo,
            width=50,
            height=24,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=10)
        )
        self.btn_next.pack(side="left", padx=4)

        btn_trash = ctk.CTkButton(
            self.album_nav_frame,
            text="🗑️ Delete (Del)",
            command=self.delete_current_file,
            width=80,
            height=24,
            fg_color="#1e293b",
            hover_color="#ef4444",
            font=ctk.CTkFont(size=10)
        )
        btn_trash.pack(side="left", padx=8)

        # Right: Camera Badge & Zoom Controls
        self.lbl_camera_badge = ctk.CTkLabel(
            self.status_bar,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#818cf8"
        )
        self.lbl_camera_badge.pack(side="right", padx=(0, 16))

        self.zoom_controls_frame = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        self.zoom_controls_frame.pack(side="right")

        btn_zoom_in = ctk.CTkButton(
            self.zoom_controls_frame,
            text="+",
            command=lambda: self.canvas_view.zoom_by(1.2),
            width=28,
            height=22,
            fg_color="#334155",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        btn_zoom_in.pack(side="right", padx=2)

        btn_zoom_100 = ctk.CTkButton(
            self.zoom_controls_frame,
            text="100%",
            command=self.canvas_view.actual_size,
            width=42,
            height=22,
            fg_color="#334155",
            font=ctk.CTkFont(size=10)
        )
        btn_zoom_100.pack(side="right", padx=2)

        btn_zoom_fit = ctk.CTkButton(
            self.zoom_controls_frame,
            text="Fit",
            command=self.canvas_view.fit_to_screen,
            width=36,
            height=22,
            fg_color="#334155",
            font=ctk.CTkFont(size=10)
        )
        btn_zoom_fit.pack(side="right", padx=2)

        btn_zoom_out = ctk.CTkButton(
            self.zoom_controls_frame,
            text="−",
            command=lambda: self.canvas_view.zoom_by(0.8),
            width=28,
            height=22,
            fg_color="#334155",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        btn_zoom_out.pack(side="right", padx=2)

    def _setup_drag_and_drop(self):
        """Native Windows drag & drop hook using windnd."""
        try:
            windnd.hook_dropfiles(self, func=self._on_files_dropped)
        except Exception as e:
            print("Drag and drop hook warning:", e)

    def _on_files_dropped(self, files):
        if not files:
            return
        # Decode byte paths if delivered as bytes
        first = files[0].decode("utf-8", errors="ignore") if isinstance(files[0], bytes) else files[0]
        if os.path.isdir(first):
            self._load_album_from_dir(first)
            if self.album_files:
                self.load_media_path(self.album_files[0])
        elif os.path.isfile(first):
            directory = os.path.dirname(first)
            # Load active media FIRST for instantaneous response (<50ms)
            self.load_media_path(first)
            self.after(20, lambda: self._load_album_from_dir(directory, active_file=first))

    def _bind_shortcuts(self):
        self.bind("<Control-o>", lambda e: self.open_file_dialog())
        self.bind("<Control-s>", lambda e: self.save_as_dialog())
        self.bind("<Control-e>", lambda e: self.quick_export_jpg())
        self.bind("<Control-c>", lambda e: self.copy_to_clipboard_action())
        self.bind("<Control-z>", lambda e: self.handle_undo())
        self.bind("<Control-y>", lambda e: self.handle_redo())
        self.bind("<Control-i>", lambda e: self.open_exif_dialog())
        self.bind("<Control-b>", lambda e: self.open_batch_dialog())
        self.bind("<e>", lambda e: self.toggle_edit_panel())
        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._on_escape())
        self.bind("<Tab>", lambda e: self.toggle_zen_mode())
        self.bind("<h>", lambda e: self.toggle_zen_mode())
        self.bind("<F5>", lambda e: self.toggle_slideshow())
        self.bind("<Delete>", lambda e: self.delete_current_file())
        self.bind("<Left>", lambda e: self.prev_photo())
        self.bind("<Right>", lambda e: self.next_photo())
        self.bind("<space>", lambda e: self._on_spacebar())
        self.bind("<plus>", lambda e: self.canvas_view.zoom_by(1.2))
        self.bind("<equal>", lambda e: self.canvas_view.zoom_by(1.2))
        self.bind("<minus>", lambda e: self.canvas_view.zoom_by(0.8))
        self.bind("<Control-0>", lambda e: self.canvas_view.fit_to_screen())

    def show_toast(self, message: str, duration_ms: int = 2500):
        """Displays floating pill notification."""
        self.toast_banner.configure(text=f"  {message}  ")
        self.toast_banner.place(relx=0.5, rely=0.08, anchor="center")
        self.toast_banner.lift()
        if self._toast_timer:
            self.after_cancel(self._toast_timer)
        self._toast_timer = self.after(duration_ms, lambda: self.toast_banner.place_forget())

    def _on_escape(self):
        if self.is_fullscreen:
            self.toggle_fullscreen()
        elif self.is_zen_mode:
            self.toggle_zen_mode()
        elif self.is_slideshow:
            self.toggle_slideshow()

    def _on_spacebar(self):
        if self.current_media_type == "video":
            self.video_player.toggle_play_pause()
        elif self.is_slideshow:
            self.toggle_slideshow()

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        if self.is_fullscreen:
            self.show_toast("Fullscreen Enabled (Press F11 or Esc to exit)")
        self.update_idletasks()

    def toggle_edit_panel(self):
        """Toggles the editing tools drawer on/off (E key)."""
        self.is_edit_panel_visible = not self.is_edit_panel_visible
        if self.is_edit_panel_visible:
            self.sidebar_frame.pack(side="left", fill="y", before=self.viewport_container)
            self.btn_toggle_edit.configure(fg_color="#4f46e5", text="🎨 Edit (Active)")
            self.show_toast("Edit Studio Opened (Press E to close)")
        else:
            self.sidebar_frame.pack_forget()
            self.btn_toggle_edit.configure(fg_color="#334155", text="🎨 Edit Tools (E)")
            self.show_toast("Edit Studio Closed")

    def toggle_filmstrip(self):
        """Toggles horizontal footer filmstrip preview."""
        self.is_filmstrip_visible = not self.is_filmstrip_visible
        if self.is_filmstrip_visible:
            self.filmstrip.pack(fill="x", side="bottom", before=self.status_bar)
            self.btn_toggle_filmstrip.configure(fg_color="#4f46e5")
            self.show_toast("Filmstrip Shown")
        else:
            self.filmstrip.pack_forget()
            self.btn_toggle_filmstrip.configure(fg_color="#334155")
            self.show_toast("Filmstrip Hidden")

    def _on_filmstrip_item_clicked(self, file_path: str):
        """Called when a thumbnail in the footer filmstrip is clicked."""
        if file_path in self.album_files:
            self.album_index = self.album_files.index(file_path)
            self._update_album_counter()
        self.load_media_path(file_path)
        self.filmstrip.set_active_index(self.album_index)
        if self.is_edit_panel_visible and hasattr(self, "tabview") and self.tabview.get() == "Album & Thumbnails":
            self._render_album_page()

    def toggle_zen_mode(self):
        """Cinema / Zen mode: collapses sidebar and toolbar for 100% clean viewing."""
        self.is_zen_mode = not self.is_zen_mode
        if self.is_zen_mode:
            if self.is_edit_panel_visible:
                self.sidebar_frame.pack_forget()
            self.toolbar.pack_forget()
            if self.is_filmstrip_visible:
                self.filmstrip.pack_forget()
            self.status_bar.pack_forget()
            self.show_toast("Cinema View Enabled (Press Tab or Esc to restore controls)")
        else:
            self.toolbar.pack(fill="x", side="top", before=self.workspace)
            if self.is_edit_panel_visible:
                self.sidebar_frame.pack(side="left", fill="y", before=self.viewport_container)
            if self.is_filmstrip_visible:
                self.filmstrip.pack(fill="x", side="bottom", before=self.status_bar)
            self.status_bar.pack(fill="x", side="bottom")

    def toggle_slideshow(self):
        self.is_slideshow = not self.is_slideshow
        if self.is_slideshow:
            self.show_toast("▶ Slideshow Started (Press Space or Esc to stop)")
            self._run_slideshow_step()
        else:
            if self._slideshow_timer:
                self.after_cancel(self._slideshow_timer)
                self._slideshow_timer = None
            self.show_toast("Slideshow Stopped")

    def _run_slideshow_step(self):
        if not self.is_slideshow:
            return
        self.next_photo()
        self._slideshow_timer = self.after(3500, self._run_slideshow_step)

    def copy_to_clipboard_action(self):
        """Copies active image or video frame to Windows Clipboard (Ctrl+C)."""
        target_img = None
        if self.current_media_type == "video":
            target_img = self.video_player.engine.current_pil_frame
        else:
            target_img = self.image_engine.get_full_rendered_image()

        if target_img:
            ok = copy_image_to_clipboard(target_img)
            if ok:
                self.show_toast("✓ Copied image to Windows clipboard! (Paste anywhere with Ctrl+V)")
            else:
                self.show_toast("Failed to copy image to clipboard")
        else:
            self.show_toast("No media loaded to copy")

    def delete_current_file(self):
        """Safely moves current file to Windows Recycle Bin."""
        if not self.current_file_path or not os.path.exists(self.current_file_path):
            self.show_toast("No file loaded to delete")
            return

        fname = os.path.basename(self.current_file_path)
        if messagebox.askyesno("Send to Recycle Bin", f"Are you sure you want to move:\n\n{fname}\n\nto the Windows Recycle Bin?"):
            fpath = self.current_file_path
            ok = send_to_recycle_bin(fpath)
            if ok:
                self.show_toast(f"🗑️ Moved {fname} to Recycle Bin")
                # Remove from album list and advance to next
                if fpath in self.album_files:
                    idx = self.album_files.index(fpath)
                    self.album_files.remove(fpath)
                    if self.album_files:
                        self.album_index = min(idx, len(self.album_files) - 1)
                        self._update_album_counter()
                        self.load_media_path(self.album_files[self.album_index])
                    else:
                        self.album_index = -1
                        self._update_album_counter()
            else:
                messagebox.showerror("Error", f"Could not move {fname} to Recycle Bin.")

    # ================= Media Loading =================

    def load_media_path(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        self.current_file_path = file_path

        if hasattr(self, "filmstrip") and file_path in self.album_files:
            self.album_index = self.album_files.index(file_path)
            self.filmstrip.set_active_index(self.album_index)

        if ext in SUPPORTED_VIDEO_EXTENSIONS:
            self._load_video(file_path)
        else:
            self._load_photo(file_path)

    def _load_video(self, file_path: str):
        self.current_media_type = "video"

        # Switch viewport to Video Player
        self.canvas_view.pack_forget()
        self.video_player.pack(fill="both", expand=True)
        self.zoom_controls_frame.pack_forget()

        ok, msg = self.video_player.load_video_file(file_path)
        if not ok:
            messagebox.showerror("Video Error", msg)
            return

        meta = self.video_player.engine.get_metadata()
        fname = meta["Filename"]
        ext = os.path.splitext(fname)[1].upper().replace(".", "")

        self.title(f"{fname} [🎬 {ext} Video] — {meta['Resolution']} — Gallery Cube")
        self.lbl_status_res.configure(
            text=f"🎬 {fname}  •  {meta['Resolution']}  •  {meta['FPS']}  •  {meta['Duration']}  •  {meta['FileSize']}"
        )
        self.lbl_camera_badge.configure(text=f"🎬 {ext} Video")

    def _load_photo(self, file_path: str):
        self.current_media_type = "photo"

        # Stop and hide video player
        self.video_player.stop()
        self.video_player.pack_forget()
        self.canvas_view.pack(fill="both", expand=True)
        self.zoom_controls_frame.pack(side="right")

        ok, msg = self.image_engine.load_file(file_path)
        if not ok:
            messagebox.showerror("Failed to Open File", msg)
            return

        self.metadata = parse_exif_metadata(self.image_engine.master_image)
        preview = self.image_engine.get_preview_image()
        self.canvas_view.set_image(preview, reset_zoom=True)

        w, h = self.image_engine.dimensions
        mp = round((w * h) / 1_000_000, 1)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        fname = os.path.basename(file_path)
        ext = os.path.splitext(fname)[1].upper().replace(".", "")

        self.title(f"{fname} [{ext}] — {w} × {h} ({mp} MP) — Gallery Cube")
        self.lbl_status_res.configure(
            text=f"{fname}  •  {ext}  •  {w} × {h} ({mp} MP)  •  {file_size_mb:.2f} MB"
        )

        dev_title = self.metadata.get("DeviceTitle", "")
        if dev_title and dev_title != "Unknown Camera / Device":
            self.lbl_camera_badge.configure(text=f"📷 {dev_title}")
        else:
            self.lbl_camera_badge.configure(text="")

        self.panel_transforms.update_dimensions(w, h)
        self.panel_adjustments.sync_values(self.image_engine.adjustments)

    def open_extracted_frame(self, frame_pil: Image.Image, frame_title: str):
        """Called by video player when user clicks 'Edit Frame in Studio'."""
        self.current_media_type = "photo"
        self.video_player.stop()
        self.video_player.pack_forget()
        self.canvas_view.pack(fill="both", expand=True)
        self.zoom_controls_frame.pack(side="right")

        self.image_engine.master_image = frame_pil.copy()
        self.image_engine.transformed_master = frame_pil.copy()
        self.image_engine.file_path = f"{frame_title}.png"
        self.image_engine._rebuild_proxy()
        self.image_engine.undo_stack.clear()
        self.image_engine.redo_stack.clear()
        self.image_engine._save_state("Extract Video Frame")

        preview = self.image_engine.get_preview_image()
        self.canvas_view.set_image(preview, reset_zoom=True)
        w, h = self.image_engine.dimensions
        self.panel_transforms.update_dimensions(w, h)
        self.title(f"{frame_title} [Extracted Video Frame] — Gallery Cube")
        self.lbl_status_res.configure(text=f"Extracted Frame: {w} × {h} ({round((w*h)/1_000_000, 1)} MP)")
        self.lbl_camera_badge.configure(text="🎬 Video Frame")
        self.tabview.set("Adjust")
        self.show_toast("✓ Video frame loaded into Photo Studio!")

    # ================= Album & File Open Dialogs =================

    def open_file_dialog(self):
        file_path = filedialog.askopenfilename(
            title="Open Media in Gallery Cube",
            filetypes=[
                ("All Supported Media (Photos & Videos)", "*.heic;*.heif;*.hif;*.jpg;*.jpeg;*.jfif;*.png;*.webp;*.bmp;*.tiff;*.tif;*.gif;*.ico;*.avif;*.dng;*.mp4;*.mov;*.m4v;*.mkv;*.avi;*.webm"),
                ("Flagship HEIC / HEIF", "*.heic;*.heif;*.hif"),
                ("Mobile Videos (MP4, MOV, ProRes)", "*.mp4;*.mov;*.m4v;*.mkv;*.avi;*.webm"),
                ("JPEG Photos", "*.jpg;*.jpeg;*.jfif;*.jpe"),
                ("PNG Graphics", "*.png;*.apng"),
                ("WebP Modern Web", "*.webp"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            directory = os.path.dirname(file_path)
            # Load active media FIRST for instantaneous response (<50ms)
            self.load_media_path(file_path)
            self.after(20, lambda: self._load_album_from_dir(directory, active_file=file_path))

    def open_folder_dialog(self):
        directory = filedialog.askdirectory(title="Open Media Folder / Album")
        if directory:
            self._load_album_from_dir(directory)
            if self.album_files:
                self.load_media_path(self.album_files[0])

    def _load_album_from_dir(self, directory: str, active_file: Optional[str] = None):
        if not directory or not os.path.isdir(directory):
            return

        # If already scanned this exact directory, just update index without re-scanning
        if self._current_album_dir == directory and self.album_files:
            if active_file and active_file in self.album_files:
                self.album_index = self.album_files.index(active_file)
            self._update_album_counter()
            self._render_album_page()
            return

        self._current_album_dir = directory
        files = []
        try:
            with os.scandir(directory) as it:
                for entry in it:
                    if entry.is_file():
                        _, ext = os.path.splitext(entry.name)
                        if ext.lower() in ALL_SUPPORTED_EXTS_SET:
                            files.append(entry.path)
        except Exception as e:
            print("Directory scan error:", e)

        # Natural case-insensitive sort
        files.sort(key=lambda p: os.path.basename(p).lower())
        self.album_files = files

        if active_file and active_file in self.album_files:
            self.album_index = self.album_files.index(active_file)
        elif self.album_files:
            self.album_index = 0
        else:
            self.album_index = -1

        self.album_page = max(0, self.album_index // self.ALBUM_PAGE_SIZE) if self.album_index >= 0 else 0
        self._update_album_counter()
        self._render_album_page()
        if hasattr(self, "filmstrip"):
            self.filmstrip.set_files(self.album_files, self.album_index)

    def _on_album_item_clicked(self, fpath: str):
        if fpath in self.album_files:
            self.album_index = self.album_files.index(fpath)
            self._update_album_counter()
        self.load_media_path(fpath)
        self._render_album_page()
        if hasattr(self, "filmstrip"):
            self.filmstrip.set_active_index(self.album_index)

    def prev_photo(self):
        if not self.album_files:
            return
        if self.album_index > 0:
            self.album_index -= 1
        else:
            self.album_index = len(self.album_files) - 1
        self._update_album_counter()
        target_path = self.album_files[self.album_index]
        self.load_media_path(target_path)
        cur_page = self.album_index // self.ALBUM_PAGE_SIZE
        if cur_page != self.album_page:
            self.album_page = cur_page
        self._render_album_page()
        if hasattr(self, "filmstrip"):
            self.filmstrip.set_active_index(self.album_index)

    def next_photo(self):
        if not self.album_files:
            return
        if self.album_index < len(self.album_files) - 1:
            self.album_index += 1
        else:
            self.album_index = 0
        self._update_album_counter()
        target_path = self.album_files[self.album_index]
        self.load_media_path(target_path)
        cur_page = self.album_index // self.ALBUM_PAGE_SIZE
        if cur_page != self.album_page:
            self.album_page = cur_page
        self._render_album_page()
        if hasattr(self, "filmstrip"):
            self.filmstrip.set_active_index(self.album_index)

    def _update_album_counter(self):
        if not self.album_files:
            self.lbl_album_counter.configure(text="— / —")
        else:
            self.lbl_album_counter.configure(
                text=f"{self.album_index + 1:,} of {len(self.album_files):,}"
            )

    # ================= Adjustments & Transforms =================

    def on_adjustment_change(self, key: str, value: float):
        if self.current_media_type != "photo" or not self.image_engine.has_image:
            return
        self.image_engine.update_adjustment(key, value)
        preview = self.image_engine.get_preview_image()
        self.canvas_view.set_image(preview, reset_zoom=False)

    def on_adjustment_reset(self):
        if self.current_media_type != "photo" or not self.image_engine.has_image:
            return
        self.image_engine.reset_adjustments()
        preview = self.image_engine.get_preview_image()
        self.canvas_view.set_image(preview, reset_zoom=False)

    def on_select_preset(self, preset_name: str):
        if self.current_media_type != "photo" or not self.image_engine.has_image:
            return
        self.image_engine.apply_filter_preset(preset_name)
        self.panel_adjustments.sync_values(self.image_engine.adjustments)
        preview = self.image_engine.get_preview_image()
        self.canvas_view.set_image(preview, reset_zoom=False)

    def on_rotate(self, degrees: int):
        if self.current_media_type != "photo" or not self.image_engine.has_image:
            return
        self.image_engine.rotate(degrees)
        preview = self.image_engine.get_preview_image()
        self.canvas_view.set_image(preview, reset_zoom=True)
        w, h = self.image_engine.dimensions
        self.panel_transforms.update_dimensions(w, h)

    def on_flip(self, horizontal: bool):
        if self.current_media_type != "photo" or not self.image_engine.has_image:
            return
        self.image_engine.flip(horizontal)
        preview = self.image_engine.get_preview_image()
        self.canvas_view.set_image(preview, reset_zoom=False)

    def on_start_crop(self, aspect_ratio: Optional[float]):
        if self.current_media_type != "photo" or not self.image_engine.has_image:
            return
        self.canvas_view.start_crop(aspect_ratio)

    def on_apply_crop(self):
        if self.current_media_type != "photo" or not self.image_engine.has_image or not self.canvas_view.crop_active:
            return
        box = self.canvas_view.get_crop_pixel_box(self.image_engine.dimensions)
        self.canvas_view.cancel_crop()
        self.panel_transforms.hide_crop_actions()
        self.image_engine.crop(box)
        preview = self.image_engine.get_preview_image()
        self.canvas_view.set_image(preview, reset_zoom=True)
        w, h = self.image_engine.dimensions
        self.panel_transforms.update_dimensions(w, h)

    def on_cancel_crop(self):
        self.canvas_view.cancel_crop()
        self.panel_transforms.hide_crop_actions()

    def on_resize(self, width: int, height: int):
        if self.current_media_type != "photo" or not self.image_engine.has_image:
            return
        from PIL import Image
        self.image_engine.transformed_master = self.image_engine.transformed_master.resize(
            (width, height), Image.Resampling.LANCZOS
        )
        self.image_engine._rebuild_proxy()
        self.image_engine.redo_stack.clear()
        self.image_engine._save_state(f"Resize to {width} × {height}")
        preview = self.image_engine.get_preview_image()
        self.canvas_view.set_image(preview, reset_zoom=True)
        self.panel_transforms.update_dimensions(width, height)

    def handle_undo(self):
        if self.current_media_type != "photo":
            return
        if self.image_engine.undo():
            preview = self.image_engine.get_preview_image()
            self.canvas_view.set_image(preview, reset_zoom=False)
            w, h = self.image_engine.dimensions
            self.panel_transforms.update_dimensions(w, h)
            self.panel_adjustments.sync_values(self.image_engine.adjustments)

    def handle_redo(self):
        if self.current_media_type != "photo":
            return
        if self.image_engine.redo():
            preview = self.image_engine.get_preview_image()
            self.canvas_view.set_image(preview, reset_zoom=False)
            w, h = self.image_engine.dimensions
            self.panel_transforms.update_dimensions(w, h)
            self.panel_adjustments.sync_values(self.image_engine.adjustments)

    def handle_revert(self):
        if self.current_media_type != "photo" or not self.image_engine.has_image:
            return
        if messagebox.askyesno("Revert Changes", "Revert all transformations and color adjustments to the original imported image?"):
            self.image_engine.reset_transforms()
            preview = self.image_engine.get_preview_image()
            self.canvas_view.set_image(preview, reset_zoom=True)
            w, h = self.image_engine.dimensions
            self.panel_transforms.update_dimensions(w, h)
            self.panel_adjustments.sync_values(self.image_engine.adjustments)

    # ================= Export Dialogs =================

    def save_as_dialog(self):
        if self.current_media_type != "photo" or not self.image_engine.has_image:
            messagebox.showinfo("No Image", "Save As is available when an image is active.")
            return

        initial_name = "edited_image.png"
        if self.image_engine.file_path:
            base, ext = os.path.splitext(os.path.basename(self.image_engine.file_path))
            initial_name = f"{base}_edited{ext}"

        output_path = filedialog.asksaveasfilename(
            title="Save Image As...",
            initialfile=initial_name,
            filetypes=[
                ("PNG Lossless / Transparent", "*.png"),
                ("JPEG High Compatibility", "*.jpg"),
                ("Flagship HEIC / HEIF", "*.heic"),
                ("WebP Modern Web", "*.webp"),
                ("BMP Bitmap", "*.bmp"),
                ("TIFF Format", "*.tiff"),
                ("Windows Icon", "*.ico")
            ]
        )
        if not output_path:
            return

        rendered = self.image_engine.get_full_rendered_image()
        ok, msg = export_image(
            image=rendered,
            output_path=output_path,
            quality=95,
            raw_exif_bytes=self.image_engine.raw_exif_bytes,
            preserve_exif=True
        )
        if ok:
            self.show_toast(f"✓ Saved image: {os.path.basename(output_path)}")
        else:
            messagebox.showerror("Export Failed", msg)

    def quick_export_jpg(self):
        if self.current_media_type != "photo" or not self.image_engine.has_image:
            messagebox.showinfo("No Image", "Quick Export is available when an image is active.")
            return

        if self.image_engine.file_path:
            dirname = os.path.dirname(self.image_engine.file_path)
            base = os.path.splitext(os.path.basename(self.image_engine.file_path))[0]
            out_path = os.path.join(dirname, f"{base}_converted.jpg")
        else:
            out_path = os.path.join(os.path.expanduser("~"), "Pictures", "converted.jpg")

        rendered = self.image_engine.get_full_rendered_image()
        ok, msg = export_image(
            image=rendered,
            output_path=out_path,
            format_name="JPEG",
            quality=95,
            raw_exif_bytes=self.image_engine.raw_exif_bytes,
            preserve_exif=True
        )
        if ok:
            self.show_toast(f"✓ Quick exported: {os.path.basename(out_path)}")
        else:
            messagebox.showerror("Export Failed", msg)

    # ================= Dialog Popups =================

    def open_exif_dialog(self):
        if self.current_media_type == "video":
            meta = self.video_player.engine.get_metadata()
            msg = "\n".join([f"{k}: {v}" for k, v in meta.items()])
            messagebox.showinfo("Video Information", msg)
            return

        if not self.image_engine.has_image:
            messagebox.showinfo("No Image", "Please open an image first to inspect its EXIF data.")
            return

        ExifDialog(
            self,
            self.metadata,
            current_file_path=self.current_file_path,
            album_files=self.album_files,
            on_jump_to_file=self.load_media_path
        )

    def open_batch_dialog(self):
        BatchConverterDialog(self)

    def open_first_run_dialog(self):
        FirstRunDialog(
            self,
            on_applied=lambda count: self.show_toast(f"✓ Registered Gallery Cube as default viewer for {count} formats!")
        )

    def _toggle_theme(self):
        mode = ctk.get_appearance_mode()
        new_mode = "Light" if mode == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)

    def open_rmscube_feedback(self):
        """Open rmscube.com in default web browser to rate Gallery Cube and submit feature suggestions."""
        import webbrowser
        try:
            webbrowser.open("https://rmscube.com/#gallery-cube-feedback")
            self.show_toast("Opening rmscube.com feedback in browser...")
        except Exception as e:
            messagebox.showinfo("Feedback", "Please visit https://rmscube.com/#gallery-cube-feedback to rate and suggest features.")

    def _check_updates_quietly(self):
        """Quiet background update check on app launch; notifies via toast if an update is available."""
        try:
            from core.updater import check_for_updates_async
            def on_found(data):
                ver = data.get("latest_version", "New")
                self.after(0, lambda: self.show_toast(f"🎉 Update Available: Gallery Cube v{ver}! Click Rate/Feedback to download."))
            check_for_updates_async(on_update_found=on_found)
        except Exception:
            pass

    def check_for_updates_dialog(self):
        """Manual check for updates triggered by user."""
        try:
            from core.updater import check_for_updates_async, CURRENT_VERSION
            self.show_toast("Checking rmscube.com for updates...")
            def on_found(data):
                ver = data.get("latest_version", "New")
                notes = "\n• " + "\n• ".join(data.get("changelog", []))
                msg = f"Gallery Cube v{ver} is now available!\n\nWhat's new in v{ver}:{notes}\n\nWould you like to open rmscube.com to download the update?"
                def _prompt():
                    if messagebox.askyesno("Update Available", msg):
                        import webbrowser
                        webbrowser.open(data.get("download_url", "https://rmscube.com/#gallery-cube"))
                self.after(0, _prompt)

            def on_up_to_date():
                self.after(0, lambda: messagebox.showinfo("Up to Date", f"Gallery Cube v{CURRENT_VERSION} is the latest version available."))

            check_for_updates_async(on_update_found=on_found, on_up_to_date=on_up_to_date)
        except Exception as e:
            messagebox.showerror("Update Check Failed", f"Could not check for updates: {e}")
