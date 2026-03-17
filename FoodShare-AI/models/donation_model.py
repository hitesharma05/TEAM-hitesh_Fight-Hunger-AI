"""
FoodShare AI — Database Models
Supports BOTH Supabase (PostgreSQL) and SQLite fallback.

Architecture layer: Supabase Backend
  - PostgreSQL Database
  - Authentication
  - Real-time API
"""

import sqlite3
import os
from datetime import datetime

# ── Supabase client (installed via: pip install supabase) ──────────────────
try:
    from supabase import create_client, Client as SupabaseClient
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
#  SUPABASE SQL SCHEMA
#  Run this once in Supabase SQL Editor:
#  https://app.supabase.com → SQL Editor → New Query
# ─────────────────────────────────────────────────────────────────────────────
SUPABASE_SCHEMA_SQL = """
-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Donors / Food listings
create table if not exists donations (
    id           uuid primary key default uuid_generate_v4(),
    donor_name   text not null,
    phone        text,
    pincode      text,
    food_types   text,
    quantity     text,
    serves       integer default 0,
    prepared_at  text,
    best_before  text,
    address      text,
    lat          float,
    lng          float,
    status       text not null default 'pending',
    matched_ngo  uuid references ngos(id),
    created_at   timestamptz default now(),
    updated_at   timestamptz default now()
);

-- NGO partners
create table if not exists ngos (
    id         uuid primary key default uuid_generate_v4(),
    name       text not null,
    lat        float not null,
    lng        float not null,
    capacity   integer default 100,
    status     text default 'online',
    area       text,
    phone      text,
    email      text,
    created_at timestamptz default now()
);

-- Running impact counters
create table if not exists impact (
    id           integer primary key default 1,
    meals_today  integer default 0,
    meals_total  integer default 0,
    co2_saved_kg float   default 0,
    active_ngos  integer default 0,
    avg_resp_min integer default 0,
    updated_at   timestamptz default now()
);

-- Enable Realtime for donations table (Supabase dashboard)
-- alter publication supabase_realtime add table donations;
"""

# ─────────────────────────────────────────────────────────────────────────────
#  SQLITE SCHEMA  (fallback when Supabase is not configured)
# ─────────────────────────────────────────────────────────────────────────────
SQLITE_SCHEMA_SQL = """
create table if not exists donations (
    id           integer primary key autoincrement,
    donor_name   text not null,
    phone        text,
    pincode      text,
    food_types   text,
    quantity     text,
    serves       integer default 0,
    prepared_at  text,
    best_before  text,
    address      text,
    lat          real,
    lng          real,
    status       text not null default 'pending',
    matched_ngo  integer references ngos(id),
    created_at   text default (datetime('now')),
    updated_at   text default (datetime('now'))
);

create table if not exists ngos (
    id         integer primary key autoincrement,
    name       text not null,
    lat        real not null,
    lng        real not null,
    capacity   integer default 100,
    status     text default 'online',
    area       text,
    phone      text,
    email      text,
    created_at text default (datetime('now'))
);

create table if not exists impact (
    id           integer primary key default 1,
    meals_today  integer default 0,
    meals_total  integer default 0,
    co2_saved_kg real    default 0,
    active_ngos  integer default 0,
    avg_resp_min integer default 0,
    updated_at   text default (datetime('now'))
);
"""

SEED_NGOS = [
    ("Annapurna Foundation", 18.9750, 72.8258, 200, "online", "Colaba",  "+91 22 2202 1234", "info@annapurna.org"),
    ("Mumbai Food Bank",     19.0176, 72.8561, 500, "online", "Bandra",  "+91 22 2640 5678", "contact@mumbaifoodbank.org"),
    ("Robin Hood Army",      19.1136, 72.8697, 150, "busy",   "Andheri", "+91 98200 12345",  "mumbai@robinhoodarmy.com"),
    ("Roti Bank",            19.0596, 72.8295, 300, "online", "Dadar",   "+91 98190 67890",  "rotibank@example.org"),
    ("Feeding India",        19.0825, 72.7411, 400, "online", "Borivali","+91 98765 43210",  "info@feedingindia.org"),
]


