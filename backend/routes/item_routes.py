"""
Item Routes
POST /api/items/lost       - Report lost item
POST /api/items/found      - Report found item
GET  /api/items            - Get all items (with filters)
GET  /api/items/:id        - Get single item
PUT  /api/items/:id        - Update item
DELETE /api/items/:id      - Delete item (owner or admin)
GET  /api/items/my         - Get current user's items
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from datetime import datetime
import os
import uuid

from database import get_collection, serialize_doc, serialize_list

item_bp = Blueprint("items", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

TECH_TYPES   = ["Phone", "Laptop", "Earbuds", "Tablet", "Smartwatch", "Charger", "Power Bank", "Headphones", "Camera", "USB Drive"]
NORMAL_TYPES = ["Bottle", "Bag", "Notebook", "Wallet", "Keys", "Glasses", "Umbrella", "ID Card", "Books", "Clothing", "Jewellery"]


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file) -> str | None:
    """Save uploaded image and return relative path."""
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        return None
    ext      = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    file.save(os.path.join(upload_folder, filename))
    return filename


def validate_item_data(data: dict) -> list[str]:
    """Return list of validation errors."""
    errors = []
    if not data.get("name", "").strip():
        errors.append("Item name is required")
    if data.get("categoryType") not in ["Tech", "Normal"]:
        errors.append("Category type must be 'Tech' or 'Normal'")
    if not data.get("color", "").strip():
        errors.append("Color is required")
    if not data.get("location", "").strip():
        errors.append("Location is required")
    return errors


# ── Report Lost Item ───────────────────────────────────────────────────────────
@item_bp.route("/lost", methods=["POST"])
@jwt_required()
def report_lost():
    user_id = get_jwt_identity()
    data    = request.form.to_dict() if request.content_type and "multipart" in request.content_type else request.get_json() or {}

    errors = validate_item_data(data)
    if errors:
        return jsonify({"error": errors[0], "all_errors": errors}), 400

    image_path = None
    if "image" in request.files:
        image_path = save_image(request.files["image"])

    item = {
        "name":         data["name"].strip(),
        "categoryType": data["categoryType"],
        "categoryName": data.get("categoryName", "").strip(),
        "color":        data["color"].strip(),
        "brand":        data.get("brand", "").strip(),
        "features":     data.get("features", "").strip(),
        "location":     data["location"].strip(),
        "date":         data.get("date", datetime.utcnow().strftime("%Y-%m-%d")),
        "description":  data.get("description", "").strip(),
        "imagePath":    image_path,
        "reporterId":   user_id,
        "status":       "lost",
        "createdAt":    datetime.utcnow().isoformat(),
        "updatedAt":    datetime.utcnow().isoformat()
    }

    result = get_collection("items").insert_one(item)
    item["id"] = str(result.inserted_id)

    return jsonify({"message": "Lost item reported successfully", "item": serialize_doc(item)}), 201


# ── Report Found Item ──────────────────────────────────────────────────────────
@item_bp.route("/found", methods=["POST"])
@jwt_required()
def report_found():
    user_id = get_jwt_identity()
    data    = request.form.to_dict() if request.content_type and "multipart" in request.content_type else request.get_json() or {}

    errors = validate_item_data(data)
    if errors:
        return jsonify({"error": errors[0], "all_errors": errors}), 400

    image_path = None
    if "image" in request.files:
        image_path = save_image(request.files["image"])
        if not image_path:
            return jsonify({"error": "Invalid image file. Allowed: png, jpg, jpeg, gif, webp"}), 400

    item = {
        "name":         data["name"].strip(),
        "categoryType": data["categoryType"],
        "categoryName": data.get("categoryName", "").strip(),
        "color":        data["color"].strip(),
        "brand":        data.get("brand", "").strip(),
        "features":     data.get("features", "").strip(),
        "location":     data["location"].strip(),
        "date":         data.get("date", datetime.utcnow().strftime("%Y-%m-%d")),
        "description":  data.get("description", "").strip(),
        "imagePath":    image_path,
        "reporterId":   user_id,
        "status":       "found",
        "createdAt":    datetime.utcnow().isoformat(),
        "updatedAt":    datetime.utcnow().isoformat()
    }

    result = get_collection("items").insert_one(item)
    item["id"] = str(result.inserted_id)

    return jsonify({"message": "Found item reported successfully", "item": serialize_doc(item)}), 201


# ── Get All Items (with filters) ───────────────────────────────────────────────
@item_bp.route("", methods=["GET"])
def get_items():
    query  = {}
    status = request.args.get("status")
    cat    = request.args.get("category")
    search = request.args.get("search", "").strip()
    page   = max(1, int(request.args.get("page", 1)))
    limit  = min(50, int(request.args.get("limit", 20)))

    if status in ["lost", "found", "claimed"]:
        query["status"] = status
    if cat in ["Tech", "Normal"]:
        query["categoryType"] = cat
    if search:
        query["$text"] = {"$search": search}

    items_col = get_collection("items")
    total     = items_col.count_documents(query)
    items     = list(items_col.find(query).sort("createdAt", -1).skip((page - 1) * limit).limit(limit))

    return jsonify({
        "items":      serialize_list(items),
        "total":      total,
        "page":       page,
        "totalPages": (total + limit - 1) // limit
    })


# ── Get Single Item ────────────────────────────────────────────────────────────
@item_bp.route("/<item_id>", methods=["GET"])
def get_item(item_id):
    try:
        item = get_collection("items").find_one({"_id": ObjectId(item_id)})
    except Exception:
        return jsonify({"error": "Invalid item ID"}), 400

    if not item:
        return jsonify({"error": "Item not found"}), 404

    # Attach reporter info (name, studentId only)
    reporter = get_collection("users").find_one({"_id": ObjectId(item["reporterId"])})
    result   = serialize_doc(item)
    if reporter:
        result["reporter"] = {
            "name":      reporter["name"],
            "studentId": reporter["studentId"]
        }

    return jsonify(result)


# ── Get My Items ───────────────────────────────────────────────────────────────
@item_bp.route("/my", methods=["GET"])
@jwt_required()
def my_items():
    user_id = get_jwt_identity()
    items   = list(get_collection("items").find({"reporterId": user_id}).sort("createdAt", -1))
    return jsonify({"items": serialize_list(items)})


# ── Update Item ────────────────────────────────────────────────────────────────
@item_bp.route("/<item_id>", methods=["PUT"])
@jwt_required()
def update_item(item_id):
    user_id = get_jwt_identity()
    claims  = get_jwt()

    try:
        item = get_collection("items").find_one({"_id": ObjectId(item_id)})
    except Exception:
        return jsonify({"error": "Invalid item ID"}), 400

    if not item:
        return jsonify({"error": "Item not found"}), 404

    if item["reporterId"] != user_id and claims.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    allowed_fields = ["name", "color", "brand", "features", "location", "description", "date"]
    update = {k: data[k] for k in allowed_fields if k in data}
    update["updatedAt"] = datetime.utcnow().isoformat()

    get_collection("items").update_one({"_id": ObjectId(item_id)}, {"$set": update})
    return jsonify({"message": "Item updated successfully"})


# ── Delete Item ────────────────────────────────────────────────────────────────
@item_bp.route("/<item_id>", methods=["DELETE"])
@jwt_required()
def delete_item(item_id):
    user_id = get_jwt_identity()
    claims  = get_jwt()

    try:
        item = get_collection("items").find_one({"_id": ObjectId(item_id)})
    except Exception:
        return jsonify({"error": "Invalid item ID"}), 400

    if not item:
        return jsonify({"error": "Item not found"}), 404

    if item["reporterId"] != user_id and claims.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    get_collection("items").delete_one({"_id": ObjectId(item_id)})

    # Also delete related claims
    get_collection("claims").delete_many({"itemId": item_id})

    # Delete image file
    if item.get("imagePath"):
        try:
            os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], item["imagePath"]))
        except OSError:
            pass

    return jsonify({"message": "Item deleted successfully"})


# ── Get Item Types ─────────────────────────────────────────────────────────────
@item_bp.route("/types/<category>", methods=["GET"])
def get_item_types(category):
    types = TECH_TYPES if category == "Tech" else NORMAL_TYPES if category == "Normal" else []
    return jsonify({"types": types})
