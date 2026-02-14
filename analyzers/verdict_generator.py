"""
AI Verdict Generator
Uses OpenRouter API to generate a human-readable verdict
summarizing all forensic findings.
"""

import logging
import httpx

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = "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"

SYSTEM_PROMPT = """You are TruthLens AI, an expert forensic image analyst. Given the results of multiple forensic analyses on an image, provide a clear, concise verdict.

Your response should include:
1. **Verdict**: One of: LIKELY AUTHENTIC, POSSIBLY MANIPULATED, LIKELY MANIPULATED, HIGHLY SUSPICIOUS
2. **Confidence**: Low/Medium/High
3. **Key Findings**: 2-3 bullet points of the most important findings
4. **Recommendation**: What the user should do (verify source, reverse image search, treat with caution, etc.)
5. **Context**: Brief explanation of what the forensic evidence means in simple terms

Keep your response concise (under 200 words), professional, and actionable. Use simple language that a non-technical person can understand. Do NOT use markdown headers — use plain text with bullet points."""


async def generate_verdict(risk_result: dict, analysis_data: dict) -> dict:
    """Generate AI-powered verdict from analysis results."""
    result = {
        "verdict": "",
        "ai_analysis": "",
        "generated": False,
        "error": None
    }

    # Build context from analysis results
    context_parts = []
    context_parts.append(f"Overall Risk Score: {risk_result['overall_score']}/100 ({risk_result['risk_level']})")
    context_parts.append(f"Risk Description: {risk_result['risk_description']}")

    # Add individual analyzer summaries
    analyzer_keys = {
        "exif": "EXIF Metadata Analysis",
        "ela": "Error Level Analysis",
        "tampering": "Tampering Detection",
        "ocr": "OCR Text Analysis",
        "ai_detection": "AI Generation Detection"
    }

    for key, name in analyzer_keys.items():
        if key in analysis_data:
            data = analysis_data[key]
            score = data.get("risk_score", 0)
            summary = data.get("summary", "N/A")
            flags = data.get("flags", [])
            context_parts.append(f"\n{name} (Score: {score}/100):")
            context_parts.append(f"  Summary: {summary}")
            if flags:
                context_parts.append(f"  Flags: {'; '.join(flags[:5])}")

    # Add top concerns
    if risk_result.get("top_concerns"):
        context_parts.append("\nTop Concerns:")
        for concern in risk_result["top_concerns"]:
            context_parts.append(f"  - {concern['analyzer']}: {concern['summary']}")

    context = "\n".join(context_parts)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://truthlens.app",
                    "X-Title": "TruthLens - Fake News Analyzer"
                },
                json={
                    "model": "google/gemini-2.0-flash-001",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Analyze these forensic results and provide your verdict:\n\n{context}"}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                }
            )

            if response.status_code == 200:
                data = response.json()
                ai_text = data["choices"][0]["message"]["content"]
                result["ai_analysis"] = ai_text
                result["generated"] = True

                # Extract verdict from response
                ai_lower = ai_text.lower()
                if "highly suspicious" in ai_lower:
                    result["verdict"] = "HIGHLY SUSPICIOUS"
                elif "likely manipulated" in ai_lower:
                    result["verdict"] = "LIKELY MANIPULATED"
                elif "possibly manipulated" in ai_lower:
                    result["verdict"] = "POSSIBLY MANIPULATED"
                elif "likely authentic" in ai_lower:
                    result["verdict"] = "LIKELY AUTHENTIC"
                else:
                    # Fallback based on risk score
                    score = risk_result["overall_score"]
                    if score >= 75:
                        result["verdict"] = "HIGHLY SUSPICIOUS"
                    elif score >= 50:
                        result["verdict"] = "LIKELY MANIPULATED"
                    elif score >= 25:
                        result["verdict"] = "POSSIBLY MANIPULATED"
                    else:
                        result["verdict"] = "LIKELY AUTHENTIC"
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                result["error"] = f"API returned status {response.status_code}"

    except httpx.TimeoutException:
        logger.error("OpenRouter API timeout")
        result["error"] = "AI analysis timed out"
    except Exception as e:
        logger.error(f"Verdict generation failed: {e}")
        result["error"] = str(e)

    # Fallback verdict if AI failed
    if not result["generated"]:
        score = risk_result["overall_score"]
        if score >= 75:
            result["verdict"] = "HIGHLY SUSPICIOUS"
            result["ai_analysis"] = "AI analysis unavailable. Based on forensic scores, this image shows strong indicators of manipulation or misinformation. Exercise extreme caution and verify from trusted sources."
        elif score >= 50:
            result["verdict"] = "LIKELY MANIPULATED"
            result["ai_analysis"] = "AI analysis unavailable. Forensic analysis detected significant anomalies. This image may have been edited or contains misleading content. Verify before sharing."
        elif score >= 25:
            result["verdict"] = "POSSIBLY MANIPULATED"
            result["ai_analysis"] = "AI analysis unavailable. Some minor anomalies were detected. While not conclusive, consider verifying the image source."
        else:
            result["verdict"] = "LIKELY AUTHENTIC"
            result["ai_analysis"] = "AI analysis unavailable. Forensic analysis shows minimal signs of manipulation. The image appears authentic, but always verify important claims."

    return result
