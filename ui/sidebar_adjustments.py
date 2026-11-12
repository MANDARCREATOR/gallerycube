"""
Sidebar Adjustments Panel for HEIC Studio Pro.
Provides responsive sliders for Brightness, Contrast, Saturation, Sharpness, Warmth, and Tint.
"""
from typing import Callable, Dict
import customtkinter as ctk


class SidebarAdjustments(ctk.CTkScrollableFrame):
    def __init__(self, master, on_change: Callable[[str, float], None], on_reset: Callable[[], None], **kwargs):
        super().__init__(master, **kwargs)
        self.on_change = on_change
        self.on_reset = on_reset

        self.sliders: Dict[str, ctk.CTkSlider] = {}
        self.labels: Dict[str, ctk.CTkLabel] = {}

        self._build_ui()

    def _build_ui(self):
        # Section Header
        header = ctk.CTkLabel(
            self,
            text="Color & Lighting",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        header.pack(anchor="w", padx=10, pady=(5, 12))

        # Config for sliders: (key, title, min, max, default)
        slider_configs = [
            ("brightness", "Exposure / Brightness", -100.0, 100.0, 0.0),
            ("contrast", "Contrast", -100.0, 100.0, 0.0),
            ("saturation", "Saturation", -100.0, 100.0, 0.0),
            ("sharpness", "Sharpness", 0.0, 100.0, 0.0),
            ("warmth", "Warmth / Temp", -100.0, 100.0, 0.0),
            ("tint", "Tint (Green / Magenta)", -100.0, 100.0, 0.0),
        ]

        for key, title, min_val, max_val, default_val in slider_configs:
            self._create_slider_row(key, title, min_val, max_val, default_val)

        # Reset button
        reset_btn = ctk.CTkButton(
            self,
            text="Reset Adjustments",
            command=self._handle_reset,
            fg_color="#334155",
            hover_color="#475569",
            height=32,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        reset_btn.pack(fill="x", padx=10, pady=(20, 10))

    def _create_slider_row(self, key: str, title: str, min_v: float, max_v: float, default_v: float):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=8, pady=6)

        # Top line: Title & Value readout
        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.pack(fill="x")

        title_lbl = ctk.CTkLabel(
            header_frame,
            text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e2e8f0"
        )
        title_lbl.pack(side="left")

        val_lbl = ctk.CTkLabel(
            header_frame,
            text="0",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        val_lbl.pack(side="right")
        self.labels[key] = val_lbl

        # Slider
        slider = ctk.CTkSlider(
            frame,
            from_=min_v,
            to=max_v,
            number_of_steps=100,
            command=lambda val, k=key: self._on_slider_moved(k, val),
            button_color="#4f46e5",
            button_hover_color="#4338ca",
            progress_color="#6366f1",
            height=16
        )
        slider.set(default_v)
        slider.pack(fill="x", pady=(4, 2))
        self.sliders[key] = slider

    def _on_slider_moved(self, key: str, value: float):
        int_val = int(round(value))
        prefix = "+" if int_val > 0 else ""
        self.labels[key].configure(text=f"{prefix}{int_val}")
        self.on_change(key, float(int_val))

    def _handle_reset(self):
        for key, slider in self.sliders.items():
            slider.set(0.0)
            self.labels[key].configure(text="0")
        self.on_reset()

    def sync_values(self, adjustments: Dict[str, float]):
        """Synchronizes slider UI positions with the image engine state."""
        for key, slider in self.sliders.items():
            val = adjustments.get(key, 0.0)
            slider.set(val)
            int_val = int(round(val))
            prefix = "+" if int_val > 0 else ""
            self.labels[key].configure(text=f"{prefix}{int_val}")

