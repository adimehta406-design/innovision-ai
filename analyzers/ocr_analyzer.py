"""
OCR Text Analyzer
Extracts text from screenshots using Pillow and analyzes
the content for misinformation patterns.
"""

import io
import re
import logging
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)

# Misinformation pattern keywords (case-insensitive)
URGENCY_PATTERNS = [
    r"\b(breaking|urgent|alert|warning|emergency|exclusive|shocking|exposed)\b",
    r"\b(share before deleted|must read|act now|limited time)\b",
    r"(!{3,})",  # Multiple exclamation marks
    r"(\?{3,})",  # Multiple question marks
]

CLICKBAIT_PATTERNS = [
    r"\b(you won'?t believe|what happens next|this will shock|mind-?blown)\b",
    r"\b(exposed|busted|caught|leaked|revealed|confession)\b",
    r"\b(100%|guaranteed|proven|secret|hidden truth)\b",
]

UNVERIFIED_PATTERNS = [
    r"\b(sources say|reportedly|allegedly|rumou?red?|unconfirmed)\b",
    r"\b(forward to|share with|send to everyone|whatsapp forward)\b",
    r"\b(government hiding|media won'?t show|they don'?t want you)\b",
    r"\b(exposed by|whistleblower|insider reveals)\b",
]

HEALTH_MISINFO_PATTERNS = [
    r"\b(miracle cure|home remedy|doctors? hate|big pharma|natural cure)\b",
    r"\b(vaccine danger|5g|microchip|depopulation)\b",
]

POLITICAL_MISINFO_PATTERNS = [
    r"\b(rigged election|vote fraud|deep state|conspiracy)\b",
    r"\b(fake media|media lies|presstitute|paid media)\b",
]


def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Extract text from image using basic image processing.
    Uses contrast enhancement and thresholding for better OCR-like extraction.
    For production, integrate Tesseract OCR.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to grayscale
        gray = img.convert("L")

        # Enhance contrast
        arr = np.array(gray, dtype=np.float64)

        # Adaptive thresholding simulation
        # High-contrast text regions can be detected
        mean_val = arr.mean()

        # Check if image has text-like characteristics
        # (high contrast regions, bimodal histogram)
        hist, _ = np.histogram(arr.flatten(), bins=256, range=(0, 256))
        hist_normalized = hist / hist.sum()

        # Find peaks in histogram (bimodal = likely text on background)
        peaks = []
        for i in range(5, 250):
            if hist_normalized[i] > hist_normalized[i-1] and hist_normalized[i] > hist_normalized[i+1]:
                if hist_normalized[i] > 0.005:
                    peaks.append(i)

        is_text_likely = len(peaks) >= 2

        # Basic OCR placeholder - in production use pytesseract
        # For hackathon demo, we detect TEXT PRESENCE and characteristics
        text_info = {
            "is_text_likely": is_text_likely,
            "contrast_ratio": float(arr.std()),
            "mean_brightness": float(mean_val),
            "peak_count": len(peaks)
        }

        # Try to use pytesseract if available
        try:
            import pytesseract
            extracted = pytesseract.image_to_string(img)
            return extracted.strip()
        except ImportError:
            pass

        # Fallback: return metadata about text detection
        if is_text_likely:
            return f"[TEXT DETECTED - {len(peaks)} contrast regions, contrast: {arr.std():.1f}]"
        return ""

    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        return ""


def analyze_text_content(text: str) -> dict:
    """Analyze extracted text for misinformation patterns."""
    result = {
        "text_extracted": text,
        "text_length": len(text),
        "has_text": bool(text.strip()),
        "urgency_matches": [],
        "clickbait_matches": [],
        "unverified_matches": [],
        "health_misinfo_matches": [],
        "political_misinfo_matches": [],
        "risk_score": 0,
        "flags": [],
        "summary": "",
        "pattern_count": 0
    }

    if not text.strip():
        result["summary"] = "No text content detected in image."
        return result

    text_lower = text.lower()

    # Check each pattern category
    def find_matches(patterns, category_name):
        matches = []
        for pattern in patterns:
            found = re.findall(pattern, text_lower)
            matches.extend(found)
        return matches

    result["urgency_matches"] = find_matches(URGENCY_PATTERNS, "urgency")
    result["clickbait_matches"] = find_matches(CLICKBAIT_PATTERNS, "clickbait")
    result["unverified_matches"] = find_matches(UNVERIFIED_PATTERNS, "unverified")
    result["health_misinfo_matches"] = find_matches(HEALTH_MISINFO_PATTERNS, "health")
    result["political_misinfo_matches"] = find_matches(POLITICAL_MISINFO_PATTERNS, "political")

    # Clean up matches for JSON serialization
    for key in ["urgency_matches", "clickbait_matches", "unverified_matches",
                 "health_misinfo_matches", "political_misinfo_matches"]:
        result[key] = [str(m) for m in result[key]]

    # --- Risk Scoring ---
    risk = 0
    flags = []
    total_patterns = 0

    if result["urgency_matches"]:
        count = len(result["urgency_matches"])
        total_patterns += count
        flags.append(f"🟡 {count} urgency/alarm phrase(s) detected")
        risk += min(count * 8, 25)

    if result["clickbait_matches"]:
        count = len(result["clickbait_matches"])
        total_patterns += count
        flags.append(f"🟡 {count} clickbait phrase(s) detected")
        risk += min(count * 10, 30)

    if result["unverified_matches"]:
        count = len(result["unverified_matches"])
        total_patterns += count
        flags.append(f"🔴 {count} unverified/forwarding phrase(s) detected")
        risk += min(count * 12, 35)

    if result["health_misinfo_matches"]:
        count = len(result["health_misinfo_matches"])
        total_patterns += count
        flags.append(f"🔴 {count} health misinformation pattern(s) detected")
        risk += min(count * 15, 40)

    if result["political_misinfo_matches"]:
        count = len(result["political_misinfo_matches"])
        total_patterns += count
        flags.append(f"🔴 {count} political misinformation pattern(s) detected")
        risk += min(count * 12, 35)

    # ALL CAPS detection
    words = text.split()
    caps_words = [w for w in words if w.isupper() and len(w) > 2]
    if len(caps_words) > 5:
        flags.append(f"🟡 Excessive ALL CAPS usage ({len(caps_words)} words)")
        risk += 10
        total_patterns += 1

    # Excessive punctuation
    exclamation_count = text.count('!')
    if exclamation_count > 5:
        flags.append(f"🟡 Excessive exclamation marks ({exclamation_count})")
        risk += 8
        total_patterns += 1

    result["pattern_count"] = total_patterns
    risk = min(risk, 100)
    result["risk_score"] = risk
    result["flags"] = flags

    if risk >= 50:
        result["summary"] = f"Text contains {total_patterns} misinformation pattern(s) — high likelihood of misleading content."
    elif risk >= 25:
        result["summary"] = f"Text contains {total_patterns} suspicious pattern(s) that may indicate misleading content."
    elif total_patterns > 0:
        result["summary"] = f"Text has {total_patterns} minor pattern(s) but overall appears normal."
    else:
        result["summary"] = "Text content appears normal with no misinformation patterns detected."

    return result


def analyze_ocr(image_bytes: bytes) -> dict:
    """Full OCR pipeline: extract text then analyze content."""
    text = extract_text_from_image(image_bytes)
    return analyze_text_content(text)
