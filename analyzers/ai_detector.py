"""
AI-Generated Image Detector
Uses statistical analysis on frequency domain, texture uniformity,
and color distribution to estimate if an image was AI-generated.
"""

import io
import logging
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def detect_ai_generated(image_bytes: bytes) -> dict:
    """Detect if an image was AI-generated using statistical analysis."""
    result = {
        "performed": False,
        "is_ai_generated": False,
        "confidence": 0.0,
        "frequency_score": 0.0,
        "texture_score": 0.0,
        "color_score": 0.0,
        "symmetry_score": 0.0,
        "risk_score": 0,
        "flags": [],
        "summary": ""
    }

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]

        # Resize for consistent analysis
        analysis_size = 512
        if max(h, w) > analysis_size:
            scale = analysis_size / max(h, w)
            img_resized = cv2.resize(img, None, fx=scale, fy=scale)
            gray_resized = cv2.resize(gray, None, fx=scale, fy=scale)
        else:
            img_resized = img
            gray_resized = gray

        scores = []

        # === 1. Frequency Domain Analysis (DCT) ===
        try:
            # AI images often have unusual frequency distributions
            gray_float = np.float32(gray_resized)

            # Compute DCT on blocks
            block_size = 8
            dct_energies = []
            rh, rw = gray_resized.shape[:2]

            for y in range(0, rh - block_size, block_size):
                for x in range(0, rw - block_size, block_size):
                    block = gray_float[y:y+block_size, x:x+block_size]
                    dct_block = cv2.dct(block)
                    # High frequency energy ratio
                    total_energy = np.sum(np.abs(dct_block))
                    if total_energy > 0:
                        high_freq = np.sum(np.abs(dct_block[4:, 4:])) / total_energy
                        dct_energies.append(high_freq)

            if dct_energies:
                mean_hf = np.mean(dct_energies)
                std_hf = np.std(dct_energies)

                # AI images tend to have more uniform frequency distribution
                # (less natural high-frequency detail)
                freq_anomaly = 0
                if mean_hf < 0.05:  # Very low high-frequency content
                    freq_anomaly = 70
                elif mean_hf < 0.10:
                    freq_anomaly = 40
                elif std_hf < 0.02:  # Very uniform frequency distribution
                    freq_anomaly = 50

                result["frequency_score"] = round(freq_anomaly, 2)
                scores.append(freq_anomaly)

        except Exception as e:
            logger.debug(f"Frequency analysis error: {e}")
            scores.append(0)

        # === 2. Texture Uniformity Analysis ===
        try:
            # AI images often have unnaturally smooth textures
            laplacian = cv2.Laplacian(gray_resized, cv2.CV_64F)

            # Analyze texture in blocks
            block_size = 32
            texture_vars = []
            rh, rw = gray_resized.shape[:2]

            for y in range(0, rh - block_size, block_size):
                for x in range(0, rw - block_size, block_size):
                    block = laplacian[y:y+block_size, x:x+block_size]
                    texture_vars.append(np.var(block))

            if texture_vars:
                # Coefficient of variation of texture
                mean_tex = np.mean(texture_vars)
                std_tex = np.std(texture_vars)
                cv_tex = (std_tex / mean_tex) if mean_tex > 0 else 0

                texture_anomaly = 0
                if cv_tex < 0.5:  # Very uniform texture (AI-like)
                    texture_anomaly = 60
                elif cv_tex < 1.0:
                    texture_anomaly = 30
                elif cv_tex > 3.0:  # Also suspicious — too varied
                    texture_anomaly = 25

                result["texture_score"] = round(texture_anomaly, 2)
                scores.append(texture_anomaly)

        except Exception as e:
            logger.debug(f"Texture analysis error: {e}")
            scores.append(0)

        # === 3. Color Distribution Analysis ===
        try:
            # AI images may have unusual color distributions
            hsv = cv2.cvtColor(img_resized, cv2.COLOR_BGR2HSV)
            h_channel = hsv[:, :, 0].flatten()
            s_channel = hsv[:, :, 1].flatten()

            # Check for unnaturally smooth color transitions
            h_hist, _ = np.histogram(h_channel, bins=180, range=(0, 180))
            h_hist = h_hist.astype(float) / h_hist.sum()

            # Entropy of hue distribution
            h_entropy = -np.sum(h_hist[h_hist > 0] * np.log2(h_hist[h_hist > 0]))

            # Very low entropy = limited color palette (possible AI)
            color_anomaly = 0
            if h_entropy < 3.0:
                color_anomaly = 40
            elif h_entropy < 4.5:
                color_anomaly = 20

            # Check saturation uniformity
            s_std = np.std(s_channel)
            if s_std < 30:  # Very uniform saturation
                color_anomaly += 20

            result["color_score"] = round(min(color_anomaly, 100), 2)
            scores.append(min(color_anomaly, 100))

        except Exception as e:
            logger.debug(f"Color analysis error: {e}")
            scores.append(0)

        # === 4. Symmetry Analysis ===
        try:
            # AI images sometimes exhibit unusual symmetry
            rh, rw = gray_resized.shape[:2]
            left = gray_resized[:, :rw//2]
            right = cv2.flip(gray_resized[:, rw//2:rw//2*2], 1)

            if left.shape == right.shape:
                diff = np.abs(left.astype(float) - right.astype(float))
                symmetry = 1 - (np.mean(diff) / 128)

                symmetry_anomaly = 0
                if symmetry > 0.85:  # Very high symmetry
                    symmetry_anomaly = 50
                elif symmetry > 0.75:
                    symmetry_anomaly = 25

                result["symmetry_score"] = round(symmetry_anomaly, 2)
                scores.append(symmetry_anomaly)

        except Exception as e:
            logger.debug(f"Symmetry analysis error: {e}")
            scores.append(0)

        # === Combine Scores ===
        if scores:
            confidence = np.mean(scores)
        else:
            confidence = 0

        result["confidence"] = round(confidence, 2)
        result["is_ai_generated"] = confidence > 45
        result["performed"] = True

        # Risk score and flags
        risk = int(min(confidence, 100))
        flags = []

        if confidence > 60:
            flags.append("🔴 High probability of AI-generated image")
            risk = min(int(confidence), 100)
        elif confidence > 40:
            flags.append("🟡 Moderate indicators of AI generation")
            risk = int(confidence * 0.8)
        elif confidence > 20:
            flags.append("ℹ️ Some minor AI-like characteristics detected")
            risk = int(confidence * 0.5)
        else:
            flags.append("✅ Image appears to be naturally captured")
            risk = int(confidence * 0.3)

        if result["frequency_score"] > 50:
            flags.append("🟡 Unusual frequency domain pattern (common in AI images)")
        if result["texture_score"] > 40:
            flags.append("🟡 Unnaturally uniform texture detected")
        if result["symmetry_score"] > 40:
            flags.append("ℹ️ High bilateral symmetry detected")

        result["risk_score"] = min(risk, 100)
        result["flags"] = flags

        if confidence > 60:
            result["summary"] = "Statistical analysis strongly suggests this image may be AI-generated."
        elif confidence > 40:
            result["summary"] = "Some characteristics suggest possible AI generation, but not conclusive."
        else:
            result["summary"] = "Image appears to be naturally captured or photographed."

    except Exception as e:
        logger.error(f"AI detection failed: {e}")
        result["summary"] = f"AI detection error: {str(e)}"
        result["risk_score"] = 5

    return result
