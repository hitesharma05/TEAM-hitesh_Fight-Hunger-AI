import requests
import json
import traceback

BASE_URL = "http://localhost:5000"

def run_tests():
    out = {}
    
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
    try:
        res = requests.post(f"{BASE_URL}/api/donate", json=donation_data, timeout=10)
        out["api_donate"] = {
            "status": res.status_code, 
            "text_preview": res.text[:2000] # Capture the HTML or text error
        }
    except Exception as e:
        out["api_donate"] = {"error": str(e)}

    with open("test_results2.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    run_tests()
