"""
FoodShare AI — Map Utilities
Architecture layer: Google Maps API (Location Tracking)

Responsibilities:
  1. Geocode donor pincode → GPS coords  (Google Maps Geocoding API)
  2. Haversine distance calculation
  3. AI NGO matching (nearest online NGO)
  4. Reverse geocode coords → address
"""

import math
import urllib.request
import urllib.parse
import json
from config.config import Config
from models.donation_model import list_ngos


# ─────────────────────────────────────────────────────────────────────────────
#  HAVERSINE DISTANCE
# ─────────────────────────────────────────────────────────────────────────────

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return great-circle distance in km between two GPS points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─────────────────────────────────────────────────────────────────────────────
#  GOOGLE MAPS GEOCODING API
# ─────────────────────────────────────────────────────────────────────────────

# Pincode lookup table — used as fallback when the API key is not set
_PINCODE_COORDS: dict[str, tuple[float, float]] = {
    "400001": (18.9322, 72.8264),
    "400005": (18.9750, 72.8258),
    "400050": (19.0176, 72.8561),
    "400053": (19.0596, 72.8295),
    "400058": (19.0825, 72.7411),
    "400069": (19.1136, 72.8697),
    "400093": (19.1641, 72.8597),
}


from typing import Optional, Tuple

def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Convert a free-text address to (lat, lng) using Google Maps Geocoding API.
    Returns None on failure.

    Docs: https://developers.google.com/maps/documentation/geocoding
    """
    api_key = Config.GOOGLE_MAPS_KEY
    if "YOUR_GOOGLE" in api_key or not api_key:
        return None

    base = "https://maps.googleapis.com/maps/api/geocode/json"
    params = urllib.parse.urlencode({"address": address, "key": api_key})
    url = f"{base}?{params}"

    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        if data.get("status") == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return float(loc["lat"]), float(loc["lng"])
    except Exception as e:
        print(f"[Maps] Geocoding failed: {e}")
    return None


def geocode_pincode(pincode: str) -> tuple[float, float]:
    """
    Convert a pincode string to (lat, lng).
    Order: 1) Google Maps API  2) local lookup table  3) default city center
    """
    pincode = (pincode or "").strip()

    # Try Google Maps API first
    coords = geocode_address(f"{pincode}, India")
    if coords:
        return coords

    # Fall back to local table
    if pincode in _PINCODE_COORDS:
        return _PINCODE_COORDS[pincode]

    # Default: Mumbai Central
    return Config.DEFAULT_LAT, Config.DEFAULT_LNG


def reverse_geocode(lat: float, lng: float) -> str:
    """
    Convert GPS coordinates to a human-readable address using Google Maps.
    Returns a fallback string if the API is not available.
    """
    api_key = Config.GOOGLE_MAPS_KEY
    if "YOUR_GOOGLE" in api_key or not api_key:
        return f"{lat:.4f}, {lng:.4f}"

    base = "https://maps.googleapis.com/maps/api/geocode/json"
    params = urllib.parse.urlencode({"latlng": f"{lat},{lng}", "key": api_key})
    url = f"{base}?{params}"

    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        if data.get("status") == "OK":
            return data["results"][0].get("formatted_address", "")
    except Exception as e:
        print(f"[Maps] Reverse geocode failed: {e}")
    return f"{lat:.4f}, {lng:.4f}"


def get_maps_embed_url(address: str) -> str:
    """Return a Google Maps embed URL for displaying on the page."""
    api_key = Config.GOOGLE_MAPS_KEY
    encoded = urllib.parse.quote(address)
    return f"https://www.google.com/maps/embed/v1/place?key={api_key}&q={encoded}"


# ─────────────────────────────────────────────────────────────────────────────
#  AI NGO MATCHING  (uses map_utils for distance)
# ─────────────────────────────────────────────────────────────────────────────

def find_best_ngo(pincode: str = None, lat: float = None, lng: float = None,
                  food_types: list = None) -> Optional[dict]:
    """
    AI Matching Algorithm (Antigravity Platform layer):
      1. Resolve donor location via pincode or direct coords
      2. Filter to online NGOs
      3. Rank by Haversine distance (primary) + capacity (secondary)
      4. Return best match with distance_km attached

    Upgrade path:
      - Add scikit-learn RandomForest for demand prediction weighting
      - Include food-type compatibility scoring
      - Consider time-of-day (peak vs off-peak capacity)
    """
    # Resolve donor location
    if lat and lng:
        ref_lat, ref_lng = float(lat), float(lng)
    else:
        ref_lat, ref_lng = geocode_pincode(pincode or "")

    ngos = list_ngos()
    candidates = [n for n in ngos if n.get("status") == "online"]
    if not candidates:
        candidates = [n for n in ngos if n.get("status") != "offline"]
    if not candidates:
        return None

    def score(ngo: dict) -> float:
        dist = haversine_km(ref_lat, ref_lng, ngo["lat"], ngo["lng"])
        cap_bonus = -min(ngo.get("capacity", 100) / 1000, 0.5)  # slight bonus for higher capacity
        return dist + cap_bonus

    best = min(candidates, key=score)
    best = dict(best)
    best["distance_km"] = round(haversine_km(ref_lat, ref_lng, best["lat"], best["lng"]), 1)
    return best


def get_ngos_near(pincode: str = None, lat: float = None, lng: float = None,
                  max_km: float = None) -> list[dict]:
    """Return all NGOs within max_km, sorted by distance."""
    max_km = max_km or Config.MAX_NGO_RADIUS
    if lat and lng:
        ref_lat, ref_lng = float(lat), float(lng)
    else:
        ref_lat, ref_lng = geocode_pincode(pincode or "")

    result = []
    for ngo in list_ngos():
        d = haversine_km(ref_lat, ref_lng, ngo["lat"], ngo["lng"])
        if d <= max_km:
            n = dict(ngo)
            n["distance_km"] = round(d, 1)
            result.append(n)

    result.sort(key=lambda n: n["distance_km"])
    return result
