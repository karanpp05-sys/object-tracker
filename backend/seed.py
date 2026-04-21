"""
Seed Script - Populate MongoDB with sample data for development/testing.
Run: python seed.py
"""

from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import os
import random

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/object_tracker")
client    = MongoClient(MONGO_URI)
db        = client["object_tracker"]

print("🌱 Seeding ObjectTracker database...")

# ── Clear existing data ────────────────────────────────────────────────────────
db.users.drop()
db.items.drop()
db.claims.drop()
db.quiz_sessions.drop()
print("✅ Cleared existing collections")

# ── Users ──────────────────────────────────────────────────────────────────────
users_data = [
    {
        "name":      "Admin User",
        "email":     "admin@campus.edu",
        "password":  generate_password_hash("admin123"),
        "studentId": "ADMIN001",
        "role":      "admin",
        "isActive":  True,
        "createdAt": datetime.utcnow().isoformat()
    },
    {
        "name":      "Rahul Kumar",
        "email":     "rahul@college.edu",
        "password":  generate_password_hash("pass123"),
        "studentId": "CS21B1001",
        "role":      "user",
        "isActive":  True,
        "createdAt": datetime.utcnow().isoformat()
    },
    {
        "name":      "Priya Singh",
        "email":     "priya@college.edu",
        "password":  generate_password_hash("pass123"),
        "studentId": "EC21B1042",
        "role":      "user",
        "isActive":  True,
        "createdAt": datetime.utcnow().isoformat()
    },
    {
        "name":      "Arjun Sharma",
        "email":     "arjun@college.edu",
        "password":  generate_password_hash("pass123"),
        "studentId": "ME22B1015",
        "role":      "user",
        "isActive":  True,
        "createdAt": datetime.utcnow().isoformat()
    },
    {
        "name":      "Sneha Patel",
        "email":     "sneha@college.edu",
        "password":  generate_password_hash("pass123"),
        "studentId": "BA21B2031",
        "role":      "user",
        "isActive":  True,
        "createdAt": datetime.utcnow().isoformat()
    }
]

user_ids = db.users.insert_many(users_data).inserted_ids
print(f"✅ Inserted {len(user_ids)} users")

u_admin, u1, u2, u3, u4 = [str(uid) for uid in user_ids]

# ── Items ──────────────────────────────────────────────────────────────────────
base_date = datetime.utcnow()
items_data = [
    {
        "name": "iPhone 14 Pro", "categoryType": "Tech", "categoryName": "Phone",
        "color": "Space Black", "brand": "Apple",
        "features": "Blue silicone case, cracked screen protector",
        "location": "Library 2nd Floor", "date": (base_date - timedelta(days=5)).strftime("%Y-%m-%d"),
        "description": "iPhone 14 Pro with blue silicone case and cracked screen protector. Has a small scratch near the camera.",
        "imagePath": None, "reporterId": u1, "status": "lost",
        "createdAt": (base_date - timedelta(days=5)).isoformat()
    },
    {
        "name": "Navy Blue Backpack", "categoryType": "Normal", "categoryName": "Bag",
        "color": "Navy Blue", "brand": "Wildcraft",
        "features": "Minnie Mouse keychain on zipper, torn right shoulder strap",
        "location": "Canteen Area", "date": (base_date - timedelta(days=3)).strftime("%Y-%m-%d"),
        "description": "Large navy blue Wildcraft backpack with multiple compartments. Has a Minnie Mouse keychain.",
        "imagePath": None, "reporterId": u2, "status": "found",
        "createdAt": (base_date - timedelta(days=3)).isoformat()
    },
    {
        "name": "Sony WH-1000XM5", "categoryType": "Tech", "categoryName": "Headphones",
        "color": "Silver", "brand": "Sony",
        "features": "Sticker on left earcup with GitHub logo, black carrying case",
        "location": "Seminar Hall B", "date": (base_date - timedelta(days=4)).strftime("%Y-%m-%d"),
        "description": "Premium Sony noise-cancelling headphones in carrying case. Has GitHub sticker on left cup.",
        "imagePath": None, "reporterId": u1, "status": "found",
        "createdAt": (base_date - timedelta(days=4)).isoformat()
    },
    {
        "name": "Milton Water Bottle", "categoryType": "Normal", "categoryName": "Bottle",
        "color": "Red", "brand": "Milton",
        "features": "Name 'Arjun S' written with marker on the side",
        "location": "Gymnasium", "date": (base_date - timedelta(days=2)).strftime("%Y-%m-%d"),
        "description": "1-litre red Milton water bottle with straw lid. Has the owner's name written in black marker.",
        "imagePath": None, "reporterId": u3, "status": "lost",
        "createdAt": (base_date - timedelta(days=2)).isoformat()
    },
    {
        "name": "Honda Car Keys", "categoryType": "Normal", "categoryName": "Keys",
        "color": "Silver", "brand": "Honda",
        "features": "3 keys with Minnie Mouse rubber keychain",
        "location": "Parking Lot B", "date": (base_date - timedelta(days=1)).strftime("%Y-%m-%d"),
        "description": "Honda car key bundle with 3 keys attached to a Minnie Mouse rubber keychain.",
        "imagePath": None, "reporterId": u2, "status": "found",
        "createdAt": (base_date - timedelta(days=1)).isoformat()
    },
    {
        "name": "MacBook Air M2", "categoryType": "Tech", "categoryName": "Laptop",
        "color": "Midnight", "brand": "Apple",
        "features": "Python logo sticker and GitHub logo sticker on lid",
        "location": "CS Lab 3", "date": (base_date - timedelta(days=6)).strftime("%Y-%m-%d"),
        "description": "13-inch MacBook Air M2 in Midnight colour. Has Python and GitHub stickers on the lid.",
        "imagePath": None, "reporterId": u1, "status": "lost",
        "createdAt": (base_date - timedelta(days=6)).isoformat()
    },
    {
        "name": "Ray-Ban Sunglasses", "categoryType": "Normal", "categoryName": "Glasses",
        "color": "Black Frame", "brand": "Ray-Ban",
        "features": "Gold RB logo on frame, brown gradient lenses",
        "location": "Sports Ground", "date": base_date.strftime("%Y-%m-%d"),
        "description": "Classic Ray-Ban Wayfarer sunglasses with black frame and brown gradient lenses.",
        "imagePath": None, "reporterId": u4, "status": "found",
        "createdAt": base_date.isoformat()
    },
    {
        "name": "Samsung Galaxy S23", "categoryType": "Tech", "categoryName": "Phone",
        "color": "Phantom Black", "brand": "Samsung",
        "features": "Transparent back case, screen has small crack on corner",
        "location": "Admin Block Corridor", "date": (base_date - timedelta(days=2)).strftime("%Y-%m-%d"),
        "description": "Samsung Galaxy S23 in transparent case with a small crack at the bottom-right corner of the screen.",
        "imagePath": None, "reporterId": u3, "status": "found",
        "createdAt": (base_date - timedelta(days=2)).isoformat()
    },
    {
        "name": "College ID Card", "categoryType": "Normal", "categoryName": "ID Card",
        "color": "Blue and White", "brand": "Campus Issued",
        "features": "Name: Sneha Patel, Roll: BA21B2031",
        "location": "Main Gate Reception", "date": base_date.strftime("%Y-%m-%d"),
        "description": "Student ID card found near the main gate. Name: Sneha Patel, Dept: Business Administration.",
        "imagePath": None, "reporterId": u2, "status": "found",
        "createdAt": base_date.isoformat()
    },
    {
        "name": "Anker PowerCore 20000", "categoryType": "Tech", "categoryName": "Power Bank",
        "color": "Black", "brand": "Anker",
        "features": "White tape on one side with name 'Priya'",
        "location": "Reading Room", "date": (base_date - timedelta(days=3)).strftime("%Y-%m-%d"),
        "description": "Anker PowerCore 20000mAh power bank with white tape on side labelled Priya.",
        "imagePath": None, "reporterId": u4, "status": "lost",
        "createdAt": (base_date - timedelta(days=3)).isoformat()
    }
]

