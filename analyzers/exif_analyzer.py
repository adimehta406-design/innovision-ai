"""
EXIF Metadata Analyzer
Extracts and analyzes EXIF metadata from images to detect signs of manipulation.
"""

import io
import logging
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

logger = logging.getLogger(__name__)

# Software names commonly associated with image editing
EDITING_SOFTWARE = [
    "photoshop", "gimp", "lightroom", "affinity", "paint.net",
    "pixlr", "canva", "snapseed", "faceapp", "facetune",
    "adobe", "corel", "paintshop", "photoscape", "fotor",
    "picsart", "befunky", "polarr", "vsco", "darktable",
    "rawtherapee", "capture one", "luminar", "on1", "dxo"
]

# Suspicious indicators
SUSPICIOUS_FIELDS = {
    "Software": "Image was processed/edited with software",
    "ProcessingSoftware": "Image was processed with software",
    "ImageDescription": "Image has a custom description (may indicate editing)",
}


def extract_exif(image_bytes: bytes) -> dict:
    """Extract and analyze EXIF metadata from image bytes."""
    result = {
        "has_exif": False,
        "metadata": {},
        "flags": [],
        "risk_score": 0,
        "summary": "",
        "details": {}
    }

    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        logger.error(f"Failed to open image for EXIF: {e}")
        result["flags"].append("Could not open image for EXIF analysis")
        result["risk_score"] = 30
        result["summary"] = "Image could not be opened for EXIF analysis."
        return result

    # Get basic image info
    result["details"]["format"] = img.format or "Unknown"
    result["details"]["mode"] = img.mode
    result["details"]["size"] = f"{img.size[0]}x{img.size[1]}"

    # Extract EXIF data
    exif_data = {}
    try:
        raw_exif = img._getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                # Convert bytes to string for JSON serialization
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8", errors="replace")
                    except Exception:
                        value = str(value)
                elif isinstance(value, tuple):
                    value = str(value)
                exif_data[tag_name] = str(value)
            result["has_exif"] = True
    except Exception as e:
        logger.debug(f"No standard EXIF data: {e}")

    # Also try Pillow's getexif()
    try:
        pil_exif = img.getexif()
        if pil_exif:
            for tag_id, value in pil_exif.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                if tag_name not in exif_data:
                    if isinstance(value, bytes):
                        try:
                            value = value.decode("utf-8", errors="replace")
                        except Exception:
                            value = str(value)
                    exif_data[tag_name] = str(value)
            if exif_data:
                result["has_exif"] = True
    except Exception:
        pass

    result["metadata"] = exif_data

    # --- Analysis ---
    risk = 0
    flags = []

    # 1. No EXIF at all — suspicious for photos (could be stripped)
    if not result["has_exif"]:
        flags.append("⚠️ No EXIF metadata found — metadata may have been stripped")
        risk += 35

    # 2. Check for editing software
    for field in ["Software", "ProcessingSoftware"]:
        if field in exif_data:
            software_val = exif_data[field].lower()
            for editor in EDITING_SOFTWARE:
                if editor in software_val:
                    flags.append(f"🔴 Editing software detected: {exif_data[field]}")
                    risk += 40
                    break
            else:
                flags.append(f"ℹ️ Software tag: {exif_data[field]}")
                risk += 10

    # 3. Check for date inconsistencies
    date_fields = {}
    for field in ["DateTime", "DateTimeOriginal", "DateTimeDigitized"]:
        if field in exif_data:
            date_fields[field] = exif_data[field]

    if len(date_fields) >= 2:
        dates = list(date_fields.values())
        if len(set(dates)) > 1:
            flags.append("🟡 Date/time inconsistency detected across EXIF fields")
            risk += 20

    # 4. Check for GPS data (not necessarily suspicious, but notable)
    if any(k.startswith("GPS") for k in exif_data):
        flags.append("📍 GPS location data present in image")

    # 5. Check for thumbnail mismatch indicator
    if "Orientation" in exif_data:
        try:
            orientation = int(exif_data["Orientation"])
            if orientation > 4:
                flags.append("ℹ️ Non-standard orientation (image may have been rotated)")
        except (ValueError, TypeError):
            pass

    # 6. Very high resolution might indicate screenshot composition
    if img.size[0] * img.size[1] > 20_000_000:
        flags.append("ℹ️ Very high resolution image (20+ MP)")
        risk += 5

    # 7. PNG with no EXIF is common for screenshots — lower suspicion
    if img.format == "PNG" and not result["has_exif"]:
        risk = max(risk - 15, 5)
        flags.append("ℹ️ PNG format without EXIF is common for screenshots/graphics")

    # Clamp risk
    risk = min(risk, 100)
    result["risk_score"] = risk
    result["flags"] = flags

    # Generate summary
    if risk >= 50:
        result["summary"] = "EXIF analysis reveals significant signs of image manipulation or metadata stripping."
    elif risk >= 25:
        result["summary"] = "EXIF analysis shows some anomalies worth investigating."
    else:
        result["summary"] = "EXIF metadata appears normal with no major red flags."

    return result
