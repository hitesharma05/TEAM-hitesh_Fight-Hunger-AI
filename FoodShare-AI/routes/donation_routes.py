"""
FoodShare AI — All URL Routes (Flask Blueprint)
Wires together: Frontend ↔ Antigravity Middleware ↔ Supabase ↔ AI Module ↔ External Services
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from models.donation_model import (
    create_donation, get_donation, list_donations,
    update_donation_status, list_ngos, get_impact_stats,
)
from utils.map_utils    import find_best_ngo, get_ngos_near, geocode_address
from utils.email_utils  import notify_donor_confirmation, notify_ngo_new_match, notify_status_update
from utils.auth_utils   import login_required
from ai_module.predictor import predict_urgency, train_model

main = Blueprint("main", __name__)


# ═════════════════════════════════════════════════════════════════════════════
#  PAGE ROUTES  (HTML — Frontend Layer)
# ═════════════════════════════════════════════════════════════════════════════

@main.route("/")
def index():
    stats = get_impact_stats()
    return render_template("index.html", stats=stats)


@main.route("/donor")
def donor():
    return render_template("donor.html")


@main.route("/donate")
@login_required
def donation_form():
    pincode = request.args.get("pincode", "400001")
    nearby  = get_ngos_near(pincode=pincode, max_km=10)
    from config.config import Config
    return render_template("donation_form.html",
                           nearby_ngos=nearby,
                           pincode=pincode,
                           maps_key=Config.GOOGLE_MAPS_KEY)


@main.route("/dashboard")
@login_required
def ngo_dashboard():
    stats     = get_impact_stats()
    donations = list_donations(limit=20)
    ngos      = list_ngos()
    from config.config import Config
    return render_template("ngo_dashboard.html",
                           stats=stats,
                           donations=donations,
                           ngos=ngos,
                           maps_key=Config.GOOGLE_MAPS_KEY)


@main.route("/success/<donation_id>")
def success(donation_id):
    donation = get_donation(donation_id)
    if not donation:
        flash("Donation not found.", "error")
        return redirect(url_for("main.index"))
    return render_template("success.html", donation=donation)


# Removed duplicate donor route


@main.route("/analytics")
@login_required
def analytics():
    stats     = get_impact_stats()
    donations = list_donations(limit=100)
    ngos      = list_ngos()

    # Aggregate food type counts
    food_counts: dict = {}
    for d in donations:
        for ft in (d.get("food_types") or "").split(","):
            ft = ft.strip()
            if ft:
                food_counts[ft] = food_counts.get(ft, 0) + 1

    # Aggregate status counts
    status_counts = {"pending": 0, "matched": 0, "completed": 0, "expired": 0}
    for d in donations:
        s = d.get("status", "pending")
        status_counts[s] = status_counts.get(s, 0) + 1

    # NGO capacity utilisation
    ngo_data = [{"name": n["name"], "area": n.get("area", ""), "capacity": n.get("capacity", 100), "status": n.get("status", "online")} for n in ngos]

    return render_template("analytics.html",
                           stats=stats,
                           food_counts=food_counts,
                           status_counts=status_counts,
                           ngo_data=ngo_data,
                           total_donations=len(donations))


@main.route("/api/analytics")
def api_analytics():
    """GET /api/analytics — aggregated stats for charts."""
    donations = list_donations(limit=100)
    food_counts: dict = {}
    status_counts = {"pending": 0, "matched": 0, "completed": 0}
    for d in donations:
        for ft in (d.get("food_types") or "").split(","):
            ft = ft.strip()
            if ft:
                food_counts[ft] = food_counts.get(ft, 0) + 1
        s = d.get("status", "pending")
        if s in status_counts:
            status_counts[s] += 1
    stats = get_impact_stats()
    return jsonify({
        "food_counts": food_counts,
        "status_counts": status_counts,
        "total_donations": len(donations),
        "impact": stats,
    })


# ═════════════════════════════════════════════════════════════════════════════
#  API ROUTES  (JSON — Antigravity Middleware layer)
# ═════════════════════════════════════════════════════════════════════════════

@main.route("/api/donate", methods=["POST"])
def api_donate():
    """
    POST /api/donate
    Full pipeline:
      1. Validate input
      2. Geocode address (Google Maps API)
      3. Run AI urgency prediction (scikit-learn)
      4. Find best NGO (AI matching algorithm)
      5. Save to Supabase / SQLite
      6. Send email notifications (donor + NGO)
      7. Return JSON response

    Body (JSON):
    {
        "donor_name":  "Hotel Taj",
        "donor_email": "manager@taj.com",
        "phone":       "+91 98765 43210",
        "pincode":     "400001",
        "food_types":  ["Cooked Meal", "Rice"],
        "quantity":    "40 kg",
        "serves":      80,
        "prepared_at": "12:00",
        "best_before": "18:00",
        "address":     "Apollo Bunder, Colaba, Mumbai"
    }
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"success": False, "error": "Invalid JSON"}), 400

    # ── Validation ────────────────────────────────────────────────────
    if not (data.get("donor_name") or "").strip():
        return jsonify({"success": False, "error": "donor_name is required"}), 422
    if not (data.get("address") or "").strip():
        return jsonify({"success": False, "error": "address is required"}), 422

    # ── Step 1: Geocode donor address (Google Maps API) ───────────────
    coords = geocode_address(data.get("address", ""))
    if coords:
        data["lat"], data["lng"] = coords

    # ── Step 2: AI Urgency Prediction (scikit-learn) ──────────────────
    urgency = predict_urgency(data)
    data["urgency_score"] = urgency["urgency_score"]
    data["urgency_class"] = urgency["urgency_class"]

    # ── Step 3: AI NGO Matching ───────────────────────────────────────
    matched_ngo = find_best_ngo(
        pincode   = data.get("pincode"),
        lat       = data.get("lat"),
        lng       = data.get("lng"),
        food_types= data.get("food_types", []),
    )

    # ── Step 4: Save to Database (Supabase or SQLite) ─────────────────
    donation_id = create_donation(
        data           = data,
        matched_ngo_id = matched_ngo["id"] if matched_ngo else None,
    )

    # ── Step 5: Email Notifications ───────────────────────────────────
    donor_email = data.get("donor_email", "")
    if donor_email:
        notify_donor_confirmation(donor_email, {**data, "id": donation_id}, matched_ngo)

    if matched_ngo and matched_ngo.get("email"):
        notify_ngo_new_match(matched_ngo["email"], {**data, "id": donation_id}, matched_ngo)

    return jsonify({
        "success":      True,
        "donation_id":  donation_id,
        "matched_ngo":  matched_ngo,
        "urgency":      urgency,
        "redirect_url": url_for("main.success", donation_id=donation_id),
        "message": (
            f"Matched to {matched_ngo['name']} ({matched_ngo['distance_km']} km away)"
            if matched_ngo else "Donation listed — matching in progress"
        ),
    }), 201


