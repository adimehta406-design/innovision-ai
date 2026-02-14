"""
AI Verdict Generator
Uses OpenRouter API to generate a human-readable verdict
summarizing all forensic findings.
"""

import logging
import httpx
import asyncio
from . import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are TruthLens AI, an expert forensic image analyst. Given the results of multiple forensic analyses on an image, provide a clear, concise verdict.

Your response should include:
1. **Verdict**: One of: LIKELY AUTHENTIC, POSSIBLY MANIPULATED, LIKELY MANIPULATED, HIGHLY SUSPICIOUS
2. **Confidence**: Low/Medium/High
3. **Key Findings**: 2-3 bullet points of the most important findings
4. **Recommendation**: What the user should do (verify source, reverse image search, treat with caution, etc.)
5. **Context**: Brief explanation of what the forensic evidence means in simple terms.

**Language Instruction**:
- If the extracted text or context is in Hindi, provide the **Context** and **Recommendation** in Hindi.
- Otherwise, strictly use English.

Keep your response concise (under 200 words), professional, and actionable. Use simple language that a non-technical person can understand. Do NOT use markdown headers — use plain text with bullet points."""


async def query_model(client, model, api_key, context):
    """Query a specific model via OpenRouter."""
    try:
        response = await client.post(
            config.OPENROUTER_API_URL,
            headers=config.get_headers(api_key),
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze these forensic results and provide your verdict:\n\n{context}"}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            logger.error(f"Model {model} error: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Model {model} exception: {e}")
        return None


async def generate_verdict(risk_result: dict, analysis_data: dict) -> dict:
    """Generate AI-powered verdict from analysis results using Multi-Model Consensus."""
    result = {
        "verdict": "",
        "ai_analysis": "",
        "generated": False,
        "error": None,
        "models_used": []
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
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Single Model Query (Claude Opus 4.6)
            claude_resp = await query_model(client, config.CLAUDE_MODEL, config.CLAUDE_API_KEY, context)

            if isinstance(claude_resp, str) and claude_resp:
                result["ai_analysis"] = claude_resp
                result["generated"] = True
                result["models_used"] = ["Claude Opus 4.6"]

                # Extract verdict from response
                ai_lower = claude_resp.lower()
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
                result["error"] = "Both AI models failed to generate verdict."

    except Exception as e:
        logger.error(f"Verdict generation failed: {e}")
        result["error"] = str(e)

    # Fallback verdict if AI failed
    if not result["generated"]:
        score = risk_result["overall_score"]
        if score >= 75:
            result["verdict"] = "HIGHLY SUSPICIOUS"
            result["ai_analysis"] = "AI analysis unavailable. Based on forensic scores, this image shows strong indicators of manipulation or misinformation."
        elif score >= 50:
            result["verdict"] = "LIKELY MANIPULATED"
            result["ai_analysis"] = "AI analysis unavailable. Forensic analysis detected significant anomalies."
        elif score >= 25:
            result["verdict"] = "POSSIBLY MANIPULATED"
            result["ai_analysis"] = "AI analysis unavailable. Some minor anomalies were detected."
        else:
            result["verdict"] = "LIKELY AUTHENTIC"
            result["ai_analysis"] = "AI analysis unavailable. Forensic analysis shows minimal signs of manipulation."

    return result
