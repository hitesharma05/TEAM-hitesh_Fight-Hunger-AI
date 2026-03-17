"""
FoodShare AI — Email Notification System
Architecture layer: External Services → Email Notification System

Sends emails for:
  - Donor confirmation after submitting a donation
  - NGO alert when a new donation is matched to them
  - Status updates (pickup confirmed, completed)

Uses Python's built-in smtplib — no extra library needed.
For production, swap in SendGrid or Mailgun for better deliverability.
"""

import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.config import Config


# ─────────────────────────────────────────────────────────────────────────────
#  CORE SEND FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def _send_email(to: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """
    Send an email via SMTP (Gmail by default).
    Returns True on success, False on failure.

    Gmail setup:
      1. Enable 2FA on your Gmail account
      2. Go to Google Account → Security → App Passwords
      3. Create an App Password for 'Mail'
      4. Set MAIL_PASSWORD env variable to that 16-char password
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = Config.MAIL_FROM
        msg["To"]      = to

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT) as server:
            server.ehlo()
            if Config.MAIL_USE_TLS:
                server.starttls()
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.sendmail(Config.MAIL_FROM, to, msg.as_string())

        print(f"[Email] Sent '{subject}' → {to}")
        return True

    except Exception as e:
        print(f"[Email] Failed to send to {to}: {e}")
        return False


def send_async(to: str, subject: str, html_body: str):
    """Send email in a background thread — never blocks Flask request."""
    t = threading.Thread(target=_send_email, args=(to, subject, html_body), daemon=True)
    t.start()


