"""
Image Tampering Detector using OpenCV
Detects copy-move forgery, edge anomalies, noise inconsistencies,
and generates annotated images highlighting suspicious regions.
"""

import io
import base64
import logging
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def detect_tampering(image_bytes: bytes) -> dict:
    """Run OpenCV-based tampering detection on image bytes."""
    result = {
        "performed": False,
        "annotated_image_b64": None,
        "noise_map_b64": None,
        "copy_move_found": False,
        "copy_move_matches": 0,
        "edge_anomaly_score": 0.0,
        "noise_inconsistency": 0.0,
        "risk_score": 0,
        "flags": [],
        "summary": ""
    }

    try:
        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        annotated = img.copy()
        h, w = gray.shape[:2]
        risk = 0
        flags = []

        # === 1. Copy-Move Detection using ORB ===
        copy_move_matches = 0
        try:
            orb = cv2.ORB_create(nfeatures=1000)
            keypoints, descriptors = orb.detectAndCompute(gray, None)

            if descriptors is not None and len(descriptors) > 10:
                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
                matches = bf.knnMatch(descriptors, descriptors, k=2)

                suspicious_pairs = []
                for match_pair in matches:
                    if len(match_pair) >= 2:
                        m, n = match_pair[0], match_pair[1]
                        # Skip self-matches
                        if m.queryIdx == m.trainIdx:
                            continue
                        # Good match with spatial distance
                        if m.distance < 0.7 * n.distance:
                            pt1 = keypoints[m.queryIdx].pt
                            pt2 = keypoints[m.trainIdx].pt
                            dist = np.sqrt((pt1[0]-pt2[0])**2 + (pt1[1]-pt2[1])**2)
                            # Must be spatially separated (not just nearby similar textures)
                            if 50 < dist < max(w, h) * 0.8:
                                suspicious_pairs.append((m.queryIdx, m.trainIdx))

                copy_move_matches = len(suspicious_pairs)

                # Draw top matches on annotated image
                for i, (qi, ti) in enumerate(suspicious_pairs[:20]):
                    pt1 = tuple(map(int, keypoints[qi].pt))
                    pt2 = tuple(map(int, keypoints[ti].pt))
                    cv2.circle(annotated, pt1, 8, (0, 0, 255), 2)
                    cv2.circle(annotated, pt2, 8, (0, 0, 255), 2)
                    cv2.line(annotated, pt1, pt2, (0, 165, 255), 1)

        except Exception as e:
            logger.debug(f"Copy-move detection error: {e}")

        result["copy_move_matches"] = copy_move_matches
        if copy_move_matches > 15:
            result["copy_move_found"] = True
            flags.append(f"🔴 Copy-move forgery detected: {copy_move_matches} suspicious matching regions")
            risk += 45
        elif copy_move_matches > 5:
            flags.append(f"🟡 Possible copy-move: {copy_move_matches} similar region matches")
            risk += 20

        # === 2. Edge Anomaly Detection ===
        try:
            edges = cv2.Canny(gray, 50, 150)

            # Divide image into blocks and analyze edge density
            block_size = max(32, min(h, w) // 8)
            edge_densities = []
            for y in range(0, h - block_size, block_size):
                for x in range(0, w - block_size, block_size):
                    block = edges[y:y+block_size, x:x+block_size]
                    density = np.sum(block > 0) / (block_size * block_size)
                    edge_densities.append((density, x, y))

            if edge_densities:
                densities = [d[0] for d in edge_densities]
                mean_density = np.mean(densities)
                std_density = np.std(densities)

                # Find anomalous blocks (very high or very low edge density)
                anomalous = 0
                for density, x, y in edge_densities:
                    if abs(density - mean_density) > 2.5 * std_density and std_density > 0.01:
                        anomalous += 1
                        cv2.rectangle(annotated, (x, y), (x+block_size, y+block_size),
                                     (255, 0, 255), 2)

                edge_anomaly_score = (anomalous / len(edge_densities)) * 100 if edge_densities else 0
                result["edge_anomaly_score"] = round(edge_anomaly_score, 2)

                if edge_anomaly_score > 15:
                    flags.append(f"🟡 Edge density anomalies in {edge_anomaly_score:.1f}% of blocks")
                    risk += 15
                elif edge_anomaly_score > 5:
                    risk += 5

        except Exception as e:
            logger.debug(f"Edge analysis error: {e}")

        # === 3. Noise Inconsistency Analysis ===
        try:
            # Apply Laplacian to detect noise patterns
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)

            block_size = max(32, min(h, w) // 8)
            noise_levels = []
            for y in range(0, h - block_size, block_size):
                for x in range(0, w - block_size, block_size):
                    block = laplacian[y:y+block_size, x:x+block_size]
                    noise_levels.append((np.std(block), x, y))

            if noise_levels:
                levels = [n[0] for n in noise_levels]
                mean_noise = np.mean(levels)
                std_noise = np.std(levels)
                noise_cv = (std_noise / mean_noise * 100) if mean_noise > 0 else 0
                result["noise_inconsistency"] = round(noise_cv, 2)

                if noise_cv > 60:
                    flags.append(f"🔴 High noise inconsistency ({noise_cv:.1f}%) — different image sources likely combined")
                    risk += 30
                elif noise_cv > 35:
                    flags.append(f"🟡 Moderate noise variation ({noise_cv:.1f}%) — possible compositing")
                    risk += 15

                # Generate noise map
                noise_map = np.zeros((h, w, 3), dtype=np.uint8)
                for noise_val, x, y in noise_levels:
                    if mean_noise > 0 and std_noise > 0:
                        z_score = abs(noise_val - mean_noise) / std_noise
                        intensity = min(int(z_score * 80), 255)
                    else:
                        intensity = 0
                    cv2.rectangle(noise_map, (x, y), (x+block_size, y+block_size),
                                 (intensity, 50, 255 - intensity), -1)

                # Encode noise map
                _, noise_buf = cv2.imencode('.png', noise_map)
                result["noise_map_b64"] = base64.b64encode(noise_buf.tobytes()).decode("utf-8")

        except Exception as e:
            logger.debug(f"Noise analysis error: {e}")

        # === 4. Encode annotated image ===
        try:
            _, ann_buf = cv2.imencode('.png', annotated)
            result["annotated_image_b64"] = base64.b64encode(ann_buf.tobytes()).decode("utf-8")
        except Exception as e:
            logger.debug(f"Could not encode annotated image: {e}")

        risk = min(risk, 100)
        result["risk_score"] = risk
        result["flags"] = flags
        result["performed"] = True

        if risk >= 50:
            result["summary"] = "Significant tampering indicators detected including copy-move or noise inconsistencies."
        elif risk >= 25:
            result["summary"] = "Some structural anomalies detected that may indicate image manipulation."
        else:
            result["summary"] = "No strong tampering indicators found in structural analysis."

    except Exception as e:
        logger.error(f"Tampering detection failed: {e}")
        result["summary"] = f"Tampering detection error: {str(e)}"
        result["risk_score"] = 5

    return result
