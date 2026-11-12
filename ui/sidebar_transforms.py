"""
Sidebar Transformations Panel for HEIC Studio Pro.
Handles Rotation, Flipping, Aspect-Ratio Cropping, and Pixel Resizing.
"""
from typing import Callable, Optional, Tuple
import customtkinter as ctk


class SidebarTransforms(ctk.CTkScrollableFrame):
    def __init__(
        self,
        master,
        on_rotate: Callable[[int], None],
        on_flip: Callable[[bool], None],
        on_start_crop: Callable[[Optional[float]], None],
        on_apply_crop: Callable[[], None],
        on_cancel_crop: Callable[[], None],
        on_resize: Callable[[int, int], None],
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.on_rotate = on_rotate
        self.on_flip = on_flip
        self.on_start_crop = on_start_crop
        self.on_apply_crop = on_apply_crop
        self.on_cancel_crop = on_cancel_crop
        self.on_resize = on_resize

        self.current_width = 0
        self.current_height = 0
        self.maintain_aspect = True

        self._build_ui()

    def _build_ui(self):
        # 1. Rotate & Flip Section
        header1 = ctk.CTkLabel(
            self,
            text="Orientation & Geometry",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        header1.pack(anchor="w", padx=10, pady=(5, 8))

        # Rotate buttons row
        rot_frame = ctk.CTkFrame(self, fg_color="transparent")
        rot_frame.pack(fill="x", padx=8, pady=4)

        btn_rot_cw = ctk.CTkButton(
            rot_frame,
            text="↻ Rotate 90° CW",
            command=lambda: self.on_rotate(90),
            fg_color="#1e293b",
            hover_color="#334155",
            border_width=1,
            border_color="#334155",
            height=32,
            font=ctk.CTkFont(size=11)
        )
        btn_rot_cw.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_rot_ccw = ctk.CTkButton(
            rot_frame,
            text="↺ Rotate 90° CCW",
            command=lambda: self.on_rotate(270),
            fg_color="#1e293b",
            hover_color="#334155",
            border_width=1,
            border_color="#334155",
            height=32,
            font=ctk.CTkFont(size=11)
        )
        btn_rot_ccw.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Flip buttons row
        flip_frame = ctk.CTkFrame(self, fg_color="transparent")
        flip_frame.pack(fill="x", padx=8, pady=4)

        btn_flip_h = ctk.CTkButton(
            flip_frame,
            text="⇆ Flip Horizontal",
            command=lambda: self.on_flip(True),
            fg_color="#1e293b",
            hover_color="#334155",
            border_width=1,
            border_color="#334155",
            height=32,
            font=ctk.CTkFont(size=11)
        )
        btn_flip_h.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_flip_v = ctk.CTkButton(
            flip_frame,
            text="⇅ Flip Vertical",
            command=lambda: self.on_flip(False),
            fg_color="#1e293b",
            hover_color="#334155",
            border_width=1,
            border_color="#334155",
            height=32,
            font=ctk.CTkFont(size=11)
        )
        btn_flip_v.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # 2. Crop Section
        sep = ctk.CTkFrame(self, height=1, fg_color="#334155")
        sep.pack(fill="x", padx=8, pady=16)

        header2 = ctk.CTkLabel(
            self,
            text="Interactive Crop",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        header2.pack(anchor="w", padx=10, pady=(0, 8))

        lbl_aspect = ctk.CTkLabel(
            self,
            text="Aspect Ratio Preset:",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        lbl_aspect.pack(anchor="w", padx=10, pady=(0, 4))

        self.aspect_var = ctk.StringVar(value="Free (Custom)")
        self.aspect_menu = ctk.CTkOptionMenu(
            self,
            values=[
                "Free (Custom)",
                "1:1 Square (Instagram)",
                "4:3 Flagship Photo",
                "16:9 Cinematic Landscape",
                "9:16 Story / Reel",
                "3:2 Classic Photo"
            ],
            variable=self.aspect_var,
            command=self._on_aspect_change,
            fg_color="#1e293b",
            button_color="#334155",
            button_hover_color="#475569"
        )
        self.aspect_menu.pack(fill="x", padx=8, pady=4)

        # Start Crop / Apply / Cancel buttons
        self.btn_toggle_crop = ctk.CTkButton(
            self,
            text="✂ Start Crop Mode",
            command=self._handle_start_crop,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            height=34,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_toggle_crop.pack(fill="x", padx=8, pady=6)

        self.crop_action_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.btn_apply = ctk.CTkButton(
            self.crop_action_frame,
            text="✓ Apply Crop",
            command=self.on_apply_crop,
            fg_color="#10b981",
            hover_color="#059669",
            height=32,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_apply.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_cancel = ctk.CTkButton(
            self.crop_action_frame,
            text="✕ Cancel",
            command=self.on_cancel_crop,
            fg_color="#ef4444",
            hover_color="#dc2626",
            height=32,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_cancel.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # 3. Resize Section
        sep2 = ctk.CTkFrame(self, height=1, fg_color="#334155")
        sep2.pack(fill="x", padx=8, pady=16)

        header3 = ctk.CTkLabel(
            self,
            text="Resize & Scaling",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        header3.pack(anchor="w", padx=10, pady=(0, 8))

        dims_frame = ctk.CTkFrame(self, fg_color="transparent")
        dims_frame.pack(fill="x", padx=8, pady=4)

        self.entry_w = ctk.CTkEntry(dims_frame, placeholder_text="Width", width=90)
        self.entry_w.pack(side="left", padx=(0, 4))
        self.entry_w.bind("<KeyRelease>", self._on_width_input)

        lbl_x = ctk.CTkLabel(dims_frame, text="×", font=ctk.CTkFont(size=14))
        lbl_x.pack(side="left", padx=2)

        self.entry_h = ctk.CTkEntry(dims_frame, placeholder_text="Height", width=90)
        self.entry_h.pack(side="left", padx=(4, 0))
        self.entry_h.bind("<KeyRelease>", self._on_height_input)

        self.check_aspect = ctk.CTkCheckBox(
            self,
            text="Maintain aspect ratio",
            font=ctk.CTkFont(size=11),
            checkbox_height=18,
            checkbox_width=18,
            command=self._on_toggle_maintain
        )
        self.check_aspect.select()
        self.check_aspect.pack(anchor="w", padx=10, pady=6)

        # Scale shortcut buttons (50%, 25%)
        scale_btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        scale_btn_frame.pack(fill="x", padx=8, pady=4)

        btn_50 = ctk.CTkButton(
            scale_btn_frame,
            text="50% Size",
            command=lambda: self._scale_by(0.5),
            fg_color="#1e293b",
            hover_color="#334155",
            height=28,
            font=ctk.CTkFont(size=10)
        )
        btn_50.pack(side="left", fill="x", expand=True, padx=(0, 2))

        btn_25 = ctk.CTkButton(
            scale_btn_frame,
            text="25% Size",
            command=lambda: self._scale_by(0.25),
            fg_color="#1e293b",
            hover_color="#334155",
            height=28,
            font=ctk.CTkFont(size=10)
        )
        btn_25.pack(side="right", fill="x", expand=True, padx=(2, 0))

        btn_apply_resize = ctk.CTkButton(
            self,
            text="Apply Resize",
            command=self._handle_apply_resize,
            fg_color="#334155",
            hover_color="#475569",
            height=30,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        btn_apply_resize.pack(fill="x", padx=8, pady=(6, 12))

    def _get_selected_ratio(self) -> Optional[float]:
        val = self.aspect_var.get()
        if "1:1" in val:
            return 1.0
        elif "4:3" in val:
            return 4.0 / 3.0
        elif "16:9" in val:
            return 16.0 / 9.0
        elif "9:16" in val:
            return 9.0 / 16.0
        elif "3:2" in val:
            return 3.0 / 2.0
        return None

    def _on_aspect_change(self, choice: str):
        ratio = self._get_selected_ratio()
        self.on_start_crop(ratio)

    def _handle_start_crop(self):
        self.crop_action_frame.pack(fill="x", padx=8, pady=(0, 6))
        self.btn_toggle_crop.configure(text="✂ Adjust Crop Box")
        ratio = self._get_selected_ratio()
        self.on_start_crop(ratio)

    def hide_crop_actions(self):
        self.crop_action_frame.pack_forget()
        self.btn_toggle_crop.configure(text="✂ Start Crop Mode")

    def update_dimensions(self, width: int, height: int):
        self.current_width = width
        self.current_height = height
        self.entry_w.delete(0, "end")
        self.entry_w.insert(0, str(width))
        self.entry_h.delete(0, "end")
        self.entry_h.insert(0, str(height))

    def _on_toggle_maintain(self):
        self.maintain_aspect = bool(self.check_aspect.get())

    def _on_width_input(self, event):
        if not self.maintain_aspect or self.current_width <= 0:
            return
        try:
            val = int(self.entry_w.get())
            calc_h = int(round(val * (self.current_height / self.current_width)))
            self.entry_h.delete(0, "end")
            self.entry_h.insert(0, str(calc_h))
        except Exception:
            pass

    def _on_height_input(self, event):
        if not self.maintain_aspect or self.current_height <= 0:
            return
        try:
            val = int(self.entry_h.get())
            calc_w = int(round(val * (self.current_width / self.current_height)))
            self.entry_w.delete(0, "end")
            self.entry_w.insert(0, str(calc_w))
        except Exception:
            pass

    def _scale_by(self, factor: float):
        if self.current_width <= 0 or self.current_height <= 0:
            return
        w = max(1, int(round(self.current_width * factor)))
        h = max(1, int(round(self.current_height * factor)))
        self.entry_w.delete(0, "end")
        self.entry_w.insert(0, str(w))
        self.entry_h.delete(0, "end")
        self.entry_h.insert(0, str(h))

    def _handle_apply_resize(self):
        try:
            w = int(self.entry_w.get())
            h = int(self.entry_h.get())
            if w > 0 and h > 0:
                self.on_resize(w, h)
        except Exception:
            pass

