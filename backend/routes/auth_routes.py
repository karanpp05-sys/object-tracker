"""
Authentication Routes
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from bson import ObjectId
import re

from database import get_collection, serialize_doc

auth_bp = Blueprint("auth", __name__)


def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email))


# ── Register ───────────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    # Validation
    required = ["name", "email", "password", "studentId"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400

    name      = data["name"].strip()
    email     = data["email"].strip().lower()
    password  = data["password"]
    student_id = data["studentId"].strip().upper()

    if not is_valid_email(email):
        return jsonify({"error": "Invalid email address"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    users = get_collection("users")

    # Check duplicates
    if users.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 409

    if users.find_one({"studentId": student_id}):
        return jsonify({"error": "Student ID already registered"}), 409

    # Create user
    user = {
        "name": name,
        "email": email,
        "password": generate_password_hash(password),
        "studentId": student_id,
        "role": "user",
        "createdAt": datetime.utcnow().isoformat(),
        "isActive": True
    }
    result = users.insert_one(user)
    user_id = str(result.inserted_id)

    token = create_access_token(
        identity=user_id,
        additional_claims={"role": "user", "name": name},
        expires_delta=timedelta(days=7)
    )

    return jsonify({
        "message": "Account created successfully",
        "token": token,
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
            "studentId": student_id,
            "role": "user"
        }
    }), 201


# ── Login ──────────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    users = get_collection("users")
    user  = users.find_one({"email": email})

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    if not user.get("isActive", True):
        return jsonify({"error": "Account is deactivated. Contact admin."}), 403

    user_id = str(user["_id"])
    token = create_access_token(
        identity=user_id,
        additional_claims={"role": user["role"], "name": user["name"]},
        expires_delta=timedelta(days=7)
    )

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {
            "id": user_id,
            "name": user["name"],
            "email": user["email"],
            "studentId": user["studentId"],
            "role": user["role"]
        }
    })


# ── Get current user profile ───────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    users   = get_collection("users")
    user    = users.find_one({"_id": ObjectId(user_id)})

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "studentId": user["studentId"],
        "role": user["role"],
        "createdAt": user.get("createdAt")
    })


# ── Change password ────────────────────────────────────────────────────────────
@auth_bp.route("/change-password", methods=["PUT"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data    = request.get_json()

    current  = data.get("currentPassword", "")
    new_pass = data.get("newPassword", "")

    if not current or not new_pass:
        return jsonify({"error": "Both current and new password are required"}), 400

    if len(new_pass) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    users = get_collection("users")
    user  = users.find_one({"_id": ObjectId(user_id)})

    if not check_password_hash(user["password"], current):
        return jsonify({"error": "Current password is incorrect"}), 401

    users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password": generate_password_hash(new_pass)}}
    )

    return jsonify({"message": "Password updated successfully"})
