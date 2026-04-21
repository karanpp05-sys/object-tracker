"""
Quiz Routes
POST /api/quiz/generate   - Generate quiz questions for an item
POST /api/quiz/validate   - Validate quiz answers and return score
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
import random

from database import get_collection, serialize_doc

quiz_bp = Blueprint("quiz", __name__)

# ── Question Bank ──────────────────────────────────────────────────────────────

TECH_COLOR_DISTRACTORS   = ["Space White", "Rose Gold", "Midnight Green", "Pacific Blue", "Starlight", "Product Red", "Alpine Green"]
TECH_BRAND_DISTRACTORS   = ["Samsung", "Apple", "Sony", "HP", "Dell", "OnePlus", "Xiaomi", "Lenovo", "Asus", "LG"]
NORMAL_COLOR_DISTRACTORS = ["Scarlet Red", "Forest Green", "Cobalt Blue", "Jet Black", "Cream White", "Burnt Orange", "Lavender"]
LOCATION_DISTRACTORS     = ["Main Cafeteria", "Library Ground Floor", "Sports Complex", "Admin Block", "Parking Lot A", "Computer Lab", "Chemistry Block", "Hostel Common Room", "Basketball Court", "Reading Room"]
FEATURE_DISTRACTORS      = ["No distinctive marks", "Scratched surface", "Name tag attached", "Blue case/cover", "Red stickers", "Rubber band around it", "Initials engraved", "Keychain attached"]


def pick_distractors(correct: str, pool: list, count: int = 3) -> list:
    """Pick `count` unique distractors not matching `correct`."""
    filtered = [p for p in pool if p.lower().strip() != correct.lower().strip()]
    random.shuffle(filtered)
    return filtered[:count]


def make_options(correct: str, distractors: list) -> list:
    """Combine correct + distractors and shuffle."""
    options = [correct] + distractors[:3]
    random.shuffle(options)
    return options


def generate_tech_questions(item: dict) -> list:
    """Generate 5 quiz questions for Tech category items."""
    questions = []

    # Q1 – Color
    color = item.get("color", "Unknown")
    questions.append({
        "question": f"What is the color of the {item['name']}?",
        "options":  make_options(color, pick_distractors(color, TECH_COLOR_DISTRACTORS)),
        "correct":  color,
        "field":    "color"
    })

    # Q2 – Brand
    brand = item.get("brand") or "No Brand"
    questions.append({
        "question": f"What is the brand of the {item['name']}?",
        "options":  make_options(brand, pick_distractors(brand, TECH_BRAND_DISTRACTORS)),
        "correct":  brand,
        "field":    "brand"
    })

    # Q3 – Location
    location = item.get("location", "Unknown location")
    questions.append({
        "question": f"Where was the {item['name']} lost/found?",
        "options":  make_options(location, pick_distractors(location, LOCATION_DISTRACTORS)),
        "correct":  location,
        "field":    "location"
    })

    # Q4 – Category / Type
    cat_name = item.get("categoryName", "Device")
    cat_distractors = ["Laptop", "Phone", "Tablet", "Earbuds", "Charger", "Smartwatch", "Power Bank"]
    questions.append({
        "question": f"What type of tech device is the {item['name']}?",
        "options":  make_options(cat_name, pick_distractors(cat_name, cat_distractors)),
        "correct":  cat_name,
        "field":    "categoryName"
    })

    # Q5 – Unique Feature
    features = item.get("features", "").strip()
    first_feature = features.split(",")[0].strip() if features else "No distinctive features"
    questions.append({
        "question": f"What is a unique identifying feature of the {item['name']}?",
        "options":  make_options(first_feature, pick_distractors(first_feature, FEATURE_DISTRACTORS)),
        "correct":  first_feature,
        "field":    "features"
    })

    return questions


def generate_normal_questions(item: dict) -> list:
    """Generate 5 quiz questions for Normal category items."""
    questions = []

    # Q1 – Color
    color = item.get("color", "Unknown")
    questions.append({
        "question": f"What color is the {item['name']}?",
        "options":  make_options(color, pick_distractors(color, NORMAL_COLOR_DISTRACTORS)),
        "correct":  color,
        "field":    "color"
    })

    # Q2 – Location
    location = item.get("location", "Unknown location")
    questions.append({
        "question": f"Where was the {item['name']} lost/found?",
        "options":  make_options(location, pick_distractors(location, LOCATION_DISTRACTORS)),
        "correct":  location,
        "field":    "location"
    })

    # Q3 – Brand/Label
    brand = item.get("brand") or "No Brand/Label"
    normal_brands = ["Milton", "Wildcraft", "Skybags", "American Tourister", "No Brand/Label", "Puma", "Adidas", "Nike", "VIP", "Safari"]
    questions.append({
        "question": f"What is the brand or label on the {item['name']}?",
        "options":  make_options(brand, pick_distractors(brand, normal_brands)),
        "correct":  brand,
        "field":    "brand"
    })

    # Q4 – Item Type
    cat_name = item.get("categoryName", "Item")
    normal_types = ["Bottle", "Bag", "Keys", "Wallet", "Notebook", "Glasses", "Umbrella", "ID Card", "Books"]
    questions.append({
        "question": f"What category of item is it?",
        "options":  make_options(cat_name, pick_distractors(cat_name, normal_types)),
        "correct":  cat_name,
        "field":    "categoryName"
    })

    # Q5 – Distinguishing feature
    features = item.get("features", "").strip()
    first_feature = features.split(",")[0].strip() if features else "No distinctive marks"
    questions.append({
        "question": f"What distinguishing mark or feature does the {item['name']} have?",
        "options":  make_options(first_feature, pick_distractors(first_feature, FEATURE_DISTRACTORS)),
        "correct":  first_feature,
        "field":    "features"
    })

    return questions


# ── Generate Quiz ──────────────────────────────────────────────────────────────
@quiz_bp.route("/generate", methods=["POST"])
@jwt_required()
def generate_quiz():
    data    = request.get_json()
    item_id = data.get("itemId")

    if not item_id:
        return jsonify({"error": "itemId is required"}), 400

    try:
        item = get_collection("items").find_one({"_id": ObjectId(item_id)})
    except Exception:
        return jsonify({"error": "Invalid item ID"}), 400

    if not item:
        return jsonify({"error": "Item not found"}), 404

    if item["status"] != "found":
        return jsonify({"error": "Can only claim items with 'found' status"}), 400

    # Check user is not the reporter
    user_id = get_jwt_identity()
    if item["reporterId"] == user_id:
        return jsonify({"error": "You cannot claim your own reported item"}), 403

    # Generate questions based on category
    if item["categoryType"] == "Tech":
        all_questions = generate_tech_questions(item)
    else:
        all_questions = generate_normal_questions(item)

    # Pick 4 questions
    selected = random.sample(all_questions, min(4, len(all_questions)))

    # Return WITHOUT the correct answers exposed (only needed on validation)
    quiz_for_client = []
    for i, q in enumerate(selected):
        quiz_for_client.append({
            "id":       i,
            "question": q["question"],
            "options":  q["options"],
            # correct is NOT sent to frontend
        })

    # Store correct answers in session-like structure (in production use Redis or signed JWT)
    # For now, we store in a temp quizzes collection with TTL
    quiz_session = {
        "itemId":    item_id,
        "userId":    user_id,
        "questions": selected,
        "createdAt": __import__("datetime").datetime.utcnow().isoformat()
    }
    sessions = get_collection("quiz_sessions")
    sessions.delete_many({"itemId": item_id, "userId": user_id})  # clear old
    result = sessions.insert_one(quiz_session)

    return jsonify({
        "sessionId": str(result.inserted_id),
        "questions": quiz_for_client,
        "itemName":  item["name"],
        "totalQuestions": len(quiz_for_client),
        "passMark": 60
    })


# ── Validate Quiz ──────────────────────────────────────────────────────────────
@quiz_bp.route("/validate", methods=["POST"])
@jwt_required()
def validate_quiz():
    data       = request.get_json()
    session_id = data.get("sessionId")
    answers    = data.get("answers", {})  # { "0": "answer", "1": "answer", ... }

    if not session_id:
        return jsonify({"error": "sessionId is required"}), 400

    try:
        session = get_collection("quiz_sessions").find_one({"_id": ObjectId(session_id)})
    except Exception:
        return jsonify({"error": "Invalid session ID"}), 400

    if not session:
        return jsonify({"error": "Quiz session not found or expired"}), 404

    user_id = get_jwt_identity()
    if session["userId"] != user_id:
        return jsonify({"error": "Unauthorized quiz session"}), 403

    questions = session["questions"]
    correct_count = 0
    detailed = []

    for i, q in enumerate(questions):
        user_ans    = str(answers.get(str(i), "")).strip().lower()
        correct_ans = q["correct"].strip().lower()
        is_correct  = user_ans == correct_ans
        if is_correct:
            correct_count += 1
        detailed.append({
            "question":     q["question"],
            "yourAnswer":   answers.get(str(i), "Not answered"),
            "correctAnswer": q["correct"],
            "isCorrect":    is_correct
        })

    score = round((correct_count / len(questions)) * 100)
    passed = score >= 60

    # Clean up session
    get_collection("quiz_sessions").delete_one({"_id": ObjectId(session_id)})

    return jsonify({
        "score":       score,
        "passed":      passed,
        "correct":     correct_count,
        "total":       len(questions),
        "detailed":    detailed,
        "passMark":    60,
        "message":     "Quiz passed!" if passed else "Quiz failed. Score below 60%."
    })
