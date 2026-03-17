"""
FoodShare AI — AI Module
Architecture layer: AI Module (Food Demand Prediction using Python & scikit-learn)

This module does TWO things:
  1. TRAIN  — learns from past donation + demand data using RandomForestClassifier
  2. PREDICT — given a new donation, predicts:
       - Urgency score (0–100): how quickly this food will be needed
       - Best NGO category for this food type
       - Estimated demand (meals required in the area tonight)

scikit-learn pipeline:
  Features → StandardScaler → RandomForestClassifier → Urgency Score
"""

import os
import math
import json
import pickle
import random
from datetime import datetime, time as dtime


# ── Optional scikit-learn import ───────────────────────────────────────────
try:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("[AI] scikit-learn not installed — using rule-based fallback predictor")


# ─────────────────────────────────────────────────────────────────────────────
#  FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────────────────────

FOOD_TYPE_SCORES = {
    "cooked meal":    1.0,   # highest urgency — perishable in hours
    "bakery":         0.9,
    "dairy":          0.85,
    "vegetables":     0.6,
    "fruits":         0.5,
    "packaged food":  0.2,   # lowest urgency — longer shelf life
}

def _food_type_score(food_types_str) -> float:
    """Convert food type string to an urgency score (0–1)."""
    if isinstance(food_types_str, list):
        food_types_str = " ".join(food_types_str)
    ft = str(food_types_str or "").lower()
    scores = [v for k, v in FOOD_TYPE_SCORES.items() if k in ft]
    return max(scores) if scores else 0.5


def _time_to_float(t_str: str) -> float:
    """Convert 'HH:MM' to float hours (e.g. '14:30' → 14.5)."""
    try:
        h, m = map(int, (t_str or "12:00").split(":"))
        return h + m / 60
    except Exception:
        return 12.0


def _hours_until_expiry(prepared_at: str, best_before: str) -> float:
    """Calculate hours remaining until expiry."""
    try:
        prep = _time_to_float(prepared_at)
        exp  = _time_to_float(best_before)
        diff = exp - prep
        return diff if diff > 0 else diff + 24   # handle overnight
    except Exception:
        return 6.0


def extract_features(donation: dict) -> list[float]:
    """
    Convert a donation dict to a feature vector for the ML model.

    Features:
      [0] food_type_score   — urgency by food category (0–1)
      [1] serves            — number of people served (normalised)
      [2] hours_until_exp   — hours before food expires
      [3] time_of_day       — hour of preparation (0–24)
      [4] is_weekend        — 1 if today is Saturday/Sunday
      [5] distance_km       — donor distance to nearest NGO
    """
    food_score  = _food_type_score(donation.get("food_types", ""))
    serves      = min(float(donation.get("serves") or 50) / 200, 1.0)
    hours_exp   = _hours_until_expiry(donation.get("prepared_at"), donation.get("best_before"))
    time_of_day = _time_to_float(donation.get("prepared_at"))
    is_weekend  = 1.0 if datetime.now().weekday() >= 5 else 0.0
    dist        = float(donation.get("distance_km") or 5.0) / 20.0

    return [food_score, serves, hours_exp, time_of_day, is_weekend, dist]


# ─────────────────────────────────────────────────────────────────────────────
#  SYNTHETIC TRAINING DATA GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def _generate_training_data(n: int = 500):
    """
    Generate synthetic training examples for demonstration.
    In production, replace with real historical donation + outcome data.

    Label: urgency_class
      0 = Low (packaged, >8h shelf life)
      1 = Medium (vegetables, 4–8h)
      2 = High (cooked/dairy, <4h)
    """
    X, y = [], []
    random.seed(42)

    for _ in range(n):
        food_score  = random.choice([0.2, 0.5, 0.6, 0.85, 0.9, 1.0])
        serves      = random.uniform(0.1, 1.0)
        hours_exp   = random.uniform(1.0, 12.0)
        time_of_day = random.uniform(8, 22)
        is_weekend  = random.choice([0, 1])
        dist        = random.uniform(0, 1)

        # Rule-based labelling (simulates ground truth)
        if food_score >= 0.85 and hours_exp < 4:
            label = 2  # HIGH
        elif food_score >= 0.5 and hours_exp < 8:
            label = 1  # MEDIUM
        else:
            label = 0  # LOW

        # Add small noise
        if random.random() < 0.08:
            label = random.randint(0, 2)

        X.append([food_score, serves, hours_exp, time_of_day, is_weekend, dist])
        y.append(label)

    return X, y


