import requests
import json
import traceback

BASE_URL = "http://localhost:5000"

def run_tests():
    out = {}
    
    # 1. Test /api/stats
    try:
        res = requests.get(f"{BASE_URL}/api/stats", timeout=10)
        out["api_stats"] = {"status": res.status_code, "data": res.json()}
    except Exception as e:
        out["api_stats"] = {"error": str(e)}

    # 2. Test /api/donate (POST)
    donation_data = {
        "donor_name": "Test Bakery",
        "donor_email": "test@example.com",
        "phone": "9999999999",
        "pincode": "400050",
        "food_types": ["Bakery", "Vegetables"],
        "quantity": "10 kg",
        "serves": 20,
        "prepared_at": "10:00",
        "best_before": "20:00",
        "address": "Bandra, Mumbai"
    }
    donation_id = None
    try:
        res = requests.post(f"{BASE_URL}/api/donate", json=donation_data, timeout=10)
        data = res.json()
        out["api_donate"] = {"status": res.status_code, "data": data}
        donation_id = data.get("donation_id")
    except Exception as e:
        out["api_donate"] = {"error": str(e), "traceback": traceback.format_exc()}

    # 3. Test /api/donations/:id/status (PATCH)
    if donation_id:
        try:
            patch_data = {"status": "completed", "notify_email": ""}
            res = requests.patch(f"{BASE_URL}/api/donations/{donation_id}/status", json=patch_data, timeout=10)
            out["api_donations_status"] = {"status": res.status_code, "data": res.json()}
        except Exception as e:
            out["api_donations_status"] = {"error": str(e)}

    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    run_tests()
