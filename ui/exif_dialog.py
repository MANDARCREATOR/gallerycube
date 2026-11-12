"""
EXIF Metadata Inspector & Photo Geo-Map Dialog for Gallery Cube 🧊.
Visualizes camera specs, lens parameters, ISO, shutter speed, capture date,
and provides an interactive OpenStreetMap embedding showing this photo and
all other photos in the album taken on the visible map.
"""
import os
import queue
import threading
import webbrowser
from typing import Dict, Any, List, Optional, Callable
from PIL import Image
import customtkinter as ctk

try:
    import tkintermapview
    HAS_MAP = True
except ImportError:
    HAS_MAP = False

from core.exif_reader import parse_exif_metadata


class ExifDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        metadata: Dict[str, Any],
        current_file_path: Optional[str] = None,
        album_files: Optional[List[str]] = None,
        on_jump_to_file: Optional[Callable[[str], None]] = None
    ):
        super().__init__(master)
        self.metadata = metadata
        self.current_file_path = current_file_path
        self.album_files = album_files or []
        self.on_jump_to_file = on_jump_to_file

        self.title("Gallery Cube 🧊 — Shot Details & Photo Map")
        self.geometry("620x720")
        self.minsize(560, 640)
        self.configure(fg_color="#0f172a")

        # Map state & thread-safe queue
        self.map_widget = None
        self.markers = []
        self._album_geo_items = []
        self._geo_queue = queue.Queue()

        # Center dialog on master
        self.transient(master)
        self.grab_set()

        self._build_ui()
        self._poll_geo_queue()

    def _build_ui(self):
        # 1. Top Header with Camera Icon & Filename
        header = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=12)
        header.pack(fill="x", padx=16, pady=(16, 8))

        lbl_device = ctk.CTkLabel(
            header,
            text=f"📷 {self.metadata.get('DeviceTitle', 'Camera Unknown')}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f8fafc"
        )
        lbl_device.pack(anchor="w", padx=14, pady=(12, 2))

        sub_info = self.metadata.get("Lens") or "Primary Sensor"
        if self.current_file_path:
            sub_info = f"{os.path.basename(self.current_file_path)}  •  {sub_info}"

        lbl_lens = ctk.CTkLabel(
            header,
            text=sub_info,
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        lbl_lens.pack(anchor="w", padx=14, pady=(0, 12))

        # 2. Main Tabview: Specs vs Photo Map
        has_gps = bool(self.metadata.get("GPS"))
        self.tabview = ctk.CTkTabview(self, fg_color="#1e293b", corner_radius=12)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=4)

        tab_specs = self.tabview.add("📋 Shot Specs")
        tab_map = self.tabview.add("🗺️ Photo Map & Geotags" + (" (Active)" if has_gps else ""))

        self._build_specs_tab(tab_specs)
        self._build_map_tab(tab_map, has_gps)

        # 3. Footer with Close & Copy buttons
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(8, 14))

        btn_copy = ctk.CTkButton(
            footer,
            text="📋 Copy All Metadata",
            command=self._copy_metadata,
            fg_color="#334155",
            hover_color="#475569",
            height=32,
            font=ctk.CTkFont(size=11)
        )
        btn_copy.pack(side="left")

        btn_close = ctk.CTkButton(
            footer,
            text="Close",
            command=self.destroy,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            height=32,
            width=90,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        btn_close.pack(side="right")

    def _build_specs_tab(self, parent):
        # 4-Tile Grid for Key Exposure Parameters
        exposure_frame = ctk.CTkFrame(parent, fg_color="transparent")
        exposure_frame.pack(fill="x", padx=8, pady=(8, 4))

        tiles = [
            ("Aperture", self.metadata.get("Aperture") or "—"),
            ("Shutter Speed", self.metadata.get("ExposureTime") or "—"),
            ("ISO Sensitivity", self.metadata.get("ISO") or "—"),
            ("Focal Length", self.metadata.get("FocalLength") or "—"),
        ]

        for i, (title, val) in enumerate(tiles):
            tile = ctk.CTkFrame(exposure_frame, fg_color="#0f172a", corner_radius=8)
            tile.grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="nsew")
            exposure_frame.columnconfigure(i % 2, weight=1)

            lbl_t = ctk.CTkLabel(tile, text=title, font=ctk.CTkFont(size=10), text_color="#94a3b8")
            lbl_t.pack(anchor="w", padx=10, pady=(6, 1))

            lbl_v = ctk.CTkLabel(tile, text=val, font=ctk.CTkFont(size=13, weight="bold"), text_color="#e0e7ff")
            lbl_v.pack(anchor="w", padx=10, pady=(0, 6))

        # Details List in Scrollable Frame
        list_frame = ctk.CTkScrollableFrame(parent, fg_color="#0f172a", corner_radius=8, height=220)
        list_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        gps_info = self.metadata.get("GPS")
        details = [
            ("Resolution", self.metadata.get("Resolution")),
            ("Date Taken", self.metadata.get("DateTime")),
            ("35mm Equivalent", self.metadata.get("FocalLength35mm")),
            ("White Balance", self.metadata.get("WhiteBalance")),
            ("Flash Mode", self.metadata.get("Flash")),
            ("Software / OS", self.metadata.get("Software")),
            ("Color Space", self.metadata.get("ColorMode")),
            ("GPS Coordinates", gps_info["Formatted"] if gps_info else "No GPS tag"),
        ]

        for label, val in details:
            if val and val != "Unknown":
                row = ctk.CTkFrame(list_frame, fg_color="transparent")
                row.pack(fill="x", padx=6, pady=4)

                lbl_name = ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=11), text_color="#94a3b8")
                lbl_name.pack(side="left")

                lbl_val = ctk.CTkLabel(row, text=str(val), font=ctk.CTkFont(size=11, weight="bold"), text_color="#f8fafc")
                lbl_val.pack(side="right")

    def _build_map_tab(self, parent, has_gps: bool):
        gps_info = self.metadata.get("GPS")

        # Top Control Bar for Map
        map_bar = ctk.CTkFrame(parent, fg_color="transparent")
        map_bar.pack(fill="x", padx=8, pady=(6, 4))

        if gps_info:
            lbl_coord = ctk.CTkLabel(
                map_bar,
                text=f"📍 {gps_info['Formatted']}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#34d399"
            )
            lbl_coord.pack(side="left")

            btn_gmaps = ctk.CTkButton(
                map_bar,
                text="🌐 Open Google Maps",
                command=lambda: webbrowser.open(gps_info["MapsUrl"]),
                fg_color="#334155",
                hover_color="#475569",
                height=26,
                font=ctk.CTkFont(size=10)
            )
            btn_gmaps.pack(side="right", padx=4)

            btn_fit = ctk.CTkButton(
                map_bar,
                text="🎯 Reset View",
                command=self._center_current_photo,
                fg_color="#4f46e5",
                hover_color="#4338ca",
                height=26,
                font=ctk.CTkFont(size=10, weight="bold")
            )
            btn_fit.pack(side="right", padx=4)
        else:
            lbl_coord = ctk.CTkLabel(
                map_bar,
                text="ℹ Current photo has no embedded GPS coordinates.",
                font=ctk.CTkFont(size=11),
                text_color="#94a3b8"
            )
            lbl_coord.pack(side="left")

        # Map Frame Container
        map_container = ctk.CTkFrame(parent, fg_color="#0f172a", corner_radius=10)
        map_container.pack(fill="both", expand=True, padx=8, pady=4)

        if HAS_MAP:
            self.map_widget = tkintermapview.TkinterMapView(
                map_container,
                corner_radius=10
            )
            self.map_widget.pack(fill="both", expand=True, padx=4, pady=4)

            # Center position
            if gps_info:
                lat, lon = gps_info["Latitude"], gps_info["Longitude"]
                self.map_widget.set_position(lat, lon)
                self.map_widget.set_zoom(15)

                # Set distinct marker for CURRENT photo (Red/Indigo Pin)
                fname = os.path.basename(self.current_file_path) if self.current_file_path else "Active Photo"
                m_current = self.map_widget.set_marker(
                    lat, lon,
                    text=f"📍 Current: {fname}",
                    marker_color_circle="#4f46e5",
                    marker_color_outside="#ef4444"
                )
                m_current.file_path = self.current_file_path
                self.markers.append(m_current)

            # Status label for nearby photos
            self.lbl_nearby_status = ctk.CTkLabel(
                parent,
                text="Scanning album for nearby mapped photos...",
                font=ctk.CTkFont(size=10),
                text_color="#94a3b8"
            )
            self.lbl_nearby_status.pack(fill="x", padx=12, pady=(2, 6))

            # Start background scanner for other photos in album with GPS
            threading.Thread(target=self._async_scan_album_gps, daemon=True).start()

        else:
            lbl_nomap = ctk.CTkLabel(
                map_container,
                text="Map component (tkintermapview) is not installed.\nInstall with: pip install tkintermapview",
                font=ctk.CTkFont(size=12),
                text_color="#94a3b8"
            )
            lbl_nomap.pack(expand=True, pady=40)

    def _center_current_photo(self):
        gps_info = self.metadata.get("GPS")
        if self.map_widget and gps_info:
            self.map_widget.set_position(gps_info["Latitude"], gps_info["Longitude"])
            self.map_widget.set_zoom(15)

    def _poll_geo_queue(self):
        """Thread-safe queue processor on Tkinter main thread."""
        try:
            while not self._geo_queue.empty():
                action, data = self._geo_queue.get_nowait()
                if action == "status" and hasattr(self, "lbl_nearby_status"):
                    self.lbl_nearby_status.configure(text=data)
                elif action == "marker":
                    fpath, fname, lat, lon = data
                    self._add_album_marker(fpath, fname, lat, lon)
        except Exception:
            pass
        if self.winfo_exists():
            self.after(100, self._poll_geo_queue)

    def _async_scan_album_gps(self):
        if not self.album_files:
            self._geo_queue.put(("status", "No additional files in album."))
            return

        current_path_norm = os.path.normpath(self.current_file_path) if self.current_file_path else ""
        mapped_count = 0

        # Scan album files (up to 300 files)
        scan_list = self.album_files[:300]
        for fpath in scan_list:
            if os.path.normpath(fpath) == current_path_norm:
                continue
            if not fpath.lower().endswith((".heic", ".heif", ".jpg", ".jpeg", ".png")):
                continue

            try:
                with Image.open(fpath) as im:
                    meta = parse_exif_metadata(im)
                    gps = meta.get("GPS")
                    if gps:
                        lat, lon = gps["Latitude"], gps["Longitude"]
                        fname = os.path.basename(fpath)
                        self._album_geo_items.append((fpath, fname, lat, lon))
                        mapped_count += 1
                        self._geo_queue.put(("marker", (fpath, fname, lat, lon)))
            except Exception:
                pass

        total_scanned = len(scan_list)
        msg = f"✓ Found {mapped_count} other photos with GPS tags in album (scanned {total_scanned} files)."
        self._geo_queue.put(("status", msg))

    def _add_album_marker(self, fpath: str, fname: str, lat: float, lon: float):
        if not self.map_widget:
            return
        try:
            marker = self.map_widget.set_marker(
                lat, lon,
                text=f"📷 {fname}",
                marker_color_circle="#0284c7",
                marker_color_outside="#38bdf8",
                command=self._on_marker_clicked
            )
            marker.file_path = fpath
            self.markers.append(marker)
        except Exception:
            pass

    def _on_marker_clicked(self, marker):
        fpath = getattr(marker, "file_path", None)
        if fpath and self.on_jump_to_file:
            fname = os.path.basename(fpath)
            # Ask or directly jump
            self.on_jump_to_file(fpath)
            self.destroy()

    def _copy_metadata(self):
        lines = [f"{k}: {v}" for k, v in self.metadata.items() if k != "AllTags"]
        text = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