# ─────────────────────────────────────────────────────────────────────────────
#  DB LAYER  — auto-selects Supabase or SQLite
# ─────────────────────────────────────────────────────────────────────────────

from typing import Optional

_supabase = None


def get_supabase():
    """Return a Supabase client, or None if not configured."""
    global _supabase
    if _supabase:
        return _supabase
    if not SUPABASE_AVAILABLE:
        return None
    from config.config import Config
    url = Config.SUPABASE_URL
    # Use service role key if provided, otherwise fall back to anon key
    key = Config.SUPABASE_SERVICE or Config.SUPABASE_KEY
    if not url or not key or "YOUR_PROJECT" in url:
        return None
    _supabase = create_client(url, key)
    return _supabase


def get_sqlite(db_path: str = None):
    from config.config import Config
    path = db_path or Config.SQLITE_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def using_supabase() -> bool:
    return get_supabase() is not None


def init_db(db_path: str = None):
    """Initialize SQLite schema + seed data (used when Supabase is not set up)."""
    conn = get_sqlite(db_path)
    conn.executescript(SQLITE_SCHEMA_SQL)
    if conn.execute("select count(*) from ngos").fetchone()[0] == 0:
        conn.executemany(
            "insert into ngos (name,lat,lng,capacity,status,area,phone,email) values(?,?,?,?,?,?,?,?)",
            SEED_NGOS,
        )
    if conn.execute("select count(*) from impact").fetchone()[0] == 0:
        conn.execute(
            "insert into impact(id,meals_today,meals_total,co2_saved_kg,active_ngos,avg_resp_min) values(1,247,2400000,850000,340,23)"
        )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
#  DONATIONS
# ─────────────────────────────────────────────────────────────────────────────

