"""
Claim Routes
POST /api/claims              - Submit a claim
GET  /api/claims              - Get all claims (admin) or own claims (user)
GET  /api/claims/:id          - Get claim detail
PUT  /api/claims/:id          - Update claim status (admin only)
DELETE /api/claims/:id        - Cancel a pending claim (claimant only)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from datetime import datetime

from database import get_collection, serialize_doc, serialize_list

claim_bp = Blueprint("claims", __name__)


# ── Submit Claim ───────────────────────────────────────────────────────────────
@claim_bp.route("", methods=["POST"])
@jwt_required()
def submit_claim():
    user_id = get_jwt_identity()
    data    = request.get_json()

    item_id          = data.get("itemId")
    quiz_score       = data.get("quizScore", 0)
    image_match      = data.get("imageMatchScore", 0)
    quiz_passed      = data.get("quizPassed", False)
    image_passed     = data.get("imagePassed", False)

    if not item_id:
        return jsonify({"error": "itemId is required"}), 400

    # Validate item
    try:
        item = get_collection("items").find_one({"_id": ObjectId(item_id)})
    except Exception:
        return jsonify({"error": "Invalid item ID"}), 400

    if not item:
        return jsonify({"error": "Item not found"}), 404

    if item["status"] != "found":
        return jsonify({"error": "Can only claim items with 'found' status"}), 400

    if item["reporterId"] == user_id:
        return jsonify({"error": "Cannot claim your own reported item"}), 403

    # Check for existing claim
    existing = get_collection("claims").find_one({"itemId": item_id, "claimantId": user_id})
    if existing:
        return jsonify({"error": "You have already submitted a claim for this item"}), 409

    # Determine auto-status
    both_passed = quiz_passed and image_passed
    auto_status = "pending" if both_passed else "rejected"

    claim = {
        "itemId":          item_id,
        "claimantId":      user_id,
        "quizScore":       quiz_score,
        "imageMatchScore": image_match,
        "quizPassed":      quiz_passed,
        "imagePassed":     image_passed,
        "status":          auto_status,
        "adminNote":       None,
        "createdAt":       datetime.utcnow().isoformat(),
        "updatedAt":       datetime.utcnow().isoformat()
    }

    result = get_collection("claims").insert_one(claim)

    return jsonify({
        "message": "Claim submitted successfully" if both_passed else "Claim rejected - verification failed",
        "claimId": str(result.inserted_id),
        "status":  auto_status,
        "passed":  both_passed
    }), 201


# ── Get Claims ─────────────────────────────────────────────────────────────────
@claim_bp.route("", methods=["GET"])
@jwt_required()
def get_claims():
    user_id = get_jwt_identity()
    jwt_data = get_jwt()
    role    = jwt_data.get("role", "user")

    if role == "admin":
        # Admin sees all claims with item + user details
        claims = list(get_collection("claims").find().sort("createdAt", -1))
    else:
        claims = list(get_collection("claims").find({"claimantId": user_id}).sort("createdAt", -1))

    # Enrich with item and user info
    enriched = []
    for claim in claims:
        c = serialize_doc(claim)
        # Attach item info
        try:
            item = get_collection("items").find_one({"_id": ObjectId(c["itemId"])})
            if item:
                c["item"] = {"name": item["name"], "categoryType": item["categoryType"], "status": item["status"]}
        except Exception:
            pass
        # Attach claimant info (admin only)
        if role == "admin":
            try:
                user = get_collection("users").find_one({"_id": ObjectId(c["claimantId"])})
                if user:
                    c["claimant"] = {"name": user["name"], "studentId": user["studentId"], "email": user["email"]}
            except Exception:
                pass
        enriched.append(c)

    return jsonify({"claims": enriched, "total": len(enriched)})


# ── Get Single Claim ───────────────────────────────────────────────────────────
@claim_bp.route("/<claim_id>", methods=["GET"])
@jwt_required()
def get_claim(claim_id):
    user_id  = get_jwt_identity()
    jwt_data = get_jwt()

    try:
        claim = get_collection("claims").find_one({"_id": ObjectId(claim_id)})
    except Exception:
        return jsonify({"error": "Invalid claim ID"}), 400

    if not claim:
        return jsonify({"error": "Claim not found"}), 404

    if claim["claimantId"] != user_id and jwt_data.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify(serialize_doc(claim))


# ── Update Claim Status (Admin) ────────────────────────────────────────────────
@claim_bp.route("/<claim_id>", methods=["PUT"])
@jwt_required()
def update_claim(claim_id):
    jwt_data = get_jwt()
    if jwt_data.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403

    data   = request.get_json()
    status = data.get("status")

    if status not in ["approved", "rejected", "pending"]:
        return jsonify({"error": "Status must be 'approved', 'rejected', or 'pending'"}), 400

    try:
        claim = get_collection("claims").find_one({"_id": ObjectId(claim_id)})
    except Exception:
        return jsonify({"error": "Invalid claim ID"}), 400

    if not claim:
        return jsonify({"error": "Claim not found"}), 404

    update = {
        "status":    status,
        "adminNote": data.get("note", ""),
        "updatedAt": datetime.utcnow().isoformat(),
        "reviewedBy": get_jwt_identity()
    }
    get_collection("claims").update_one({"_id": ObjectId(claim_id)}, {"$set": update})

    prev_status = claim.get("status", "")

    # If approved, update item status to "claimed" and reject all other claims
    if status == "approved":
        get_collection("items").update_one(
            {"_id": ObjectId(claim["itemId"])},
            {"$set": {"status": "claimed", "updatedAt": datetime.utcnow().isoformat()}}
        )
        # Reject all other claims for the same item
        get_collection("claims").update_many(
            {"itemId": claim["itemId"], "_id": {"$ne": ObjectId(claim_id)}},
            {"$set": {"status": "rejected", "adminNote": "Another claim was approved for this item"}}
        )

    # If moving away from approved (e.g. admin reverses an approval), revert item to "found"
    elif prev_status == "approved" and status in ["rejected", "pending"]:
        get_collection("items").update_one(
            {"_id": ObjectId(claim["itemId"])},
            {"$set": {"status": "found", "updatedAt": datetime.utcnow().isoformat()}}
        )

    return jsonify({"message": f"Claim {status} successfully"})


# ── Cancel Claim ───────────────────────────────────────────────────────────────
@claim_bp.route("/<claim_id>", methods=["DELETE"])
@jwt_required()
def cancel_claim(claim_id):
    user_id = get_jwt_identity()

    try:
        claim = get_collection("claims").find_one({"_id": ObjectId(claim_id)})
    except Exception:
        return jsonify({"error": "Invalid claim ID"}), 400

    if not claim:
        return jsonify({"error": "Claim not found"}), 404

    if claim["claimantId"] != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    if claim["status"] != "pending":
        return jsonify({"error": "Only pending claims can be cancelled"}), 400

    get_collection("claims").delete_one({"_id": ObjectId(claim_id)})
    return jsonify({"message": "Claim cancelled successfully"})
