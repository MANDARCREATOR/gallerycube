"""
Universal Image Exporter & Batch Converter for Gallery Cube.
Supports HEIC/HEIF, JPEG, PNG, WebP, BMP, and TIFF with EXIF preservation,
quality configuration, and bulk folder conversion.
"""
import os
from typing import Optional, Tuple, Callable, List
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()


def export_image(
    image: Image.Image,
    output_path: str,
    format_name: Optional[str] = None,
    quality: int = 95,
    resize_dims: Optional[Tuple[int, int]] = None,
    raw_exif_bytes: Optional[bytes] = None,
    preserve_exif: bool = True
) -> Tuple[bool, str]:
    """
    Saves an image to disk with selectable format, quality, and optional EXIF preservation.
    Handles HEIC, JPEG, PNG, WebP, BMP, TIFF, and ICO.
    """
    try:
        export_img = image.copy()

        # Handle optional resizing
        if resize_dims and resize_dims != export_img.size:
            w, h = resize_dims
            export_img = export_img.resize((w, h), Image.Resampling.LANCZOS)

        # Detect format from extension if not explicitly provided
        ext = os.path.splitext(output_path)[1].lower()
        if not format_name:
            if ext in [".heic", ".heif", ".hif"]:
                format_name = "HEIF"
            elif ext in [".jpg", ".jpeg", ".jfif", ".jpe"]:
                format_name = "JPEG"
            elif ext == ".png":
                format_name = "PNG"
            elif ext == ".webp":
                format_name = "WEBP"
            elif ext in [".bmp", ".dib"]:
                format_name = "BMP"
            elif ext in [".tif", ".tiff"]:
                format_name = "TIFF"
            elif ext == ".ico":
                format_name = "ICO"
            else:
                format_name = "JPEG"

        save_kwargs = {}
        
        # Attach EXIF if requested, available, and supported by target format
        fmt_upper = format_name.upper()
        if preserve_exif and raw_exif_bytes and fmt_upper in ["HEIF", "JPEG", "TIFF", "WEBP", "PNG"]:
            save_kwargs["exif"] = raw_exif_bytes

        if fmt_upper == "HEIF":
            # Save using pillow-heif's libheif x265 encoder
            save_kwargs["quality"] = quality
            if export_img.mode == "RGBA":
                export_img = export_img.convert("RGB")
            export_img.save(output_path, format="HEIF", **save_kwargs)

        elif fmt_upper in ["JPEG", "JPG"]:
            if export_img.mode in ("RGBA", "P"):
                # Composite onto white background for JPEG
                bg = Image.new("RGB", export_img.size, (255, 255, 255))
                if export_img.mode == "RGBA":
                    bg.paste(export_img, mask=export_img.split()[3])
                else:
                    bg.paste(export_img)
                export_img = bg
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
            save_kwargs["subsampling"] = 0  # 4:4:4 Chroma subsampling
            export_img.save(output_path, format="JPEG", **save_kwargs)

        elif fmt_upper == "PNG":
            save_kwargs["optimize"] = True
            save_kwargs["compress_level"] = 6
            export_img.save(output_path, format="PNG", **save_kwargs)

        elif fmt_upper == "WEBP":
            save_kwargs["quality"] = quality
            save_kwargs["method"] = 6
            export_img.save(output_path, format="WEBP", **save_kwargs)

        elif fmt_upper == "BMP":
            if export_img.mode == "RGBA":
                export_img = export_img.convert("RGB")
            export_img.save(output_path, format="BMP")

        elif fmt_upper == "TIFF":
            save_kwargs["compression"] = "tiff_lzw"
            export_img.save(output_path, format="TIFF", **save_kwargs)

        elif fmt_upper == "ICO":
            # Standard Windows icon sizes
            export_img.save(output_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

        else:
            export_img.save(output_path, **save_kwargs)

        file_size_kb = os.path.getsize(output_path) / 1024.0
        return True, f"Saved successfully ({file_size_kb:.1f} KB)"
    except Exception as e:
        return False, f"Export error: {str(e)}"


def batch_convert_heic(
    file_list: List[str],
    output_directory: str,
    target_format: str = "JPEG",
    quality: int = 95,
    preserve_exif: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Tuple[int, int, List[str]]:
    """
    Converts a batch of any images (HEIC, PNG, JPG, WebP, etc.) to the target format.
    Returns: (successful_count, failed_count, errors)
    """
    os.makedirs(output_directory, exist_ok=True)
    success = 0
    failed = 0
    errors: List[str] = []

    ext_map = {
        "JPEG": ".jpg",
        "PNG": ".png",
        "WEBP": ".webp",
        "HEIF": ".heic",
        "BMP": ".bmp",
        "TIFF": ".tiff"
    }
    target_ext = ext_map.get(target_format.upper(), ".jpg")

    for i, file_path in enumerate(file_list):
        filename = os.path.basename(file_path)
        base_name = os.path.splitext(filename)[0]
        out_filename = base_name + target_ext
        dest_path = os.path.join(output_directory, out_filename)

        if progress_callback:
            progress_callback(i + 1, len(file_list), filename)

        try:
            with Image.open(file_path) as img:
                raw_exif = img.info.get("exif")
                oriented = ImageOps.exif_transpose(img)
                ok, msg = export_image(
                    image=oriented,
                    output_path=dest_path,
                    format_name=target_format,
                    quality=quality,
                    raw_exif_bytes=raw_exif,
                    preserve_exif=preserve_exif
                )
                if ok:
                    success += 1
                else:
                    failed += 1
                    errors.append(f"{filename}: {msg}")
        except Exception as e:
            failed += 1
            errors.append(f"{filename}: {str(e)}")

    return success, failed, errors
