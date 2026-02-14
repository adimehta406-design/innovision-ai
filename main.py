"""
TruthLens – Fake News Visual Analyzer
Main FastAPI application with analysis pipeline.
"""

import io
import os
import time
import uuid
import base64
import logging
import numpy as np
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from analyzers.exif_analyzer import extract_exif
from analyzers.ela_analyzer import perform_ela
from analyzers.tamper_detector import detect_tampering
from analyzers.ocr_analyzer import analyze_ocr
from analyzers.ai_detector import detect_ai_generated
from analyzers.risk_scorer import compute_risk_score
from analyzers.verdict_generator import generate_verdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("truthlens")

# Create uploads directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# FastAPI app
app = FastAPI(
    title="Innovision API",
    description="Universal Fake News & Claim Verification System",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the main frontend page."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>TruthLens</h1><p>Frontend not found. Place index.html in static/</p>")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "TruthLens",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


# === Numpy JSON Encoder Helper ===
def convert_numpy(obj):
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_numpy(i) for i in obj]
    return obj

from pydantic import BaseModel
from analyzers.text_verifier import verify_text

class TextRequest(BaseModel):
    text: str

@app.post("/api/verify/text")
async def verify_text_endpoint(request: TextRequest):
    """Verify a text claim using web search and LLM analysis."""
    logger.info(f"Verifying text claim: {request.text[:50]}...")
    result = await verify_text(request.text)
    return convert_numpy(result)

@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """
    Upload and analyze an image for signs of manipulation/misinformation.
    Returns comprehensive forensic analysis results including text verification.
    """
    start_time = time.time()
    analysis_id = str(uuid.uuid4())[:8]

    logger.info(f"[{analysis_id}] Starting analysis of: {file.filename}")

    # Validate file
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (JPEG, PNG, WebP, etc.)")

    # Read file
    try:
        image_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    if len(image_bytes) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=400, detail="Image too large (max 20MB)")

    if len(image_bytes) < 100:
        raise HTTPException(status_code=400, detail="File appears to be empty or corrupted")


    # Create base64 preview of original image
    original_b64 = base64.b64encode(image_bytes).decode("utf-8")
    original_mime = file.content_type or "image/jpeg"

    try:
        # === Run Analysis Pipeline ===
        logger.info(f"[{analysis_id}] Running EXIF analysis...")
        exif_result = extract_exif(image_bytes)

        logger.info(f"[{analysis_id}] Running ELA...")
        ela_result = perform_ela(image_bytes)

        logger.info(f"[{analysis_id}] Running tampering detection...")
        tamper_result = detect_tampering(image_bytes)

        logger.info(f"[{analysis_id}] Running OCR analysis...")
        ocr_result = analyze_ocr(image_bytes)

        logger.info(f"[{analysis_id}] Running AI detection...")
        ai_result = detect_ai_generated(image_bytes)
        
        # === Text Verification (Universal Engine) ===
        text_verification = None
        extracted_text = ocr_result.get("text_extracted", "")
        # Only verify if significant text found (e.g., > 30 chars)
        if len(extracted_text.strip()) > 30:
            logger.info(f"[{analysis_id}] Verifying extracted text...")
            text_verification = await verify_text(extracted_text)
        else:
            text_verification = {
                "verdict": "SKIPPED",
                "explanation": "No significant text found to verify.",
                "truth_score": 0
            }

        # === Compute Risk Score ===
        logger.info(f"[{analysis_id}] Computing risk score...")
        risk_result = compute_risk_score(
            exif_result, ela_result, tamper_result, ocr_result, ai_result
        )
        
        # Adjust risk if text is proven FALSE
        if text_verification and text_verification.get("risk_level") == "CRITICAL":
            risk_result["overall_score"] = max(risk_result["overall_score"], 90)
            risk_result["risk_level"] = "CRITICAL"
            risk_result["risk_description"] += " Text content verified as FALSE/MISLEADING."

        # === Generate AI Verdict ===
        logger.info(f"[{analysis_id}] Generating AI verdict...")
        analysis_data = {
            "exif": exif_result,
            "ela": ela_result,
            "tampering": tamper_result,
            "ocr": ocr_result,
            "ai_detection": ai_result,
            "text_verification": text_verification
        }
        verdict_result = await generate_verdict(risk_result, analysis_data)

        # === Build Response ===
        elapsed = round(time.time() - start_time, 2)
        logger.info(f"[{analysis_id}] Analysis complete in {elapsed}s | Score: {risk_result['overall_score']} | Verdict: {verdict_result['verdict']}")

        response = {
            "analysis_id": analysis_id,
            "filename": file.filename,
            "file_size": len(image_bytes),
            "original_image": f"data:{original_mime};base64,{original_b64}",
            "analysis_time": elapsed,
            "timestamp": datetime.utcnow().isoformat(),

            # Risk Score
            "risk": risk_result,

            # AI Verdict
            "verdict": verdict_result,

            # Individual Analyses
            "exif": exif_result,
            "ela": {
                k: v for k, v in ela_result.items()
                if k != "ela_image_b64"  # Send separately
            },
            "ela_image": f"data:image/png;base64,{ela_result['ela_image_b64']}" if ela_result.get("ela_image_b64") else None,
            "tampering": {
                k: v for k, v in tamper_result.items()
                if k not in ("annotated_image_b64", "noise_map_b64")
            },
            "tamper_annotated_image": f"data:image/png;base64,{tamper_result['annotated_image_b64']}" if tamper_result.get("annotated_image_b64") else None,
            "noise_map_image": f"data:image/png;base64,{tamper_result['noise_map_b64']}" if tamper_result.get("noise_map_b64") else None,
            "ocr": ocr_result,
            "ai_detection": ai_result,
            "text_verification": text_verification
        }

        # Convert numpy types to native Python types
        response = convert_numpy(response)

        return JSONResponse(content=response)
        
    except Exception as e:
        import traceback
        error_msg = f"Analysis Error: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": error_msg, "trace": traceback.format_exc()}
        )



if __name__ == "__main__":
    import uvicorn
    # Use PORT environment variable for Railway, default to 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
