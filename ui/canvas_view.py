"""
High-Performance Interactive Canvas for HEIC Studio Pro.
Supports smooth zoom (centered on cursor), panning, fit-to-view, 100% actual size,
and interactive crop rectangle overlay with aspect ratio constraints.
"""
import tkinter as tk
from typing import Optional, Tuple, Callable
from PIL import Image, ImageTk
import customtkinter as ctk


class CanvasView(ctk.CTkFrame):
    """
    Viewport container with a responsive Tkinter Canvas for image display,
    zooming, panning, and crop rectangle manipulation.
    """
    def __init__(self, master, on_crop_applied: Optional[Callable[[Tuple[int, int, int, int]], None]] = None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_crop_applied = on_crop_applied

        # Raw PIL preview image currently being rendered
        self.pil_image: Optional[Image.Image] = None
        self.tk_image: Optional[ImageTk.PhotoImage] = None

        # Viewport zoom & pan transform state
        self.zoom_level: float = 1.0     # 1.0 = 100%
        self.fit_zoom: float = 1.0
        self.pan_x: float = 0.0          # Image top-left offset in canvas
        self.pan_y: float = 0.0
        self.is_panning: bool = False
        self.last_mouse_x: int = 0
        self.last_mouse_y: int = 0

        # Crop Mode State
        self.crop_active: bool = False
        self.aspect_ratio: Optional[float] = None  # None = Free, or width / height (e.g. 1.0, 16/9)
        self.crop_rect = [0.0, 0.0, 0.0, 0.0]     # [x1, y1, x2, y2] in image coordinate space (0 to 1 normalized)
        self.drag_mode: Optional[str] = None      # 'move', 'nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'

        # Canvas widget setup
        self.canvas = tk.Canvas(
            self,
            bg="#0b1120",
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Event bindings
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)  # Windows mouse wheel
        self.canvas.bind("<ButtonPress-1>", self._on_button_press)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_button_release)
        self.canvas.bind("<ButtonPress-2>", self._on_middle_press)  # Middle click pan
        self.canvas.bind("<B2-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-2>", self._on_button_release)
        self.canvas.bind("<Motion>", self._on_mouse_hover)

    def set_image(self, image: Optional[Image.Image], reset_zoom: bool = False):
        """Sets the preview image and refreshes the canvas."""
        self.pil_image = image
        if reset_zoom and self.pil_image:
            self.fit_to_screen()
        else:
            self.redraw()

    def fit_to_screen(self):
        """Fits image to canvas maintaining aspect ratio."""
        if not self.pil_image:
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            return

        img_w, img_h = self.pil_image.size
        scale_w = (canvas_w - 40) / img_w
        scale_h = (canvas_h - 40) / img_h
        self.zoom_level = max(0.01, min(scale_w, scale_h))
        self.fit_zoom = self.zoom_level

        # Center image in viewport
        display_w = img_w * self.zoom_level
        display_h = img_h * self.zoom_level
        self.pan_x = (canvas_w - display_w) / 2.0
        self.pan_y = (canvas_h - display_h) / 2.0
        self.redraw()

    def actual_size(self):
        """Zooms to 100% 1:1 pixel mapping."""
        if not self.pil_image:
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        img_w, img_h = self.pil_image.size

        self.zoom_level = 1.0
        self.pan_x = (canvas_w - img_w) / 2.0
        self.pan_y = (canvas_h - img_h) / 2.0
        self.redraw()

    def zoom_by(self, factor: float):
        """Zooms in or out centered on canvas."""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        self._apply_zoom(factor, canvas_w / 2.0, canvas_h / 2.0)

    def _apply_zoom(self, factor: float, center_x: float, center_y: float):
        """Zooms in/out keeping the pixel under center_x, center_y stationary."""
        if not self.pil_image:
            return

        new_zoom = max(0.05, min(10.0, self.zoom_level * factor))
        if abs(new_zoom - self.zoom_level) < 1e-5:
            return

        # Calculate coordinate under cursor in image space
        img_x = (center_x - self.pan_x) / self.zoom_level
        img_y = (center_y - self.pan_y) / self.zoom_level

        self.zoom_level = new_zoom

        # Recompute pan so img_x, img_y stays at center_x, center_y
        self.pan_x = center_x - img_x * self.zoom_level
        self.pan_y = center_y - img_y * self.zoom_level
        self.redraw()

    def redraw(self):
        """Redraws image and crop overlay."""
        self.canvas.delete("all")
        if not self.pil_image:
            self.canvas.create_text(
                self.canvas.winfo_width() / 2,
                self.canvas.winfo_height() / 2,
                text="No Image Loaded\nClick 'Open File' (Ctrl+O) to open a HEIC photo",
                fill="#64748b",
                font=("Segoe UI", 14),
                justify=tk.CENTER
            )
            return

        # Resize PIL image for display
        img_w, img_h = self.pil_image.size
        disp_w = max(1, int(img_w * self.zoom_level))
        disp_h = max(1, int(img_h * self.zoom_level))

        # Use NEAREST when deeply zoomed in (>1.5) for crisp pixel rendering, BILINEAR when zoomed out
        resample_method = Image.Resampling.NEAREST if self.zoom_level > 1.5 else Image.Resampling.BILINEAR
        resized = self.pil_image.resize((disp_w, disp_h), resample_method)
        self.tk_image = ImageTk.PhotoImage(resized)

        self.canvas.create_image(
            int(self.pan_x),
            int(self.pan_y),
            anchor=tk.NW,
            image=self.tk_image
        )

        if self.crop_active:
            self._draw_crop_overlay(disp_w, disp_h)

    # ================= Crop Overlay Logic =================

    def start_crop(self, aspect_ratio: Optional[float] = None):
        """Enables crop mode with optional aspect ratio lock."""
        self.crop_active = True
        self.aspect_ratio = aspect_ratio
        
        # Initialize crop rectangle to 80% of image center
        if aspect_ratio is None:
            self.crop_rect = [0.1, 0.1, 0.9, 0.9]
        else:
            # Constrain to aspect ratio
            img_w, img_h = self.pil_image.size if self.pil_image else (1, 1)
            target_w = 0.8
            target_h = target_w * (img_w / img_h) / aspect_ratio
            if target_h > 0.8:
                target_h = 0.8
                target_w = target_h * (img_h / img_w) * aspect_ratio
            x1 = 0.5 - target_w / 2.0
            y1 = 0.5 - target_h / 2.0
            self.crop_rect = [x1, y1, x1 + target_w, y1 + target_h]

        self.redraw()

    def cancel_crop(self):
        """Cancels crop mode."""
        self.crop_active = False
        self.redraw()

    def get_crop_pixel_box(self, master_dims: Tuple[int, int]) -> Tuple[int, int, int, int]:
        """Maps normalized crop rectangle to master image pixel box (x1, y1, x2, y2)."""
        w, h = master_dims
        x1 = int(round(self.crop_rect[0] * w))
        y1 = int(round(self.crop_rect[1] * h))
        x2 = int(round(self.crop_rect[2] * w))
        y2 = int(round(self.crop_rect[3] * h))
        return (x1, y1, x2, y2)

    def _draw_crop_overlay(self, disp_w: int, disp_h: int):
        """Renders shaded dark regions outside crop box and glowing border with handles."""
        cx1 = self.pan_x + self.crop_rect[0] * disp_w
        cy1 = self.pan_y + self.crop_rect[1] * disp_h
        cx2 = self.pan_x + self.crop_rect[2] * disp_w
        cy2 = self.pan_y + self.crop_rect[3] * disp_h

        # Dimmed mask outside crop box
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        mask_color = "#000000"

        # 4 Rectangles around the crop box
        self.canvas.create_rectangle(0, 0, canvas_w, cy1, fill=mask_color, stipple="gray50", width=0)
        self.canvas.create_rectangle(0, cy2, canvas_w, canvas_h, fill=mask_color, stipple="gray50", width=0)
        self.canvas.create_rectangle(0, cy1, cx1, cy2, fill=mask_color, stipple="gray50", width=0)
        self.canvas.create_rectangle(cx2, cy1, canvas_w, cy2, fill=mask_color, stipple="gray50", width=0)

        # Rule of thirds grid lines
        grid_w = (cx2 - cx1) / 3.0
        grid_h = (cy2 - cy1) / 3.0
        for i in (1, 2):
            self.canvas.create_line(cx1 + i * grid_w, cy1, cx1 + i * grid_w, cy2, fill="#ffffff", dash=(2, 4), width=1)
            self.canvas.create_line(cx1, cy1 + i * grid_h, cx2, cy1 + i * grid_h, fill="#ffffff", dash=(2, 4), width=1)

        # Border rectangle
        self.canvas.create_rectangle(cx1, cy1, cx2, cy2, outline="#4f46e5", width=2)

        # Corner handles
        handle_size = 8
        corners = [
            (cx1, cy1), (cx2, cy1), (cx1, cy2), (cx2, cy2)
        ]
        for hx, hy in corners:
            self.canvas.create_rectangle(
                hx - handle_size, hy - handle_size,
                hx + handle_size, hy + handle_size,
                fill="#ffffff", outline="#4f46e5", width=2
            )

    # ================= Mouse Events =================

    def _on_resize(self, event):
        """Called on window/canvas resize."""
        if self.pil_image and self.fit_zoom == self.zoom_level:
            self.fit_to_screen()
        else:
            self.redraw()

    def _on_mousewheel(self, event):
        """Mouse wheel zooming."""
        factor = 1.15 if event.delta > 0 else 0.85
        self._apply_zoom(factor, event.x, event.y)

    def _on_middle_press(self, event):
        """Middle click always initiates panning."""
        self.is_panning = True
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

    def _on_button_press(self, event):
        """Left click handles crop handle drag or panning."""
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

        if self.crop_active and self.pil_image:
            img_w, img_h = self.pil_image.size
            disp_w = img_w * self.zoom_level
            disp_h = img_h * self.zoom_level
            cx1 = self.pan_x + self.crop_rect[0] * disp_w
            cy1 = self.pan_y + self.crop_rect[1] * disp_h
            cx2 = self.pan_x + self.crop_rect[2] * disp_w
            cy2 = self.pan_y + self.crop_rect[3] * disp_h

            margin = 12
            # Check corners
            if abs(event.x - cx1) < margin and abs(event.y - cy1) < margin:
                self.drag_mode = "nw"
            elif abs(event.x - cx2) < margin and abs(event.y - cy1) < margin:
                self.drag_mode = "ne"
            elif abs(event.x - cx1) < margin and abs(event.y - cy2) < margin:
                self.drag_mode = "sw"
            elif abs(event.x - cx2) < margin and abs(event.y - cy2) < margin:
                self.drag_mode = "se"
            elif cx1 < event.x < cx2 and cy1 < event.y < cy2:
                self.drag_mode = "move"
            else:
                self.drag_mode = None
                self.is_panning = True
        else:
            self.is_panning = True

    def _on_mouse_drag(self, event):
        """Handles panning or crop resizing."""
        dx = event.x - self.last_mouse_x
        dy = event.y - self.last_mouse_y
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

        if self.is_panning:
            self.pan_x += dx
            self.pan_y += dy
            self.redraw()
            return

        if self.crop_active and self.drag_mode and self.pil_image:
            img_w, img_h = self.pil_image.size
            disp_w = img_w * self.zoom_level
            disp_h = img_h * self.zoom_level
            if disp_w <= 0 or disp_h <= 0:
                return

            norm_dx = dx / disp_w
            norm_dy = dy / disp_h

            x1, y1, x2, y2 = self.crop_rect

            if self.drag_mode == "move":
                # Move crop rectangle
                box_w = x2 - x1
                box_h = y2 - y1
                new_x1 = max(0.0, min(1.0 - box_w, x1 + norm_dx))
                new_y1 = max(0.0, min(1.0 - box_h, y1 + norm_dy))
                self.crop_rect = [new_x1, new_y1, new_x1 + box_w, new_y1 + box_h]

            elif self.drag_mode == "se":
                x2 = min(1.0, max(x1 + 0.05, x2 + norm_dx))
                if self.aspect_ratio:
                    y2 = min(1.0, y1 + (x2 - x1) * (img_w / img_h) / self.aspect_ratio)
                else:
                    y2 = min(1.0, max(y1 + 0.05, y2 + norm_dy))
                self.crop_rect = [x1, y1, x2, y2]

            elif self.drag_mode == "nw":
                x1 = max(0.0, min(x2 - 0.05, x1 + norm_dx))
                if self.aspect_ratio:
                    y1 = max(0.0, y2 - (x2 - x1) * (img_w / img_h) / self.aspect_ratio)
                else:
                    y1 = max(0.0, min(y2 - 0.05, y1 + norm_dy))
                self.crop_rect = [x1, y1, x2, y2]

            elif self.drag_mode == "ne":
                x2 = min(1.0, max(x1 + 0.05, x2 + norm_dx))
                if self.aspect_ratio:
                    y1 = max(0.0, y2 - (x2 - x1) * (img_w / img_h) / self.aspect_ratio)
                else:
                    y1 = max(0.0, min(y2 - 0.05, y1 + norm_dy))
                self.crop_rect = [x1, y1, x2, y2]

            elif self.drag_mode == "sw":
                x1 = max(0.0, min(x2 - 0.05, x1 + norm_dx))
                if self.aspect_ratio:
                    y2 = min(1.0, y1 + (x2 - x1) * (img_w / img_h) / self.aspect_ratio)
                else:
                    y2 = min(1.0, max(y1 + 0.05, y2 + norm_dy))
                self.crop_rect = [x1, y1, x2, y2]

            self.redraw()

    def _on_button_release(self, event):
        self.is_panning = False
        self.drag_mode = None

    def _on_mouse_hover(self, event):
        """Updates cursor depending on hover over crop handles or canvas."""
        if not self.crop_active or not self.pil_image:
            self.canvas.config(cursor="crosshair" if not self.is_panning else "fleur")
            return

        img_w, img_h = self.pil_image.size
        disp_w = img_w * self.zoom_level
        disp_h = img_h * self.zoom_level
        cx1 = self.pan_x + self.crop_rect[0] * disp_w
        cy1 = self.pan_y + self.crop_rect[1] * disp_h
        cx2 = self.pan_x + self.crop_rect[2] * disp_w
        cy2 = self.pan_y + self.crop_rect[3] * disp_h

        margin = 12
        if (abs(event.x - cx1) < margin and abs(event.y - cy1) < margin) or (abs(event.x - cx2) < margin and abs(event.y - cy2) < margin):
            self.canvas.config(cursor="size_nw_se")
        elif (abs(event.x - cx2) < margin and abs(event.y - cy1) < margin) or (abs(event.x - cx1) < margin and abs(event.y - cy2) < margin):
            self.canvas.config(cursor="size_ne_sw")
        elif cx1 < event.x < cx2 and cy1 < event.y < cy2:
            self.canvas.config(cursor="fleur")
        else:
            self.canvas.config(cursor="default")

