"""
ObjectTracker - Campus Lost & Found System
Main Flask Application Entry Point
"""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

from routes.auth_routes import auth_bp
from routes.item_routes import item_bp
from routes.claim_routes import claim_bp
from routes.quiz_routes import quiz_bp
from routes.image_routes import image_bp
from routes.admin_routes import admin_bp

load_dotenv()

app = Flask(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "object-tracker-secret-key-change-in-prod")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-secret-change-in-prod")
app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/object_tracker")
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "..", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ── Extensions ─────────────────────────────────────────────────────────────────
CORS(app, resources={r"/api/*": {"origins": "*"}})
jwt = JWTManager(app)

# ── Blueprints ─────────────────────────────────────────────────────────────────
app.register_blueprint(auth_bp,   url_prefix="/api/auth")
app.register_blueprint(item_bp,   url_prefix="/api/items")
app.register_blueprint(claim_bp,  url_prefix="/api/claims")
app.register_blueprint(quiz_bp,   url_prefix="/api/quiz")
app.register_blueprint(image_bp,  url_prefix="/api/image")
app.register_blueprint(admin_bp,  url_prefix="/api/admin")

# ── Health check ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return jsonify({
        "app": "ObjectTracker",
        "version": "1.0.0",
        "status": "running",
        "description": "Campus Lost & Found System"
    })

@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "message": "ObjectTracker API is live"})

# ── JWT Error Handlers ─────────────────────────────────────────────────────────
@jwt.unauthorized_loader
def missing_token(reason):
    return jsonify({"error": "Authorization token missing", "reason": reason}), 401

@jwt.invalid_token_loader
def invalid_token(reason):
    return jsonify({"error": "Invalid token", "reason": reason}), 422

@jwt.expired_token_loader
def expired_token(jwt_header, jwt_data):
    return jsonify({"error": "Token has expired"}), 401

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
