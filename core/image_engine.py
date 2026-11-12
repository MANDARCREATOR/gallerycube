"""
Core Image Engine for Gallery Cube.
Universal image loading, decoding, proxy preview generation, non-destructive editing pipeline,
color grading, transformations (rotate, flip, crop), and undo/redo state management.
Supports HEIC/HEIF, JPEG, PNG (with transparency), WebP, BMP, TIFF, GIF, ICO, AVIF, and DNG.
"""
import copy
from typing import Optional, Tuple, Dict, Any, List
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import numpy as np
import pillow_heif

# Register HEIF opener once globally
pillow_heif.register_heif_opener()

SUPPORTED_EXTENSIONS = (
    ".heic", ".heif", ".hif",
    ".jpg", ".jpeg", ".jpe", ".jfif",
    ".png", ".apng",
    ".webp",
    ".bmp", ".dib",
    ".tif", ".tiff",
    ".gif",
    ".ico",
    ".avif",
    ".tga",
    ".dng",
    ".psd",
    ".ppm", ".pgm", ".pbm"
)


class ImageEngine:
    """
    Universal Image Engine for Gallery Cube.
    Manages active image state, high-res master, fast preview proxy, and non-destructive adjustments.
    """
    DEFAULT_ADJUSTMENTS: Dict[str, float] = {
        "brightness": 0.0,    # -100 to +100
        "contrast": 0.0,      # -100 to +100
        "saturation": 0.0,    # -100 to +100
        "sharpness": 0.0,     # 0 to 100
        "warmth": 0.0,        # -100 (Cool) to +100 (Warm)
        "tint": 0.0,          # -100 (Green) to +100 (Magenta)
        "filter": "None"      # Preset filter name
    }

    MAX_PROXY_DIMENSION = 2048  # Fast preview size for 48MP/200MP phone photos

    def __init__(self):
        self.file_path: Optional[str] = None
        self.raw_exif_bytes: Optional[bytes] = None
        self.original_format: str = "PNG"
        self.has_alpha: bool = False
        
        # Master original image (after EXIF transpose)
        self.master_image: Optional[Image.Image] = None
        
        # Transformed master image (after crops, rotates, flips)
        self.transformed_master: Optional[Image.Image] = None
        
        # Proxy image for ultra-smooth UI previews
        self.proxy_image: Optional[Image.Image] = None
        
        # Current active adjustments
        self.adjustments: Dict[str, Any] = copy.deepcopy(self.DEFAULT_ADJUSTMENTS)
        
        # Undo / Redo history stacks
        self.undo_stack: List[Dict[str, Any]] = []
        self.redo_stack: List[Dict[str, Any]] = []

    def load_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Loads and auto-transposes ANY supported image (HEIC, JPG, PNG, WEBP, BMP, TIFF, etc.).
        """
        try:
            pil_img = Image.open(file_path)
            self.original_format = pil_img.format or "JPEG"
            
            # Preserve raw EXIF bytes for export
            self.raw_exif_bytes = pil_img.info.get("exif")
            
            # Auto-transpose EXIF orientation (crucial for iPhone/Samsung portrait and angle shots)
            oriented_img = ImageOps.exif_transpose(pil_img)
            
            # Detect alpha channel
            if oriented_img.mode in ("RGBA", "LA") or (oriented_img.mode == "P" and "transparency" in oriented_img.info):
                self.has_alpha = True
                oriented_img = oriented_img.convert("RGBA")
            elif oriented_img.mode != "RGB":
                self.has_alpha = False
                oriented_img = oriented_img.convert("RGB")
            else:
                self.has_alpha = False
            
            self.file_path = file_path
            self.master_image = oriented_img
            self.transformed_master = oriented_img.copy()
            self.adjustments = copy.deepcopy(self.DEFAULT_ADJUSTMENTS)
            
            self.undo_stack.clear()
            self.redo_stack.clear()
            self._save_state("Initial Load")
            
            self._rebuild_proxy()
            alpha_str = " (Alpha Transparency)" if self.has_alpha else ""
            return True, f"Loaded {oriented_img.width} × {oriented_img.height}{alpha_str}"
        except Exception as e:
            return False, f"Failed to open image: {str(e)}"

    def _rebuild_proxy(self):
        """Generates a responsive proxy preview from the transformed master."""
        if self.transformed_master is None:
            self.proxy_image = None
            return

        w, h = self.transformed_master.size
        max_dim = max(w, h)
        if max_dim > self.MAX_PROXY_DIMENSION:
            scale = self.MAX_PROXY_DIMENSION / max_dim
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            self.proxy_image = self.transformed_master.resize(new_size, Image.Resampling.BILINEAR)
        else:
            self.proxy_image = self.transformed_master.copy()

    def _save_state(self, action_name: str):
        """Saves current transformation & adjustment state into undo stack."""
        if self.transformed_master is None:
            return

        state = {
            "action": action_name,
            "transformed_image": self.transformed_master.copy(),
            "adjustments": copy.deepcopy(self.adjustments)
        }
        self.undo_stack.append(state)
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)

    def undo(self) -> bool:
        """Undo last transformation or adjustment."""
        if len(self.undo_stack) <= 1:
            return False

        current_state = self.undo_stack.pop()
        self.redo_stack.append(current_state)

        prev_state = self.undo_stack[-1]
        self.transformed_master = prev_state["transformed_image"].copy()
        self.adjustments = copy.deepcopy(prev_state["adjustments"])
        self._rebuild_proxy()
        return True

    def redo(self) -> bool:
        """Redo previously undone action."""
        if not self.redo_stack:
            return False

        next_state = self.redo_stack.pop()
        self.undo_stack.append(next_state)
        self.transformed_master = next_state["transformed_image"].copy()
        self.adjustments = copy.deepcopy(next_state["adjustments"])
        self._rebuild_proxy()
        return True

    # ================= Transform Operations =================

    def rotate(self, degrees: int):
        """Rotate image clockwise (e.g. 90, 180, 270)."""
        if self.transformed_master is None:
            return

        self.transformed_master = self.transformed_master.rotate(-degrees, expand=True)
        self._rebuild_proxy()
        self.redo_stack.clear()
        self._save_state(f"Rotate {degrees}°")

    def flip(self, horizontal: bool = True):
        """Flip image horizontally or vertically."""
        if self.transformed_master is None:
            return

        method = Image.Transpose.FLIP_LEFT_RIGHT if horizontal else Image.Transpose.FLIP_TOP_BOTTOM
        self.transformed_master = self.transformed_master.transpose(method)
        self._rebuild_proxy()
        self.redo_stack.clear()
        self._save_state("Flip Horizontal" if horizontal else "Flip Vertical")

    def crop(self, crop_box: Tuple[int, int, int, int]):
        """Crop image to bounding box (left, top, right, bottom)."""
        if self.transformed_master is None:
            return

        w, h = self.transformed_master.size
        x1 = max(0, min(crop_box[0], w - 1))
        y1 = max(0, min(crop_box[1], h - 1))
        x2 = max(x1 + 1, min(crop_box[2], w))
        y2 = max(y1 + 1, min(crop_box[3], h))

        self.transformed_master = self.transformed_master.crop((x1, y1, x2, y2))
        self._rebuild_proxy()
        self.redo_stack.clear()
        self._save_state("Crop")

    def reset_transforms(self):
        """Resets image back to initial imported master."""
        if self.master_image is None:
            return
        self.transformed_master = self.master_image.copy()
        self.adjustments = copy.deepcopy(self.DEFAULT_ADJUSTMENTS)
        self._rebuild_proxy()
        self.redo_stack.clear()
        self._save_state("Reset to Original")

    # ================= Adjustments & Color Grading =================

    def update_adjustment(self, key: str, value: Any):
        """Updates a single adjustment parameter."""
        if key in self.adjustments:
            self.adjustments[key] = value

    def reset_adjustments(self):
        """Resets all color sliders back to 0."""
        self.adjustments = copy.deepcopy(self.DEFAULT_ADJUSTMENTS)

    def apply_filter_preset(self, preset_name: str):
        """Applies curated flagship photo color grading presets."""
        self.adjustments["filter"] = preset_name
        
        if preset_name == "Apple Vivid":
            self.adjustments["contrast"] = 18.0
            self.adjustments["saturation"] = 28.0
            self.adjustments["sharpness"] = 15.0
            self.adjustments["brightness"] = 4.0
            self.adjustments["warmth"] = 6.0
            self.adjustments["tint"] = 0.0

        elif preset_name == "Warm Golden":
            self.adjustments["contrast"] = 10.0
            self.adjustments["saturation"] = 15.0
            self.adjustments["warmth"] = 35.0
            self.adjustments["brightness"] = 6.0
            self.adjustments["tint"] = -4.0

        elif preset_name == "Cool Crisp":
            self.adjustments["contrast"] = 14.0
            self.adjustments["saturation"] = 8.0
            self.adjustments["warmth"] = -32.0
            self.adjustments["sharpness"] = 25.0
            self.adjustments["brightness"] = 2.0
            self.adjustments["tint"] = 2.0

        elif preset_name == "Dramatic":
            self.adjustments["contrast"] = 45.0
            self.adjustments["saturation"] = -10.0
            self.adjustments["sharpness"] = 25.0
            self.adjustments["brightness"] = -5.0
            self.adjustments["warmth"] = 0.0

        elif preset_name == "Noir B&W":
            self.adjustments["contrast"] = 40.0
            self.adjustments["saturation"] = -100.0
            self.adjustments["sharpness"] = 20.0
            self.adjustments["brightness"] = -4.0

        elif preset_name == "Silvertone":
            self.adjustments["contrast"] = 15.0
            self.adjustments["saturation"] = -100.0
            self.adjustments["sharpness"] = 10.0
            self.adjustments["brightness"] = 12.0

        elif preset_name == "Vintage Film":
            self.adjustments["contrast"] = -8.0
            self.adjustments["saturation"] = -15.0
            self.adjustments["warmth"] = 20.0
            self.adjustments["brightness"] = 8.0
            self.adjustments["tint"] = 10.0

        elif preset_name == "None":
            self.reset_adjustments()

    def process_pipeline(self, base_img: Image.Image) -> Image.Image:
        """
        Executes color adjustments while safely handling alpha transparency.
        """
        # Separate alpha channel if present
        alpha_channel = None
        if base_img.mode == "RGBA":
            r, g, b, alpha_channel = base_img.split()
            rgb_img = Image.merge("RGB", (r, g, b))
        else:
            rgb_img = base_img.copy()

        # 1. Warmth & Tint
        warmth = self.adjustments.get("warmth", 0.0)
        tint = self.adjustments.get("tint", 0.0)
        if warmth != 0.0 or tint != 0.0:
            arr = np.array(rgb_img, dtype=np.float32)
            if warmth != 0.0:
                shift_w = (warmth / 100.0) * 35.0
                arr[:, :, 0] += shift_w
                arr[:, :, 2] -= shift_w

            if tint != 0.0:
                shift_t = (tint / 100.0) * 30.0
                arr[:, :, 1] -= shift_t
                arr[:, :, 0] += shift_t * 0.5
                arr[:, :, 2] += shift_t * 0.5

            np.clip(arr, 0, 255, out=arr)
            rgb_img = Image.fromarray(arr.astype(np.uint8))

        # 2. Brightness
        b_val = self.adjustments.get("brightness", 0.0)
        if b_val != 0.0:
            factor = max(0.1, 1.0 + (b_val / 100.0) * 0.8)
            rgb_img = ImageEnhance.Brightness(rgb_img).enhance(factor)

        # 3. Contrast
        c_val = self.adjustments.get("contrast", 0.0)
        if c_val != 0.0:
            factor = max(0.1, 1.0 + (c_val / 100.0) * 1.0)
            rgb_img = ImageEnhance.Contrast(rgb_img).enhance(factor)

        # 4. Saturation
        s_val = self.adjustments.get("saturation", 0.0)
        if s_val != 0.0:
            factor = max(0.0, 1.0 + (s_val / 100.0) * 1.2)
            rgb_img = ImageEnhance.Color(rgb_img).enhance(factor)

        # 5. Sharpness
        sh_val = self.adjustments.get("sharpness", 0.0)
        if sh_val > 0.0:
            factor = 1.0 + (sh_val / 100.0) * 2.0
            rgb_img = ImageEnhance.Sharpness(rgb_img).enhance(factor)

        # Recombine alpha channel if existed
        if alpha_channel is not None:
            r, g, b = rgb_img.split()
            return Image.merge("RGBA", (r, g, b, alpha_channel))

        return rgb_img

    def get_preview_image(self) -> Optional[Image.Image]:
        """Returns rendered preview image."""
        if self.proxy_image is None:
            return None
        return self.process_pipeline(self.proxy_image)

    def get_full_rendered_image(self) -> Optional[Image.Image]:
        """Returns full master resolution image with all edits applied."""
        if self.transformed_master is None:
            return None
        return self.process_pipeline(self.transformed_master)

    @property
    def has_image(self) -> bool:
        return self.transformed_master is not None

    @property
    def dimensions(self) -> Tuple[int, int]:
        if self.transformed_master is None:
            return (0, 0)
        return self.transformed_master.size