def is_configured() -> bool:
    """Return True if SMTP credentials are set."""
    return (
        "your@gmail.com" not in Config.MAIL_USERNAME
        and bool(Config.MAIL_PASSWORD)
        and Config.MAIL_PASSWORD != "your_app_password"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  EMAIL TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────

def _base_html(content: str) -> str:
    """Wrap content in a consistent branded email shell."""
    return f"""
<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
  body{{font-family:Arial,sans-serif;background:#0a1a0f;margin:0;padding:20px}}
  .card{{background:#0f2216;border:1px solid rgba(255,255,255,.12);border-radius:16px;
         max-width:560px;margin:0 auto;padding:32px;color:#e8f5e9}}
  h1{{color:#2ecc71;font-size:22px;margin:0 0 8px}}
  .sub{{color:rgba(232,245,233,.55);font-size:13px;margin-bottom:24px}}
  table{{width:100%;border-collapse:collapse;margin:16px 0}}
  td{{padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.06);font-size:13px}}
  td:first-child{{color:rgba(232,245,233,.55);width:40%}}
  .badge{{display:inline-block;padding:3px 12px;border-radius:50px;font-size:11px;font-weight:700}}
  .green{{background:rgba(46,204,113,.15);color:#2ecc71;border:1px solid rgba(46,204,113,.3)}}
  .orange{{background:rgba(243,156,18,.15);color:#f39c12;border:1px solid rgba(243,156,18,.3)}}
  .btn{{display:inline-block;background:#2ecc71;color:#0a1a0f;padding:12px 28px;
        border-radius:50px;text-decoration:none;font-weight:700;margin-top:20px}}
  .footer{{text-align:center;color:rgba(232,245,233,.3);font-size:11px;margin-top:24px}}
</style></head><body>
<div class="card">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:24px">
    <div style="width:36px;height:36px;background:linear-gradient(135deg,#2ecc71,#f39c12);
                border-radius:10px;display:flex;align-items:center;justify-content:center;
                font-size:18px">🌱</div>
    <span style="font-size:18px;font-weight:700;color:#e8f5e9">FoodShare <span style="color:#2ecc71">AI</span></span>
  </div>
  {content}
  <div class="footer">© 2025 FoodShare AI · Turning Food Waste into Hope</div>
</div></body></html>"""


from typing import Optional

def notify_donor_confirmation(donor_email: str, donation: dict, ngo: Optional[dict]):
    """Email sent to the donor after their donation is submitted."""
    if not is_configured():
        print("[Email] SMTP not configured — skipping donor confirmation")
        return

    ngo_info = (
        f"<tr><td>Matched NGO</td><td><span class='badge green'>{ngo['name']}</span></td></tr>"
        f"<tr><td>NGO Distance</td><td>{ngo.get('distance_km','—')} km away</td></tr>"
        if ngo else
        "<tr><td>Status</td><td><span class='badge orange'>Matching in progress…</span></td></tr>"
    )

    content = f"""
    <h1>Donation Confirmed! 🎉</h1>
    <p class="sub">Your surplus food has been listed and our AI found the best match.</p>
    <table>
      <tr><td>Donation ID</td><td>#{donation.get('id','—')}</td></tr>
      <tr><td>Food Type</td><td>{donation.get('food_types','—')}</td></tr>
      <tr><td>Quantity</td><td>{donation.get('quantity','—')}</td></tr>
      <tr><td>Serves</td><td>~{donation.get('serves',0)} people</td></tr>
      <tr><td>Pickup Address</td><td>{donation.get('address','—')}</td></tr>
      {ngo_info}
    </table>
    <p style="color:rgba(232,245,233,.55);font-size:13px">
      The NGO will contact you to arrange pickup. Thank you for making a difference! 💚
    </p>
    <a href="http://localhost:5000/dashboard" class="btn">View Dashboard</a>
    """
    send_async(donor_email, "✅ Your FoodShare AI Donation is Confirmed", _base_html(content))


def notify_ngo_new_match(ngo_email: str, donation: dict, ngo: dict):
    """Email sent to the NGO when a new donation is matched to them."""
    if not is_configured():
        print("[Email] SMTP not configured — skipping NGO notification")
        return

    content = f"""
    <h1>New Food Donation Matched! 🍱</h1>
    <p class="sub">A donation has been AI-matched to <strong>{ngo.get('name','your NGO')}</strong>.</p>
    <table>
      <tr><td>Donor</td><td>{donation.get('donor_name','—')}</td></tr>
      <tr><td>Contact</td><td>{donation.get('phone','—')}</td></tr>
      <tr><td>Food Type</td><td>{donation.get('food_types','—')}</td></tr>
      <tr><td>Quantity</td><td>{donation.get('quantity','—')}</td></tr>
      <tr><td>Serves</td><td>~{donation.get('serves',0)} people</td></tr>
      <tr><td>Pickup Address</td><td>{donation.get('address','—')}</td></tr>
      <tr><td>Best Before</td><td>{donation.get('best_before','—')}</td></tr>
      <tr><td>Distance</td><td>{ngo.get('distance_km','—')} km from you</td></tr>
    </table>
    <p style="color:rgba(232,245,233,.55);font-size:13px">
      Please contact the donor as soon as possible to arrange pickup.
    </p>
    <a href="http://localhost:5000/dashboard" class="btn">Open Dashboard</a>
    """
    send_async(ngo_email, f"🍱 New Donation Match — {donation.get('food_types','Food')}", _base_html(content))


def notify_status_update(recipient_email: str, donation: dict, new_status: str):
    """Email sent when a donation status changes (matched → completed)."""
    if not is_configured():
        return

    status_labels = {
        "matched":   ("Matched to NGO", "🤖", "green"),
        "completed": ("Pickup Completed", "✅", "green"),
        "expired":   ("Donation Expired", "⏰", "orange"),
    }
    label, icon, badge_cls = status_labels.get(new_status, ("Status Updated", "📋", "green"))

    content = f"""
    <h1>{icon} Donation {label}</h1>
    <p class="sub">Status update for donation #{donation.get('id','—')}</p>
    <table>
      <tr><td>Donor</td><td>{donation.get('donor_name','—')}</td></tr>
      <tr><td>Food</td><td>{donation.get('food_types','—')}</td></tr>
      <tr><td>New Status</td><td><span class="badge {badge_cls}">{new_status.upper()}</span></td></tr>
    </table>
    <a href="http://localhost:5000/dashboard" class="btn">View on Dashboard</a>
    """
    send_async(recipient_email, f"{icon} FoodShare AI — Donation {label}", _base_html(content))
