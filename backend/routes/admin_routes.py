"""
Admin Routes
GET  /api/admin/stats      - System statistics
GET  /api/admin/users      - All users
PUT  /api/admin/users/:id  - Update user (activate/deactivate, change role)
DELETE /api/admin/users/:id - Delete user
GET  /api/admin/items      - All items with filters
GET  /api/admin/claims     - All claims
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from bson import ObjectId
from datetime import datetime

from database import get_collection, serialize_doc, serialize_list

admin_bp = Blueprint("admin", __name__)


def require_admin():
    """Check if current user is admin."""
    jwt_data = get_jwt()
    if jwt_data.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    return None


# ── Dashboard Stats ────────────────────────────────────────────────────────────
@admin_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_stats():
    err = require_admin()
    if err:
        return err

    items  = get_collection("items")
    claims = get_collection("claims")
    users  = get_collection("users")

    total_items  = items.count_documents({})
    lost_items   = items.count_documents({"status": "lost"})
    found_items  = items.count_documents({"status": "found"})
    claimed_items = items.count_documents({"status": "claimed"})

    total_claims   = claims.count_documents({})
    pending_claims = claims.count_documents({"status": "pending"})
    approved       = claims.count_documents({"status": "approved"})
    rejected       = claims.count_documents({"status": "rejected"})

    total_users = users.count_documents({"role": "user"})

    # Average quiz score
    pipeline = [
        {"$group": {"_id": None, "avgQuiz": {"$avg": "$quizScore"}, "avgImage": {"$avg": "$imageMatchScore"}}}
    ]
    agg = list(claims.aggregate(pipeline))
    avg_quiz  = round(agg[0]["avgQuiz"], 1)  if agg else 0
    avg_image = round(agg[0]["avgImage"], 1) if agg else 0

    # Items by category
    tech_count   = items.count_documents({"categoryType": "Tech"})
    normal_count = items.count_documents({"categoryType": "Normal"})

    return jsonify({
        "items": {
            "total":   total_items,
            "lost":    lost_items,
            "found":   found_items,
            "claimed": claimed_items
        },
        "claims": {
            "total":    total_claims,
            "pending":  pending_claims,
            "approved": approved,
            "rejected": rejected
        },
        "users": {
            "total": total_users
        },
        "averages": {
            "quizScore":        avg_quiz,
            "imageMatchScore":  avg_image
        },
        "categories": {
            "tech":   tech_count,
            "normal": normal_count
        }
    })


# ── Get All Users ──────────────────────────────────────────────────────────────
@admin_bp.route("/users", methods=["GET"])
@jwt_required()
def get_users():
    err = require_admin()
    if err:
        return err

    users = list(get_collection("users").find({"role": {"$ne": "admin"}}).sort("createdAt", -1))
    result = []
    items_col = get_collection("items")
    claims_col = get_collection("claims")

    for u in users:
        user_doc = serialize_doc(u)
        user_doc.pop("password", None)
        uid = str(u["_id"])
        user_doc["reportCount"] = items_col.count_documents({"reporterId": uid})
        user_doc["claimCount"]  = claims_col.count_documents({"claimantId": uid})
        result.append(user_doc)

    return jsonify({"users": result, "total": len(result)})


# ── Update User ────────────────────────────────────────────────────────────────
@admin_bp.route("/users/<user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id):
    err = require_admin()
    if err:
        return err

    data = request.get_json()
    allowed = {}
    if "isActive" in data:
        allowed["isActive"] = bool(data["isActive"])
    if "role" in data and data["role"] in ["user", "admin"]:
        allowed["role"] = data["role"]

    if not allowed:
        return jsonify({"error": "No valid fields to update"}), 400

    allowed["updatedAt"] = datetime.utcnow().isoformat()

    try:
        result = get_collection("users").update_one({"_id": ObjectId(user_id)}, {"$set": allowed})
    except Exception:
        return jsonify({"error": "Invalid user ID"}), 400

    if result.matched_count == 0:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"message": "User updated successfully"})


# ── Delete User ────────────────────────────────────────────────────────────────
@admin_bp.route("/users/<user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    err = require_admin()
    if err:
        return err

    try:
        result = get_collection("users").delete_one({"_id": ObjectId(user_id)})
    except Exception:
        return jsonify({"error": "Invalid user ID"}), 400

    if result.deleted_count == 0:
        return jsonify({"error": "User not found"}), 404

    # Cascade: remove items and claims
    get_collection("items").delete_many({"reporterId": user_id})
    get_collection("claims").delete_many({"claimantId": user_id})

    return jsonify({"message": "User and all their data deleted"})


# ── Get All Items (Admin view) ─────────────────────────────────────────────────
@admin_bp.route("/items", methods=["GET"])
@jwt_required()
def admin_items():
    err = require_admin()
    if err:
        return err

    query  = {}
    status = request.args.get("status")
    cat    = request.args.get("category")

    if status:
        query["status"] = status
    if cat:
        query["categoryType"] = cat

    items = list(get_collection("items").find(query).sort("createdAt", -1))
    result = []
    for item in items:
        doc = serialize_doc(item)
        reporter = get_collection("users").find_one({"_id": ObjectId(item["reporterId"])}) if item.get("reporterId") else None
        if reporter:
            doc["reporter"] = {"name": reporter["name"], "studentId": reporter["studentId"]}
        result.append(doc)

    return jsonify({"items": result, "total": len(result)})


# ── Get All Claims (Admin view) ────────────────────────────────────────────────
@admin_bp.route("/claims", methods=["GET"])
@jwt_required()
def admin_claims():
    err = require_admin()
    if err:
        return err

    status = request.args.get("status")
    query  = {}
    if status:
        query["status"] = status

    claims = list(get_collection("claims").find(query).sort("createdAt", -1))
    result = []
    for claim in claims:
        doc = serialize_doc(claim)
        try:
            item = get_collection("items").find_one({"_id": ObjectId(doc["itemId"])})
            doc["item"] = serialize_doc(item) if item else None
        except Exception:
            doc["item"] = None
        try:
            user = get_collection("users").find_one({"_id": ObjectId(doc["claimantId"])})
            if user:
                doc["claimant"] = {"name": user["name"], "studentId": user["studentId"], "email": user["email"]}
        except Exception:
            doc["claimant"] = None
        result.append(doc)

    return jsonify({"claims": result, "total": len(result)})
