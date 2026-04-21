"""
Image Comparison Routes using OpenCV
POST /api/image/compare  - Compare two images using ORB feature matching
POST /api/image/compare-files - Compare by filenames stored in DB
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
import os
import uuid

image_bp = Blueprint("image", __name__)


def load_opencv():
    """Lazy import OpenCV to avoid startup crash if not installed."""
    try:
        import cv2
        import numpy as np
        return cv2, np
    except ImportError:
        return None, None


def compare_images_orb(img1_path: str, img2_path: str) -> dict:
    """
    Compare two images using ORB (Oriented FAST and Rotated BRIEF) feature matching.
    Returns similarity score and match details.
    """
    cv2, np = load_opencv()

    if cv2 is None:
        # OpenCV not installed - return simulated result for development
        import random
        score = random.randint(50, 95)
        return {
            "method":           "simulated",
            "similarityScore":  score,
            "matchedKeypoints": random.randint(20, 80),
            "totalKeypoints1":  random.randint(80, 150),
            "totalKeypoints2":  random.randint(80, 150),
            "passed":           score >= 60,
            "note":             "OpenCV not installed - using simulated comparison"
        }

    # Load images
    img1 = cv2.imread(img1_path)
    img2 = cv2.imread(img2_path)

    if img1 is None or img2 is None:
        return {
            "error":           "Could not load one or both images",
            "similarityScore": 0,
            "passed":          False
        }

    # Resize to standard size for fair comparison
    TARGET_SIZE = (400, 400)
    img1_resized = cv2.resize(img1, TARGET_SIZE)
    img2_resized = cv2.resize(img2, TARGET_SIZE)

    # Convert to grayscale
    gray1 = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2GRAY)

    # ── ORB Feature Extraction ─────────────────────────────────────────────────
    orb = cv2.ORB_create(nfeatures=500)
    kp1, des1 = orb.detectAndCompute(gray1, None)
    kp2, des2 = orb.detectAndCompute(gray2, None)

    if des1 is None or des2 is None or len(kp1) == 0 or len(kp2) == 0:
        return {
            "method":          "ORB",
            "similarityScore": 0,
            "matchedKeypoints": 0,
            "totalKeypoints1": len(kp1) if kp1 else 0,
            "totalKeypoints2": len(kp2) if kp2 else 0,
            "passed":          False,
            "note":            "No keypoints detected in one or both images"
        }

    # ── BFMatcher with Hamming distance ───────────────────────────────────────
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

    # KNN Match
    try:
        matches = bf.knnMatch(des1, des2, k=2)
    except Exception as e:
        return {"error": str(e), "similarityScore": 0, "passed": False}

    # Lowe's ratio test to filter good matches
    good_matches = []
    for match_pair in matches:
        if len(match_pair) == 2:
            m, n = match_pair
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)

    # ── Similarity Score Calculation ──────────────────────────────────────────
    max_possible  = min(len(kp1), len(kp2))
    raw_ratio     = len(good_matches) / max_possible if max_possible > 0 else 0

    # Apply sigmoid-like scaling for better score distribution
    import math
    scaled = 1 / (1 + math.exp(-10 * (raw_ratio - 0.3)))
    score  = round(scaled * 100)
    score  = max(0, min(100, score))  # clamp to 0-100

    # ── Structural Similarity (SSIM bonus) ────────────────────────────────────
    try:
        from skimage.metrics import structural_similarity as ssim
        ssim_score = ssim(gray1, gray2) * 100
        # Weighted average: 70% ORB + 30% SSIM
        final_score = round(0.7 * score + 0.3 * ssim_score)
    except ImportError:
        final_score = score

    return {
        "method":           "ORB + BFMatcher (Lowe's Ratio Test)",
        "similarityScore":  final_score,
        "matchedKeypoints": len(good_matches),
        "totalKeypoints1":  len(kp1),
        "totalKeypoints2":  len(kp2),
        "rawRatio":         round(raw_ratio * 100, 2),
        "passed":           final_score >= 60,
        "threshold":        60,
        "note":             "ORB feature matching with Lowe's ratio test"
    }


def compare_images_histogram(img1_path: str, img2_path: str) -> dict:
    """
    Fallback: Compare images using color histogram correlation.
    Faster but less accurate than ORB.
    """
    cv2, np = load_opencv()
    if cv2 is None:
        return {"similarityScore": 0, "passed": False, "error": "OpenCV not installed"}

    img1 = cv2.imread(img1_path)
    img2 = cv2.imread(img2_path)

    if img1 is None or img2 is None:
        return {"similarityScore": 0, "passed": False, "error": "Could not load images"}

    # Calculate histograms for each channel
    scores = []
    for ch in range(3):
        h1 = cv2.calcHist([img1], [ch], None, [256], [0, 256])
        h2 = cv2.calcHist([img2], [ch], None, [256], [0, 256])
        cv2.normalize(h1, h1)
        cv2.normalize(h2, h2)
        score = cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL)
        scores.append(score)

    avg_score = round(sum(scores) / len(scores) * 100)
    avg_score = max(0, min(100, avg_score))

    return {
        "method":          "Color Histogram Correlation",
        "similarityScore": avg_score,
        "passed":          avg_score >= 60,
        "threshold":       60
    }


# ── Compare Uploaded Images ────────────────────────────────────────────────────
@image_bp.route("/compare", methods=["POST"])
@jwt_required()
def compare_uploaded():
    """Compare two uploaded images directly."""
    if "image1" not in request.files or "image2" not in request.files:
        return jsonify({"error": "Both image1 and image2 are required"}), 400

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    # Save temp files
    f1 = request.files["image1"]
    f2 = request.files["image2"]

    if not f1.filename or not f2.filename:
        return jsonify({"error": "Invalid file names"}), 400

    tmp1 = os.path.join(upload_folder, f"tmp_{uuid.uuid4().hex}.jpg")
    tmp2 = os.path.join(upload_folder, f"tmp_{uuid.uuid4().hex}.jpg")

    try:
        f1.save(tmp1)
        f2.save(tmp2)
        result = compare_images_orb(tmp1, tmp2)
    finally:
        for path in [tmp1, tmp2]:
            try:
                os.remove(path)
            except OSError:
                pass

    return jsonify(result)


# ── Compare by Item IDs ────────────────────────────────────────────────────────
@image_bp.route("/compare-items", methods=["POST"])
@jwt_required()
def compare_item_images():
    """
    Compare images of two items stored in the database.
    Body: { "lostItemId": "...", "foundItemId": "..." }
    """
    from database import get_collection
    from bson import ObjectId

    data          = request.get_json()
    lost_item_id  = data.get("lostItemId")
    found_item_id = data.get("foundItemId")

    if not lost_item_id or not found_item_id:
        return jsonify({"error": "Both lostItemId and foundItemId are required"}), 400

    try:
        lost_item  = get_collection("items").find_one({"_id": ObjectId(lost_item_id)})
        found_item = get_collection("items").find_one({"_id": ObjectId(found_item_id)})
    except Exception:
        return jsonify({"error": "Invalid item IDs"}), 400

    if not lost_item or not found_item:
        return jsonify({"error": "One or both items not found"}), 404

    upload_folder = current_app.config["UPLOAD_FOLDER"]

    # If either item has no image, return simulated result
    if not lost_item.get("imagePath") or not found_item.get("imagePath"):
        import random
        score = random.randint(55, 90)
        return jsonify({
            "method":          "simulated",
            "similarityScore": score,
            "passed":          score >= 60,
            "note":            "One or both items have no image - using simulated comparison"
        })

    img1_path = os.path.join(upload_folder, lost_item["imagePath"])
    img2_path = os.path.join(upload_folder, found_item["imagePath"])

    result = compare_images_orb(img1_path, img2_path)
    return jsonify(result)
