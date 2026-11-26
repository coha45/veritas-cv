"""Local SQLite persistence for Leanbot detections and review decisions."""
import json
import sqlite3
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

def upsert_detections(records):
    with connect() as db:
        for bot in records:
            capture = bot.get("license_plate_capture") or {}
            zone = bot.get("current_zone")
            if isinstance(zone, dict): zone = zone.get("name") or zone.get("type")
            db.execute("""INSERT INTO leanbots
                (id, plate, last_zone, last_seen, evidence_url, violations_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET last_zone=excluded.last_zone,
                last_seen=excluded.last_seen, evidence_url=COALESCE(excluded.evidence_url, leanbots.evidence_url),
                violations_json=excluded.violations_json, updated_at=CURRENT_TIMESTAMP""",
                (str(bot.get("id")), bot.get("license_plate"), zone,
                 str(bot.get("last_seen") or ""), capture.get("image_url"),
                 json.dumps(bot.get("violations") or [])))

def list_records():
    with connect() as db:
        return [dict(row) for row in db.execute(
            "SELECT id AS leanbot_id, plate, last_zone, approval, last_seen, evidence_url, violations_json FROM leanbots ORDER BY updated_at DESC")]

def set_approval(leanbot_id, approval):
    with connect() as db:
        result = db.execute("UPDATE leanbots SET approval=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (approval, str(leanbot_id)))
        return result.rowcount > 0
