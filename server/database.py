"""Local SQLite persistence for Leanbot detections and review decisions."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "veritas.sqlite3"

def connect():
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    return db

def initialize():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS leanbots (
            id TEXT PRIMARY KEY, plate TEXT, last_zone TEXT, approval TEXT NOT NULL DEFAULT 'pending',
            last_seen TEXT, evidence_url TEXT, violations_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        # This is the final database: candidates and rejected detections are not retained.
        db.execute("DELETE FROM leanbots WHERE approval <> 'approved'")

def save_approved(bot):
    capture = bot.get("license_plate_capture") or {}
    zone = bot.get("current_zone")
    if isinstance(zone, dict): zone = zone.get("name") or zone.get("type")
    leanbot_id = str(bot.get("id") or "").strip()
    if not leanbot_id:
        raise ValueError("Leanbot id is required")
    with connect() as db:
        db.execute("""INSERT INTO leanbots
            (id, plate, last_zone, approval, last_seen, evidence_url, violations_json)
            VALUES (?, ?, ?, 'approved', ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET plate=excluded.plate, last_zone=excluded.last_zone,
            approval='approved', last_seen=excluded.last_seen, evidence_url=excluded.evidence_url,
            violations_json=excluded.violations_json, updated_at=CURRENT_TIMESTAMP""",
            (leanbot_id, bot.get("license_plate"), zone,
             str(bot.get("last_seen") or datetime.now(timezone.utc).isoformat()),
             capture.get("image_url"), json.dumps(bot.get("violations") or [])))

def list_records():
    with connect() as db:
        return [dict(row) for row in db.execute(
            "SELECT id AS leanbot_id, plate, last_zone, approval, last_seen, evidence_url, violations_json FROM leanbots ORDER BY updated_at DESC")]

