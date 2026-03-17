"""
FoodShare AI — Application Entry Point
Architecture: Frontend → Flask API → Supabase / SQLite → AI Module

Run: python app.py
"""
import os
from flask import Flask
from flask_cors import CORS

# Load .env automatically (works even without .env file)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config.config import config_map
from models.donation_model import init_db, using_supabase
from routes.donation_routes import main
from routes.auth_routes import auth


def create_app(env: str = None) -> Flask:
    env = env or os.environ.get("FLASK_ENV", "development")
    cfg = config_map.get(env, config_map["default"])

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(cfg)

    CORS(app, origins=cfg.CORS_ORIGINS)

    @app.context_processor
    def inject_config():
        return {"config": app.config}

    app.register_blueprint(main)
    app.register_blueprint(auth)

    # Initialise database
    os.makedirs(os.path.dirname(cfg.SQLITE_PATH), exist_ok=True)
    if not using_supabase():
        init_db(cfg.SQLITE_PATH)

    return app


if __name__ == "__main__":
    app = create_app()

    print("\n  ╔══════════════════════════════════════════╗")
    print("  ║      🌱  FoodShare AI  is  running       ║")
    print("  ╠══════════════════════════════════════════╣")
    print(f"  ║  🌐  http://localhost:5000               ║")
    print(f"  ║  🗄️  DB: {'Supabase (PostgreSQL)' if using_supabase() else 'SQLite (local fallback)'}  ║")
    print("  ╚══════════════════════════════════════════╝\n")

    app.run(debug=True, host="0.0.0.0", port=5000)
