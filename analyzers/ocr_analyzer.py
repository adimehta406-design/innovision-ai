"""
OCR Text Analyzer
Extracts text from screenshots and analyzes for misinformation
using AI-powered pattern recognition.
"""

import io
import logging
from PIL import Image
import numpy as np
import httpx
import json
import asyncio
from . import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert MISINFORMATION ANALYST.
Analyze the provided text (extracted from an image/screenshot) for indicators of fake news, clickbait, scams, or manipulated content.

Return a JSON response with:
1. "risk_score": Integer 0-100 (0=Safe, 100=Dangerous Misinformation/Scam)
2. "flags": List of strings (e.g., "Urgency Tactics", "Unverified Claim", "Clickbait")
3. "summary": A 1-sentence summary of the analysis.
4. "category": One of [SAFE, CLICKBAIT, SPAM, MISINFORMATION, UNVERIFIED, OPINION]

Focus on:
- Sensationalism / Clickbait
- Urgent calls to action (Forward this now!)
- Unverified health/political claims
- Scam patterns"""


def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Extract text from image using basic image processing and pytesseract if available.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))

        # Basic image checks
        gray = img.convert("L")
        arr = np.array(gray, dtype=np.float64)
        mean_val = arr.mean()
        
        # Try pytesseract
        try:
            import pytesseract
            # Tesseract location hints could be added here if needed
            extracted = pytesseract.image_to_string(img)
            return extracted.strip()
        except ImportError:
            pass
        except Exception:
            pass

        # If OCR fails or not installed, return minimal info to trigger analysis
        # In a real deployment, Tesseract is required. for this demo, we might return empty
        # or simulate based on image stats if we can't extract text.
        
        # For hackathon context, if we can't extract, we return empty string.
        # But to show "Brain" power, we might rely on the image description if we had multimodal input.
        # Since we only send text to this specific function, we return what we found.
        return ""

    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        return ""


async def analyze_ocr_ai(text: str) -> dict:
    """Analyze text using Gemini 2.0 Flash (Fast & Smart)."""
    result = {
        "text_extracted": text,
        "risk_score": 0,
        "flags": [],
        "summary": "No text detected.",
        "category": "SAFE"
    }

    if not text or len(text.strip()) < 5:
        return result

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                config.OPENROUTER_API_URL,
                headers=config.get_headers(config.GEMINI_API_KEY),
                json={
                    "model": config.GEMINI_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Analyze this text:\n\n{text}"}
                    ],
                    "response_format": { "type": "json_object" }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                ai_result = json.loads(content)
                result.update(ai_result)
            else:
                logger.error(f"OCR AI Analysis failed: {response.text}")
                result["summary"] = "AI analysis failed."

    except Exception as e:
        logger.error(f"OCR Analyzer Exception: {e}")
        result["summary"] = "Error during analysis."

    return result

