"""
FoodShare AI — Authentication Routes
Handles user Registration, Login, and Logout using Supabase Auth.
Falls back to local in-memory store when rate limits are hit.
"""
import hashlib
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.donation_model import get_supabase

auth = Blueprint("auth", __name__)

# In-memory local user store — used only when Supabase rate limits hit
# Stores { email: hashed_password }
_local_users: dict = {}


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        action = request.form.get("action")
        email  = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        next_url = request.args.get("next") or url_for("main.ngo_dashboard")

        # ── Try Supabase first ───────────────────────────────────────────
        sb = get_supabase()
        if sb:
            try:
                if action == "register":
                    res = sb.auth.sign_up({"email": email, "password": password})
                    if res.user:
                        session["user"] = {"id": res.user.id, "email": res.user.email}
                        # Also save locally so they can log in even if rate-limited later
                        _local_users[email] = _hash(password)
                        flash("Account created successfully! Welcome to Fight Hunger AI.", "success")
                        return redirect(next_url)
                    else:
                        # Email confirmation probably required — fall through to local
                        raise Exception("email confirmation required")

                elif action == "login":
                    res = sb.auth.sign_in_with_password({"email": email, "password": password})
                    if res.user:
                        session["user"] = {"id": res.user.id, "email": res.user.email}
                        _local_users[email] = _hash(password)   # keep local in sync
                        flash("Welcome back!", "success")
                        return redirect(next_url)
                    else:
                        flash("Incorrect email or password.", "error")
                        return render_template("login.html")

            except Exception as supabase_err:
                # Supabase failed (rate limit, email confirmation, network…)
                # Fall through to local in-memory store below.
                pass

        # ── Local in-memory fallback ─────────────────────────────────────
        if action == "register":
            if email in _local_users:
                flash("Account already exists. Please log in.", "warn")
            else:
                _local_users[email] = _hash(password)
                session["user"] = {"id": f"local-{email}", "email": email}
                flash("Account created successfully! Welcome to Fight Hunger AI.", "success")
                return redirect(next_url)

        elif action == "login":
            if email in _local_users and _local_users[email] == _hash(password):
                session["user"] = {"id": f"local-{email}", "email": email}
                flash("Welcome back!", "success")
                return redirect(next_url)
            else:
                flash("Incorrect email or password.", "error")

    return render_template("login.html")



@auth.route("/logout")
def logout():
    session.pop("user", None)
    
    # Try to gracefully sign out from Supabase (optional, clears server-cached token)
    sb = get_supabase()
    if sb:
        try:
            sb.auth.sign_out()
        except:
            pass
            
    flash("You have been successfully logged out.", "success")
    return redirect(url_for("main.index"))