item_ids = db.items.insert_many(items_data).inserted_ids
print(f"✅ Inserted {len(item_ids)} items")

i_backpack, i_headphones, i_keys, i_sunglasses, i_galaxy = str(item_ids[1]), str(item_ids[2]), str(item_ids[4]), str(item_ids[6]), str(item_ids[7])

# ── Claims ─────────────────────────────────────────────────────────────────────
claims_data = [
    {
        "itemId":          i_backpack,
        "claimantId":      u1,
        "quizScore":       80,
        "imageMatchScore": 85,
        "quizPassed":      True,
        "imagePassed":     True,
        "status":          "pending",
        "adminNote":       None,
        "createdAt":       (base_date - timedelta(days=1)).isoformat()
    },
    {
        "itemId":          i_headphones,
        "claimantId":      u2,
        "quizScore":       40,
        "imageMatchScore": 35,
        "quizPassed":      False,
        "imagePassed":     False,
        "status":          "rejected",
        "adminNote":       "Verification scores too low",
        "createdAt":       (base_date - timedelta(days=2)).isoformat()
    },
    {
        "itemId":          i_sunglasses,
        "claimantId":      u3,
        "quizScore":       100,
        "imageMatchScore": 92,
        "quizPassed":      True,
        "imagePassed":     True,
        "status":          "approved",
        "adminNote":       "Verified – strong match on all criteria",
        "createdAt":       (base_date - timedelta(days=1)).isoformat()
    }
]

claim_ids = db.claims.insert_many(claims_data).inserted_ids

# Update sunglasses item to claimed
db.items.update_one({"_id": item_ids[6]}, {"$set": {"status": "claimed"}})

print(f"✅ Inserted {len(claim_ids)} claims")

# ── Create indexes ─────────────────────────────────────────────────────────────
db.users.create_index("email", unique=True)
db.users.create_index("studentId", unique=True)
db.items.create_index([("status", 1)])
db.items.create_index([("categoryType", 1)])
db.items.create_index([("reporterId", 1)])
db.items.create_index([("name", "text"), ("description", "text"), ("color", "text"), ("brand", "text")])
db.claims.create_index([("itemId", 1)])
db.claims.create_index([("claimantId", 1)])
print("✅ Indexes created")

print("\n🎉 Database seeded successfully!")
print("\n📋 Demo Accounts:")
print("   👤 Student: rahul@college.edu / pass123")
print("   👤 Student: priya@college.edu / pass123")
print("   🛡️  Admin:  admin@campus.edu / admin123")
print(f"\n📦 Total items: {len(items_data)}")
print(f"📋 Total claims: {len(claims_data)}")
