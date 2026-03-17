# 🌱 FoodShare AI — Intelligent Food Donation System

> AI-powered platform connecting surplus food donors with verified NGOs in real-time.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     USERS LAYER                         │
│              Donors ←→ NGOs                             │
│         (Donate Food)   (Request & Receive)             │
└───────────────────┬─────────────────┬───────────────────┘
                    │                 │
┌───────────────────▼─────────────────▼───────────────────┐
│           FRONTEND LAYER (User Interface)               │
│              HTML · CSS · JavaScript                    │
│   templates/ · static/css/ · static/js/                │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│         ANTIGRAVITY PLATFORM (Middleware)               │
│           Flask · Blueprint Routes · CORS               │
│        app.py · routes/donation_routes.py              │
└────────────┬──────────────────────────┬─────────────────┘
             │                          │
┌────────────▼───────────┐  ┌──────────▼──────────────────┐
│   SUPABASE BACKEND     │  │     EXTERNAL SERVICES        │
│  PostgreSQL Database   │  │  Google Maps API             │
│  Authentication        │  │  (Location + Geocoding)      │
│  Real-time API         │  │                              │
│  models/donation_model │  │  Email Notification          │
└────────────┬───────────┘  │  (SMTP / Gmail)              │
             │              │  utils/email_utils.py        │
┌────────────▼───────────┐  └─────────────────────────────┘
│      AI MODULE         │
│  Food Demand Prediction│
│  scikit-learn          │
│  RandomForestClassifier│
│  ai_module/predictor.py│
└────────────────────────┘
```

---

## 📁 Project Structure

```
FoodShare-AI/
│
├── app.py                      ← Flask app factory + entry point
├── requirements.txt            ← All Python dependencies
├── .env.example                ← Environment variable template
├── README.md
│
├── config/
│   └── config.py               ← All settings: Flask, Supabase, Maps, Email, AI
│
├── database/
│   └── foodshare.db            ← SQLite DB (auto-created if Supabase not set up)
│
├── models/
│   └── donation_model.py       ← DB schema, CRUD — works with Supabase OR SQLite
│
├── routes/
│   └── donation_routes.py      ← All URL routes — wires all 5 layers together
│
├── utils/
│   ├── map_utils.py            ← Google Maps geocoding + AI NGO matching
│   └── email_utils.py         ← Email notification system (donor + NGO alerts)
│
├── ai_module/
│   └── predictor.py           ← scikit-learn food demand & urgency prediction
│
├── static/
│   ├── css/style.css           ← Glassmorphism design system
│   ├── js/script.js            ← Frontend ↔ API bridge + dashboard refresh
│   └── images/logo.svg
│
└── templates/
    ├── base.html               ← Shared nav, footer, scripts
    ├── index.html              ← Landing page
    ├── donor.html              ← Donor portal
    ├── donation_form.html      ← Donation form + live AI urgency preview
    ├── ngo_dashboard.html      ← Live NGO dashboard
    └── success.html            ← Post-donation confirmation
```

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your API keys (see Configuration section below)
```

### 3. Run the app
```bash
python app.py
```

Open → **http://localhost:5000**

> The app auto-detects whether Supabase is configured.
> If `SUPABASE_URL` is not set, it falls back to a local SQLite database automatically.

---

## ⚙️ Configuration

### Option A — SQLite (Zero Setup, for development/hackathon)
No configuration needed. The app creates `database/foodshare.db` automatically on first run with seeded NGO data.

### Option B — Supabase (Production)

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** and run the schema from `models/donation_model.py` (`SUPABASE_SCHEMA_SQL`)
3. Copy your keys from **Project Settings → API**
4. Add to `.env`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE=your_service_role_key
```

### Google Maps API (Location Tracking)
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Enable **Maps JavaScript API** + **Geocoding API**
3. Create an API key and add to `.env`:
```
GOOGLE_MAPS_KEY=your_api_key
```
> Without this key, the app uses a local pincode lookup table as fallback.

### Email Notifications (Gmail)
1. Enable **2-Factor Authentication** on your Gmail account
2. Go to **Google Account → Security → App Passwords**
3. Create an App Password for "Mail"
4. Add to `.env`:
```
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=xxxx_xxxx_xxxx_xxxx  ← 16-char app password
```
> Without SMTP config, donations still work — emails are just skipped silently.

---

## 🌐 Pages

| URL | Template | Description |
|-----|----------|-------------|
| `/` | `index.html` | Full landing page |
| `/donor` | `donor.html` | Donor portal |
| `/donate` | `donation_form.html` | Food donation form with live AI preview |
| `/dashboard` | `ngo_dashboard.html` | NGO real-time dashboard |
| `/success/<id>` | `success.html` | Donation confirmation |

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/donate` | Submit donation → geocode → AI match → save → email |
| `GET` | `/api/stats` | Live dashboard metrics (polled every 30s) |
| `GET` | `/api/donations` | List donations (`?status=matched&limit=20`) |
| `GET` | `/api/donations/<id>` | Single donation detail |
| `PATCH` | `/api/donations/<id>/status` | Update status (matched/completed) |
| `GET` | `/api/ngos` | All NGO partners |
| `GET` | `/api/ngos/nearby` | NGOs sorted by distance (`?pincode=400001`) |
| `POST` | `/api/ai/predict` | Run urgency prediction without saving |
| `POST` | `/api/ai/train` | Retrain the scikit-learn model |
| `GET` | `/api/geocode` | Geocode an address via Google Maps |

---

## 🤖 AI Module — How It Works

The `ai_module/predictor.py` uses a **scikit-learn RandomForestClassifier** pipeline:

```
Donation data → Feature extraction → StandardScaler → RandomForest → Urgency class
```

**Features used:**
- `food_type_score` — cooked meals score highest (most perishable)
- `serves` — normalised serving count
- `hours_until_expiry` — calculated from prepared_at → best_before
- `time_of_day` — morning donations have longer runway
- `is_weekend` — higher demand on weekends
- `distance_km` — proximity to matched NGO

**Output:**
```json
{
  "urgency_class": "HIGH",
  "urgency_score": 87,
  "recommendation": "⚡ URGENT — dispatch NGO immediately",
  "demand_estimate": 120,
  "model": "ml"
}
```

The model auto-trains on first run using synthetic data. In production, replace the training data with real historical donation outcomes.

---

## 🗄️ Database Tables

**`donations`** — every submitted donation with geocoded coordinates, AI urgency score, matched NGO, and status lifecycle (`pending → matched → completed`).

**`ngos`** — verified NGO partners with GPS coordinates for distance-based matching.

**`impact`** — running counters for meals rescued, CO₂ saved (meals × 2.5 kg), and platform statistics shown on the landing page.

---

## 🚢 Production Deployment

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

**Recommended hosts:**
- [Render.com](https://render.com) — free tier, connects to GitHub, auto-deploys
- [Railway.app](https://railway.app) — supports PostgreSQL natively
- [Fly.io](https://fly.io) — global edge deployment

---

## 🔮 Upgrade Path

| Feature | How |
|---------|-----|
| Real geocoding | Replace pincode table in `utils/map_utils.py` with `googlemaps.Client` |
| SMS alerts | Add `twilio` package in `/api/donate` route after NGO match |
| Auth | Add `flask-login` or Supabase Auth to protect `/dashboard` |
| Better AI | Replace synthetic training data in `ai_module/predictor.py` with real outcomes |
| Realtime dashboard | Enable Supabase Realtime for `donations` table and use JS websocket client |

---

Built with ❤️ for a hunger-free world.
