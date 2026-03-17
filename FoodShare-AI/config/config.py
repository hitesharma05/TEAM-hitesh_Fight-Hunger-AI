"""
FoodShare AI — Central Configuration
Covers: Flask, Supabase, Google Maps, Email, AI Module
"""

import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    # ── Flask ─────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "foodshare-dev-key-change-in-prod")
    DEBUG = False
    TESTING = False

    # ── Supabase Configuration ────────────────────────────
    SUPABASE_URL = os.environ.get(
        "SUPABASE_URL",
        "https://nrnndnmmkwevyjuatqxb.supabase.co"
    )

    SUPABASE_KEY = os.environ.get(
        "SUPABASE_KEY",
        "sb_publishable_xXTON1OeO08xxvtnAw2AmQ_al9Rz7LQ"
    )

    SUPABASE_SERVICE = os.environ.get(
        "SUPABASE_SERVICE",
        ""
    )

    # ── Fallback SQLite ───────────────────────────────────
    SQLITE_PATH = os.path.join(BASE_DIR, "database", "foodshare.db")
    USE_SUPABASE = bool(os.environ.get("SUPABASE_URL"))

    # ── Google Maps API ───────────────────────────────────
    GOOGLE_MAPS_KEY = os.environ.get("GOOGLE_MAPS_KEY", "")

    # ── Email Notification ────────────────────────────────
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", "FoodShare AI")

    # ── AI Module ─────────────────────────────────────────
    AI_MODEL_PATH = os.path.join(BASE_DIR, "ai_module", "model.pkl")
    CO2_PER_MEAL = 2.5
    MAX_NGO_RADIUS = 20

    # ── CORS ──────────────────────────────────────────────
    CORS_ORIGINS = ["http://localhost:5000", "http://127.0.0.1:5000"]

    # ── Default Location ──────────────────────────────────
    DEFAULT_LAT = 18.9696
    DEFAULT_LNG = 72.8196


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLITE_PATH = ":memory:"
    USE_SUPABASE = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}