def create_donation(data: dict, matched_ngo_id=None, db_path=None) -> str:
    """
    Insert a donation row.
    Works with both Supabase and SQLite.
    Returns the new donation id.
    """
    print(f"DEBUG: create_donation called with data: {data}")
    food_str = ", ".join(data.get("food_types") or [])
    serves   = int(data.get("serves") or 0)
    status   = "matched" if matched_ngo_id else "pending"

    sb = get_supabase()
    if sb:
        row = sb.table("donations").insert({
            "user_id":     None,  # Not used in this app
            "donor_name":  data.get("donor_name"),
            "phone":       data.get("phone"),
            "pincode":     data.get("pincode"),
            "food_types":  food_str,
            "food_name":   food_str or "Food donation",  # Ensure food_name is not null
            "quantity":    data.get("quantity"),
            "serves":      serves,
            "prepared_at": data.get("prepared_at"),
            "best_before": data.get("best_before"),
            "expiry_time": data.get("best_before") or "23:59",  # Ensure expiry_time is not null
            "address":     data.get("address"),
            "latitude":    data.get("lat"),  # Map lat to latitude
            "longitude":   data.get("lng"),  # Map lng to longitude
            "status":      status,
            "matched_ngo": str(matched_ngo_id) if matched_ngo_id else None,
        }).execute()
        donation_id = row.data[0]["id"]
        # Update impact via Supabase RPC
        sb.rpc("increment_impact", {"p_serves": serves, "p_co2": serves * 2.5}).execute()
        return donation_id
    else:
        conn = get_sqlite(db_path)
        cur = conn.execute(
            """insert into donations
               (donor_name,phone,pincode,food_types,quantity,serves,
                prepared_at,best_before,address,lat,lng,status,matched_ngo)
               values(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data.get("donor_name"), data.get("phone"), data.get("pincode"),
             food_str, data.get("quantity"), serves,
             data.get("prepared_at"), data.get("best_before"),
             data.get("address"), data.get("lat"), data.get("lng"),
             status, matched_ngo_id),
        )
        conn.execute(
            """update impact set meals_today=meals_today+?, meals_total=meals_total+?,
               co2_saved_kg=co2_saved_kg+? where id=1""",
            (serves, serves, serves * 2.5),
        )
        conn.commit()
        did = cur.lastrowid
        conn.close()
        return did


def get_donation(donation_id, db_path=None) -> Optional[dict]:
    sb = get_supabase()
    if sb:
        r = sb.table("donations").select("*").eq("id", str(donation_id)).maybe_single().execute()
        if not r.data:
            return None
        d = dict(r.data)
        # Manually fetch NGO name to avoid PostgREST join issues
        if d.get("matched_ngo"):
            ngo_r = sb.table("ngos").select("name,area").eq("id", str(d["matched_ngo"])).maybe_single().execute()
            if ngo_r.data:
                d["ngo_name"] = ngo_r.data.get("name")
                d["ngo_area"] = ngo_r.data.get("area")
        return d
    conn = get_sqlite(db_path)
    row = conn.execute(
        "select d.*,n.name as ngo_name,n.area as ngo_area from donations d left join ngos n on n.id=d.matched_ngo where d.id=?",
        (donation_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_donations(status=None, limit=50, db_path=None) -> list[dict]:
    sb = get_supabase()
    if sb:
        q = sb.table("donations").select("*").order("created_at", desc=True).limit(limit)
        if status:
            q = q.eq("status", status)
        return q.execute().data or []
    conn = get_sqlite(db_path)
    if status:
        rows = conn.execute(
            "select d.*,n.name as ngo_name from donations d left join ngos n on n.id=d.matched_ngo where d.status=? order by d.created_at desc limit ?",
            (status, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "select d.*,n.name as ngo_name from donations d left join ngos n on n.id=d.matched_ngo order by d.created_at desc limit ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_donation_status(donation_id, new_status: str, db_path=None) -> bool:
    valid = {"pending", "matched", "completed", "expired"}
    if new_status not in valid:
        return False
    sb = get_supabase()
    if sb:
        sb.table("donations").update({"status": new_status}).eq("id", str(donation_id)).execute()
        return True
    conn = get_sqlite(db_path)
    conn.execute("update donations set status=?,updated_at=datetime('now') where id=?", (new_status, donation_id))
    conn.commit()
    conn.close()
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  NGOs
# ─────────────────────────────────────────────────────────────────────────────

def list_ngos(db_path=None) -> list[dict]:
    sb = get_supabase()
    if sb:
        return sb.table("ngos").select("*").execute().data or []
    conn = get_sqlite(db_path)
    rows = conn.execute("select * from ngos order by name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ngo(ngo_id, db_path=None) -> Optional[dict]:
    sb = get_supabase()
    if sb:
        r = sb.table("ngos").select("*").eq("id", str(ngo_id)).single().execute()
        return r.data
    conn = get_sqlite(db_path)
    row = conn.execute("select * from ngos where id=?", (ngo_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ─────────────────────────────────────────────────────────────────────────────
#  IMPACT STATS
# ─────────────────────────────────────────────────────────────────────────────

def get_impact_stats(db_path=None) -> dict:
    sb = get_supabase()
    if sb:
        impact = sb.table("impact").select("*").eq("id", 1).single().execute().data or {}
        active = sb.table("donations").select("id", count="exact").in_("status", ["pending", "matched"]).execute().count
        recent = sb.table("donations").select("*").order("created_at", desc=True).limit(10).execute().data or []
        ngos   = sb.table("ngos").select("*").execute().data or []
    else:
        conn   = get_sqlite(db_path)
        impact = dict(conn.execute("select * from impact where id=1").fetchone() or {})
        active = conn.execute("select count(*) from donations where status in ('pending','matched')").fetchone()[0]
        recent = [dict(r) for r in conn.execute(
            "select d.*,n.name as ngo_name from donations d left join ngos n on n.id=d.matched_ngo order by d.created_at desc limit 10"
        ).fetchall()]
        ngos   = [dict(r) for r in conn.execute("select * from ngos").fetchall()]
        conn.close()

    return {
        **impact,
        "co2_saved_kg":     round(float(impact.get("co2_saved_kg", 0))),
        "active_donations": active,
        "recent_donations": recent,
        "ngos":             ngos,
        "db_backend":       "supabase" if sb else "sqlite",
    }
