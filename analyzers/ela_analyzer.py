"""
Error Level Analysis (ELA)
Re-saves image at a known quality and computes pixel-level differences
to reveal regions that have been edited or spliced.
"""

import io
import base64
import logging
import numpy as np
from PIL import Image, ImageChops, ImageEnhance

logger = logging.getLogger(__name__)

ELA_QUALITY = 90  # Re-save quality level
ELA_SCALE = 15     # Amplification factor for visibility


def perform_ela(image_bytes: bytes) -> dict:
    """Perform Error Level Analysis on image bytes."""
    result = {
        "performed": False,
        "ela_image_b64": None,
        "max_error": 0,
        "mean_error": 0.0,
        "std_error": 0.0,
        "risk_score": 0,
        "flags": [],
        "summary": "",
        "hotspot_percentage": 0.0
    }

    try:
        original = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        logger.error(f"Failed to open image for ELA: {e}")
        result["summary"] = "Could not open image for ELA."
        return result

    try:
        # Re-save at known quality
        buffer = io.BytesIO()
        original.save(buffer, format="JPEG", quality=ELA_QUALITY)
        buffer.seek(0)
        resaved = Image.open(buffer).convert("RGB")

        # Compute difference
        diff = ImageChops.difference(original, resaved)

        # Convert to numpy for analysis
        diff_array = np.array(diff, dtype=np.float64)

        # Calculate statistics
        max_error = int(diff_array.max())
        mean_error = float(diff_array.mean())
        std_error = float(diff_array.std())

        # Calculate hotspot percentage (pixels with high error)
        threshold = mean_error + 2 * std_error
        if threshold < 10:
            threshold = 10
        hotspot_mask = diff_array.max(axis=2) > threshold
        hotspot_percentage = float(hotspot_mask.sum()) / (diff_array.shape[0] * diff_array.shape[1]) * 100

        # Enhance the difference image for visualization
        # Scale up the differences to make them visible
        ela_enhanced = diff_array * ELA_SCALE
        ela_enhanced = np.clip(ela_enhanced, 0, 255).astype(np.uint8)

        # Apply a colormap-like effect for better visualization
        # Red channel dominant for high error areas
        ela_visual = np.zeros_like(ela_enhanced)
        gray_diff = ela_enhanced.mean(axis=2)

        # Create heat-map: low=blue, medium=yellow, high=red
        ela_visual[:, :, 0] = np.clip(gray_diff * 2, 0, 255)       # Red
        ela_visual[:, :, 1] = np.clip(gray_diff * 1.2, 0, 200)     # Green
        ela_visual[:, :, 2] = np.clip(100 - gray_diff, 0, 255)     # Blue

        # Convert to image and base64
        ela_img = Image.fromarray(ela_visual.astype(np.uint8))
        ela_buffer = io.BytesIO()
        ela_img.save(ela_buffer, format="PNG")
        ela_buffer.seek(0)
        ela_b64 = base64.b64encode(ela_buffer.read()).decode("utf-8")

        result["performed"] = True
        result["ela_image_b64"] = ela_b64
        result["max_error"] = max_error
        result["mean_error"] = round(mean_error, 2)
        result["std_error"] = round(std_error, 2)
        result["hotspot_percentage"] = round(hotspot_percentage, 2)

        # --- Risk Assessment ---
        risk = 0
        flags = []

        # High standard deviation indicates mixing of different compression levels
        if std_error > 15:
            flags.append("🔴 High ELA variance — strong indicator of image splicing/editing")
            risk += 45
        elif std_error > 8:
            flags.append("🟡 Moderate ELA variance — possible editing detected")
            risk += 25
        elif std_error > 4:
            flags.append("ℹ️ Slight ELA variance — minor inconsistencies")
            risk += 10

        # Hotspot analysis
        if hotspot_percentage > 15:
            flags.append(f"🔴 {hotspot_percentage:.1f}% of image shows high error — widespread tampering likely")
            risk += 30
        elif hotspot_percentage > 5:
            flags.append(f"🟡 {hotspot_percentage:.1f}% of image shows elevated error — localized editing possible")
            risk += 15
        elif hotspot_percentage > 1:
            flags.append(f"ℹ️ {hotspot_percentage:.1f}% of image shows slightly elevated error")
            risk += 5

        # Max error
        if max_error > 200:
            flags.append("🔴 Extreme maximum error level detected")
            risk += 15
        elif max_error > 100:
            flags.append("🟡 High maximum error level detected")
            risk += 8

        risk = min(risk, 100)
        result["risk_score"] = risk
        result["flags"] = flags

        if risk >= 50:
            result["summary"] = "ELA reveals significant compression inconsistencies indicating image manipulation."
        elif risk >= 25:
            result["summary"] = "ELA shows some compression anomalies that may indicate editing."
        else:
            result["summary"] = "ELA shows relatively uniform compression levels — no strong editing indicators."

    except Exception as e:
        logger.error(f"ELA analysis failed: {e}")
        result["summary"] = f"ELA analysis encountered an error: {str(e)}"
        result["risk_score"] = 10

    return result