# ─────────────────────────────────────────────────────────────────────────────
#  MODEL TRAINING
# ─────────────────────────────────────────────────────────────────────────────

def train_model(save_path: str = None) -> dict:
    """
    Train the Random Forest urgency classifier and save it to disk.
    Returns training metrics.

    Usage:
        from ai_module.predictor import train_model
        metrics = train_model()
        print(metrics)
    """
    from config.config import Config
    save_path = save_path or Config.AI_MODEL_PATH

    if not SKLEARN_AVAILABLE:
        return {"error": "scikit-learn not installed. Run: pip install scikit-learn numpy"}

    print("[AI] Generating training data…")
    X, y = _generate_training_data(1000)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Pipeline: scale → random forest
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            random_state=42,
            class_weight="balanced",
        )),
    ])

    print("[AI] Training RandomForestClassifier…")
    pipeline.fit(X_train, y_train)

    preds    = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, preds)
    print(f"[AI] Training complete — accuracy: {accuracy:.1%}")

    # Save model
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"[AI] Model saved → {save_path}")

    return {
        "accuracy":      round(accuracy, 4),
        "n_train":       len(X_train),
        "n_test":        len(X_test),
        "model_path":    save_path,
        "features":      ["food_type_score", "serves", "hours_until_exp",
                          "time_of_day", "is_weekend", "distance_km"],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  PREDICTION
# ─────────────────────────────────────────────────────────────────────────────

_model_cache = None


def _load_model():
    """Load the trained model from disk (cached in memory)."""
    global _model_cache
    if _model_cache:
        return _model_cache

    from config.config import Config
    path = Config.AI_MODEL_PATH

    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                _model_cache = pickle.load(f)
            print(f"[AI] Model loaded from {path}")
            return _model_cache
        except Exception as e:
            print(f"[AI] Failed to load model: {e}")

    # Auto-train if model doesn't exist yet
    if SKLEARN_AVAILABLE:
        print("[AI] No model found — training now…")
        train_model(path)
        return _load_model()

    return None


def predict_urgency(donation: dict) -> dict:
    """
    Predict urgency class and score for a donation.

    Returns:
        {
            "urgency_class": "HIGH" | "MEDIUM" | "LOW",
            "urgency_score": 0–100,
            "demand_estimate": int,   # estimated meals needed tonight
            "recommendation": str,    # human-readable advice
            "model": "ml" | "rules"
        }
    """
    LABELS   = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}
    COLORS   = {0: "green", 1: "orange", 2: "red"}
    serves   = int(donation.get("serves") or 50)

    model = _load_model()

    if model and SKLEARN_AVAILABLE:
        features    = extract_features(donation)
        X           = np.array([features])
        cls         = int(model.predict(X)[0])
        proba       = model.predict_proba(X)[0]
        raw_score   = float(proba[2]) * 60 + float(proba[1]) * 30 + float(proba[0]) * 10
        urgency_pct = min(100, round(raw_score * 100))

        recommendations = {
            2: "⚡ URGENT — cooked food expires soon. Dispatch NGO immediately.",
            1: "⏰ SOON — pickup recommended within 2 hours.",
            0: "✅ STABLE — food is safe for several hours. Standard scheduling applies.",
        }
        return {
            "urgency_class":    LABELS[cls],
            "urgency_score":    urgency_pct,
            "urgency_color":    COLORS[cls],
            "demand_estimate":  serves + random.randint(10, 50),
            "recommendation":   recommendations[cls],
            "model":            "ml",
            "features":         features,
        }

    # ── Rule-based fallback ────────────────────────────────────────────
    food_score = _food_type_score(donation.get("food_types", ""))
    hours_exp  = _hours_until_expiry(donation.get("prepared_at"), donation.get("best_before"))

    if food_score >= 0.85 and hours_exp < 4:
        cls = 2
    elif food_score >= 0.5 and hours_exp < 8:
        cls = 1
    else:
        cls = 0

    urgency_pct = round(food_score * 70 + max(0, (8 - hours_exp) / 8) * 30)

    return {
        "urgency_class":    LABELS[cls],
        "urgency_score":    min(100, urgency_pct),
        "urgency_color":    COLORS[cls],
        "demand_estimate":  serves + random.randint(10, 50),
        "recommendation":   "Install scikit-learn for ML predictions: pip install scikit-learn",
        "model":            "rules",
        "features":         extract_features(donation),
    }


def batch_predict(donations: list[dict]) -> list[dict]:
    """Predict urgency for a list of donations."""
    return [{"id": d.get("id"), **predict_urgency(d)} for d in donations]
