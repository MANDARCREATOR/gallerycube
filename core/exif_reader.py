"""
EXIF Metadata Reader for Flagship Apple and Samsung HEIC/HEIF images.
Extracts camera details, shot parameters, lens specs, color spaces, and GPS coordinates.
"""
from typing import Dict, Any, Optional
from PIL import Image, ExifTags


def _convert_dms_to_decimal(dms, ref) -> Optional[float]:
    """Convert degrees, minutes, seconds tuple to decimal coordinate."""
    try:
        degrees = float(dms[0])
        minutes = float(dms[1])
        seconds = float(dms[2])
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ['S', 'W']:
            decimal = -decimal
        return round(decimal, 6)
    except Exception:
        return None


def parse_exif_metadata(image: Image.Image) -> Dict[str, Any]:
    """
    Extracts human-readable metadata from a PIL Image.
    Works with both Apple iPhone (iOS) and Samsung Galaxy (OneUI) HEIC photos.
    """
    metadata: Dict[str, Any] = {
        "Make": "Unknown",
        "Model": "Unknown Camera / Device",
        "Lens": "Unknown Lens",
        "DateTime": "Unknown Date",
        "Resolution": f"{image.width} × {image.height} ({round((image.width * image.height) / 1_000_000, 1)} MP)",
        "ColorMode": image.mode,
        "Aperture": None,
        "ExposureTime": None,
        "ISO": None,
        "FocalLength": None,
        "FocalLength35mm": None,
        "Software": None,
        "Flash": None,
        "WhiteBalance": None,
        "ExposureProgram": None,
        "GPS": None,
        "AllTags": {}
    }

    try:
        exif = image.getexif()
        if not exif:
            return metadata

        # Map standard tags
        for tag_id, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
            metadata["AllTags"][tag_name] = value

            if tag_name == "Make":
                metadata["Make"] = str(value).strip()
            elif tag_name == "Model":
                metadata["Model"] = str(value).strip()
            elif tag_name == "Software":
                metadata["Software"] = str(value).strip()
            elif tag_name == "DateTime":
                metadata["DateTime"] = str(value).strip()

        # Check Exif sub-IFD (where shooting params like ISO, F-number live)
        if hasattr(exif, "get_ifd"):
            try:
                exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
                for tag_id, value in exif_ifd.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    metadata["AllTags"][tag_name] = value

                    if tag_name == "FNumber":
                        try:
                            f_val = float(value)
                            metadata["Aperture"] = f"f/{f_val:.1f}" if f_val % 1 else f"f/{int(f_val)}"
                        except Exception:
                            metadata["Aperture"] = str(value)

                    elif tag_name == "ExposureTime":
                        try:
                            exp_val = float(value)
                            if exp_val > 0:
                                if exp_val < 1:
                                    metadata["ExposureTime"] = f"1/{int(round(1.0 / exp_val))}s"
                                else:
                                    metadata["ExposureTime"] = f"{exp_val:.1f}s"
                        except Exception:
                            metadata["ExposureTime"] = str(value)

                    elif tag_name == "ISOSpeedRatings" or tag_name == "PhotographicSensitivity":
                        metadata["ISO"] = f"ISO {value}"

                    elif tag_name == "FocalLength":
                        try:
                            focal = float(value)
                            metadata["FocalLength"] = f"{focal:.1f} mm"
                        except Exception:
                            metadata["FocalLength"] = str(value)

                    elif tag_name == "FocalLengthIn35mmFilm":
                        metadata["FocalLength35mm"] = f"{value} mm (35mm eq.)"

                    elif tag_name == "LensModel":
                        metadata["Lens"] = str(value).strip()

                    elif tag_name == "Flash":
                        # Bit 0 indicates flash fired
                        metadata["Flash"] = "Fired" if (int(value) & 1) else "Did not fire"

                    elif tag_name == "WhiteBalance":
                        metadata["WhiteBalance"] = "Manual" if int(value) == 1 else "Auto"
            except Exception:
                pass

            # Check GPS sub-IFD
            try:
                gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
                if gps_ifd:
                    lat_dms = gps_ifd.get(ExifTags.GPS.GPSLatitude)
                    lat_ref = gps_ifd.get(ExifTags.GPS.GPSLatitudeRef)
                    lon_dms = gps_ifd.get(ExifTags.GPS.GPSLongitude)
                    lon_ref = gps_ifd.get(ExifTags.GPS.GPSLongitudeRef)

                    if lat_dms and lat_ref and lon_dms and lon_ref:
                        lat = _convert_dms_to_decimal(lat_dms, lat_ref)
                        lon = _convert_dms_to_decimal(lon_dms, lon_ref)
                        if lat is not None and lon is not None:
                            metadata["GPS"] = {
                                "Latitude": lat,
                                "Longitude": lon,
                                "Formatted": f"{abs(lat):.4f}° {'N' if lat >= 0 else 'S'}, {abs(lon):.4f}° {'E' if lon >= 0 else 'W'}",
                                "MapsUrl": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                            }
            except Exception:
                pass

    except Exception as e:
        metadata["Error"] = str(e)

    # Format Device string cleanly
    if metadata["Make"] != "Unknown" and metadata["Model"] != "Unknown Camera / Device":
        make = metadata["Make"]
        model = metadata["Model"]
        if not model.lower().startswith(make.lower()):
            metadata["DeviceTitle"] = f"{make} {model}"
        else:
            metadata["DeviceTitle"] = model
    else:
        metadata["DeviceTitle"] = metadata["Model"]

    return metadata

