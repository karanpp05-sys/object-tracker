# 🔍 ObjectTracker — Campus Lost & Found System

A full-stack campus lost & found platform with **AI-powered quiz verification** and **OpenCV ORB image matching**.

---

## 🏗️ Project Structure

```
object-tracker/
├── backend/                  ← Flask REST API
│   ├── app.py                ← Main Flask application
│   ├── database.py           ← MongoDB connection helpers
│   ├── seed.py               ← Database seeder with demo data
│   ├── requirements.txt      ← Python dependencies
│   ├── .env.example          ← Environment variables template
│   └── routes/
│       ├── auth_routes.py    ← POST /auth/login, /auth/register
│       ├── item_routes.py    ← CRUD /items/lost, /items/found
│       ├── claim_routes.py   ← POST /claims, PUT /claims/:id
│       ├── quiz_routes.py    ← Dynamic quiz generation & validation
│       ├── image_routes.py   ← OpenCV ORB image comparison
│       └── admin_routes.py   ← Admin dashboard, users, stats
├── frontend/
│   └── index.html            ← Complete single-file frontend (no build step)
└── uploads/                  ← Image uploads (auto-created)
```

---

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.10+
- MongoDB running locally (or Atlas URI)
- pip

### 2. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your MongoDB URI and secret keys

# Seed database with demo data
python seed.py

# Start Flask server
python app.py
```

Server starts at: `http://localhost:5000`

### 3. Open Frontend

Simply open `frontend/index.html` in your browser — **no build step required**.

Or serve it with any static server:
```bash
cd frontend
python -m http.server 3000
# Open http://localhost:3000
```

> **Note:** The frontend works **offline in demo mode** even without the backend running. All mock data is built-in.

---

## 🔐 Demo Accounts

| Role    | Email                 | Password   |
|---------|-----------------------|------------|
| Student | rahul@college.edu     | pass123    |
| Student | priya@college.edu     | pass123    |
| Admin   | admin@campus.edu      | admin123   |

---

## 🌐 API Endpoints

### Auth
| Method | Endpoint              | Description           |
|--------|-----------------------|-----------------------|
| POST   | /api/auth/register    | Create account        |
| POST   | /api/auth/login       | Login & get JWT token |
| GET    | /api/auth/me          | Get current user      |

### Items
| Method | Endpoint              | Description           |
|--------|-----------------------|-----------------------|
| POST   | /api/items/lost       | Report lost item      |
| POST   | /api/items/found      | Report found item     |
| GET    | /api/items            | Browse all items      |
| GET    | /api/items/:id        | Get single item       |
| GET    | /api/items/my         | My reported items     |
| DELETE | /api/items/:id        | Delete item           |

### Claims
| Method | Endpoint              | Description           |
|--------|-----------------------|-----------------------|
| POST   | /api/claims           | Submit claim          |
| GET    | /api/claims           | My claims / all (admin) |
| PUT    | /api/claims/:id       | Approve/reject (admin)|

### Quiz (Verification Step 1)
| Method | Endpoint              | Description                    |
|--------|-----------------------|--------------------------------|
| POST   | /api/quiz/generate    | Generate 4-question quiz       |
| POST   | /api/quiz/validate    | Validate answers, return score |

### Image (Verification Step 2)
| Method | Endpoint                   | Description              |
|--------|----------------------------|--------------------------|
| POST   | /api/image/compare         | Compare 2 uploaded images |
| POST   | /api/image/compare-items   | Compare by item IDs       |

### Admin
| Method | Endpoint              | Description           |
|--------|-----------------------|-----------------------|
| GET    | /api/admin/stats      | System statistics     |
| GET    | /api/admin/users      | All users             |
| DELETE | /api/admin/users/:id  | Delete user           |
| GET    | /api/admin/items      | All items             |
| GET    | /api/admin/claims     | All claims            |

---

## 🤖 Verification System

### Step 1 — Dynamic Quiz (Pass: ≥60%)
- Generates **4 questions** from the item's own database fields
- Questions cover: color, brand, location, item type, unique features
- Different question sets for **Tech** vs **Normal** items
- Options are shuffled — only owner knows correct answers

### Step 2 — Image Matching (Pass: ≥70%)
- Uses **OpenCV ORB** (Oriented FAST and Rotated BRIEF)
- **BFMatcher** with Hamming distance + Lowe's ratio test
- Optional **SSIM** (Structural Similarity) for bonus accuracy
- Falls back to simulated score if OpenCV not installed

### Both steps must pass → Claim sent to Admin for final approval

---

## 🛠️ Tech Stack

| Layer    | Technology                              |
|----------|-----------------------------------------|
| Backend  | Flask 3, Flask-JWT-Extended, Flask-CORS |
| Database | MongoDB (PyMongo)                       |
| Auth     | JWT tokens, Werkzeug password hashing   |
| Images   | OpenCV (ORB), scikit-image (SSIM)       |
| Frontend | Vanilla HTML/CSS/JS, Bootstrap-free     |
| Fonts    | Syne (display), DM Sans (body)          |

---

## 📦 MongoDB Collections

- **users** — email, studentId, password hash, role
- **items** — name, categoryType, color, brand, features, location, imagePath, status, reporterId
- **claims** — itemId, claimantId, quizScore, imageMatchScore, status, adminNote
- **quiz_sessions** — temp storage for quiz answers (TTL)

---

## 🎨 Frontend Features

- Dark glassmorphism design with animated ambient blobs
- Fully responsive (mobile-friendly)
- Works offline with built-in mock data
- Connects to Flask API automatically when running
- Pages: Home, Browse, Report Lost/Found, Dashboard, Admin Panel
- Claim flow: Quiz → Image Compare → Result → Admin Review
