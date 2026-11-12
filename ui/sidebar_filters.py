"""
Sidebar Filters Panel for HEIC Studio Pro.
Curated color grading presets inspired by Apple iOS Photos & Samsung Gallery styles.
"""
from typing import Callable
import customtkinter as ctk


class SidebarFilters(ctk.CTkScrollableFrame):
    def __init__(self, master, on_select_preset: Callable[[str], None], **kwargs):
        super().__init__(master, **kwargs)
        self.on_select_preset = on_select_preset
        self.active_preset = "None"
        self.preset_buttons = {}

        self._build_ui()

    def _build_ui(self):
        header = ctk.CTkLabel(
            self,
            text="Flagship Color Presets",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        header.pack(anchor="w", padx=10, pady=(5, 12))

        presets = [
            ("None", "Original / Natural", "Standard unprocessed sensor capture", "#334155"),
            ("Apple Vivid", "Apple Vivid", "Punchy contrast & vibrant iPhone saturation", "#4f46e5"),
            ("Warm Golden", "Warm Golden Hour", "Sunset amber tones & rich warm shadows", "#d97706"),
            ("Cool Crisp", "Cool Crisp", "Clean cyan highlights & ultra-sharp clarity", "#0284c7"),
            ("Dramatic", "Dramatic Contrast", "Intense shadows & deep dynamic range", "#7c3aed"),
            ("Noir B&W", "Noir Monochrome", "Punchy deep black & white street style", "#1e293b"),
            ("Silvertone", "Silvertone B&W", "High-key classic studio silver monochrome", "#475569"),
            ("Vintage Film", "Vintage Film Fade", "Analog film warmth with softened contrast", "#b45309"),
        ]

        for key, title, desc, accent_color in presets:
            self._create_preset_card(key, title, desc, accent_color)

    def _create_preset_card(self, key: str, title: str, desc: str, accent_color: str):
        card = ctk.CTkFrame(
            self,
            fg_color="#1e293b",
            corner_radius=10,
            border_width=1,
            border_color="#334155"
        )
        card.pack(fill="x", padx=8, pady=5)

        # Card Title
        lbl_title = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f8fafc"
        )
        lbl_title.pack(anchor="w", padx=10, pady=(8, 2))

        # Card Description
        lbl_desc = ctk.CTkLabel(
            card,
            text=desc,
            font=ctk.CTkFont(size=10),
            text_color="#94a3b8",
            wraplength=180,
            justify="left"
        )
        lbl_desc.pack(anchor="w", padx=10, pady=(0, 8))

        # Apply Button
        btn = ctk.CTkButton(
            card,
            text="Apply Preset",
            command=lambda k=key: self._on_preset_click(k),
            fg_color=accent_color,
            hover_color="#4338ca",
            height=26,
            font=ctk.CTkFont(size=10, weight="bold")
        )
        btn.pack(fill="x", padx=10, pady=(0, 10))
        self.preset_buttons[key] = (btn, card)

    def _on_preset_click(self, key: str):
        self.active_preset = key
        for p_key, (btn, card) in self.preset_buttons.items():
            if p_key == key and key != "None":
                card.configure(border_color="#6366f1", border_width=2)
                btn.configure(text="✓ Active")
            else:
                card.configure(border_color="#334155", border_width=1)
                btn.configure(text="Apply Preset" if p_key != "None" else "Reset to Original")
        self.on_select_preset(key)

    def sync_preset(self, preset_name: str):
        self._on_preset_click(preset_name)

