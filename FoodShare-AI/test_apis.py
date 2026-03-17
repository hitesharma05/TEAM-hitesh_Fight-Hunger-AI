import requests
import time

BASE_URL = "http://localhost:5000"

def run_tests():
    print("--- Starting Backend API Verification ---")
    
    # 1. Test /api/stats
    print("\n[GET] /api/stats")
    try:
        res = requests.get(f"{BASE_URL}/api/stats")
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json()}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Test /api/donate (POST)
    print("\n[POST] /api/donate")
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
        res = requests.post(f"{BASE_URL}/api/donate", json=donation_data)
        print(f"Status: {res.status_code}")
        data = res.json()
        print(f"Response: {data}")
        donation_id = data.get("donation_id")
    except Exception as e:
        print(f"Error: {e}")

    # 3. Test /api/donations/:id/status (PATCH)
    if donation_id:
        print(f"\n[PATCH] /api/donations/{donation_id}/status")
        patch_data = {"status": "completed", "notify_email": ""}
        try:
            res = requests.patch(f"{BASE_URL}/api/donations/{donation_id}/status", json=patch_data)
            print(f"Status: {res.status_code}")
            print(f"Response: {res.json()}")
        except Exception as e:
            print(f"Error: {e}")
            
    print("\n--- Backend Verification Complete ---")

if __name__ == "__main__":
    run_tests()
