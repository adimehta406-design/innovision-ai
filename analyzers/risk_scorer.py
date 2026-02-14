"""
Risk Scoring Engine
Combines results from all analyzers into a weighted composite risk score.
"""

import logging

logger = logging.getLogger(__name__)

# Weights for each analyzer (must sum to 1.0)
WEIGHTS = {
    "exif": 0.20,
    "ela": 0.25,
    "tampering": 0.25,
    "ocr": 0.15,
    "ai_detection": 0.15
}

RISK_LEVELS = [
    (25, "LOW", "🟢", "Image appears authentic with minimal risk indicators."),
    (50, "MEDIUM", "🟡", "Some anomalies detected — manual verification recommended."),
    (75, "HIGH", "🟠", "Significant manipulation indicators found — treat with caution."),
    (100, "CRITICAL", "🔴", "Strong evidence of manipulation or misinformation detected.")
]


def compute_risk_score(
    exif_result: dict,
    ela_result: dict,
    tamper_result: dict,
    ocr_result: dict,
    ai_result: dict
) -> dict:
    """Compute weighted risk score from all analyzer results."""

    # Extract individual scores
    scores = {
        "exif": exif_result.get("risk_score", 0),
        "ela": ela_result.get("risk_score", 0),
        "tampering": tamper_result.get("risk_score", 0),
        "ocr": ocr_result.get("risk_score", 0),
        "ai_detection": ai_result.get("risk_score", 0)
    }

    # Compute weighted score
    weighted_score = sum(scores[k] * WEIGHTS[k] for k in scores)

    # Bonus risk for multiple high-scoring analyzers
    high_count = sum(1 for s in scores.values() if s >= 50)
    if high_count >= 3:
        weighted_score = min(weighted_score + 15, 100)
    elif high_count >= 2:
        weighted_score = min(weighted_score + 8, 100)

    # Determine risk level
    final_score = round(weighted_score, 1)
    risk_level = "LOW"
    risk_emoji = "🟢"
    risk_description = RISK_LEVELS[0][3]

    for threshold, level, emoji, desc in RISK_LEVELS:
        if final_score <= threshold:
            risk_level = level
            risk_emoji = emoji
            risk_description = desc
            break
    else:
        risk_level = "CRITICAL"
        risk_emoji = "🔴"
        risk_description = RISK_LEVELS[-1][3]

    # Collect all flags from all analyzers
    all_flags = []
    for r in [exif_result, ela_result, tamper_result, ocr_result, ai_result]:
        all_flags.extend(r.get("flags", []))

    # Build detailed breakdown
    breakdown = []
    analyzer_names = {
        "exif": "EXIF Metadata",
        "ela": "Error Level Analysis",
        "tampering": "Tampering Detection",
        "ocr": "Text/OCR Analysis",
        "ai_detection": "AI Generation Detection"
    }

    for key, name in analyzer_names.items():
        score = scores[key]
        weight = WEIGHTS[key]
        weighted = round(score * weight, 1)
        level = "LOW" if score <= 25 else "MEDIUM" if score <= 50 else "HIGH" if score <= 75 else "CRITICAL"
        breakdown.append({
            "analyzer": name,
            "raw_score": score,
            "weight": f"{weight*100:.0f}%",
            "weighted_score": weighted,
            "level": level
        })

    # Top concerns (highest scoring analyzers)
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_concerns = []
    for key, score in sorted_scores:
        if score >= 25:
            analyzer_map = {
                "exif": exif_result,
                "ela": ela_result,
                "tampering": tamper_result,
                "ocr": ocr_result,
                "ai_detection": ai_result
            }
            top_concerns.append({
                "analyzer": analyzer_names[key],
                "score": score,
                "summary": analyzer_map[key].get("summary", "")
            })

    return {
        "overall_score": final_score,
        "risk_level": risk_level,
        "risk_emoji": risk_emoji,
        "risk_description": risk_description,
        "breakdown": breakdown,
        "top_concerns": top_concerns[:3],
        "all_flags": all_flags,
        "individual_scores": scores,
        "high_risk_analyzers": high_count
    }