@main.route("/api/stats")
def api_stats():
    """GET /api/stats — live dashboard metrics (polled every 30s)."""
    return jsonify(get_impact_stats())


@main.route("/api/donations")
def api_donations():
    """GET /api/donations?status=matched&limit=20"""
    status = request.args.get("status")
    limit  = min(int(request.args.get("limit", 50)), 200)
    return jsonify(list_donations(status=status, limit=limit))


@main.route("/api/donations/<donation_id>")
def api_get_donation(donation_id):
    d = get_donation(donation_id)
    return (jsonify(d), 200) if d else (jsonify({"error": "Not found"}), 404)


@main.route("/api/donations/<donation_id>/status", methods=["PATCH"])
def api_update_status(donation_id):
    """PATCH /api/donations/:id/status  Body: {"status": "completed"}"""
    data       = request.get_json(force=True, silent=True) or {}
    new_status = data.get("status")

    if not update_donation_status(donation_id, new_status):
        return jsonify({"error": "Invalid status"}), 400

    # Send status email if recipient is provided
    recipient = data.get("notify_email")
    if recipient:
        donation = get_donation(donation_id) or {}
        notify_status_update(recipient, donation, new_status)

    return jsonify({"success": True, "donation_id": donation_id, "status": new_status})


@main.route("/api/ngos")
def api_ngos():
    return jsonify(list_ngos())


@main.route("/api/ngos/nearby")
def api_ngos_nearby():
    """GET /api/ngos/nearby?pincode=400001&max_km=10"""
    return jsonify(get_ngos_near(
        pincode = request.args.get("pincode", "400001"),
        max_km  = float(request.args.get("max_km", 10)),
    ))


@main.route("/api/ai/predict", methods=["POST"])
def api_ai_predict():
    """
    POST /api/ai/predict
    Run urgency prediction on a donation dict without saving it.
    Useful for real-time form feedback.
    """
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(predict_urgency(data))


@main.route("/api/ai/train", methods=["POST"])
@login_required
def api_ai_train():
    """
    POST /api/ai/train
    Retrain the ML model. Protect this endpoint in production!
    """
    metrics = train_model()
    return jsonify(metrics)


@main.route("/api/geocode")
def api_geocode():
    """GET /api/geocode?address=400001+Mumbai — geocode via Google Maps."""
    address = request.args.get("address", "")
    coords  = geocode_address(address)
    if coords:
        return jsonify({"lat": coords[0], "lng": coords[1], "address": address})
    return jsonify({"error": "Could not geocode address"}), 404

@main.route("/api/config/maps")
def api_config_maps():
    """GET /api/config/maps — returns the Google Maps API key for frontend dynamic loading."""
    from config.config import Config
    return jsonify({"key": Config.GOOGLE_MAPS_KEY})
