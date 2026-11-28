"""Local SQLite persistence for Leanbot detections and review decisions."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

DB_PATH = Path(__file__).resolve().parent / "veritas.sqlite3"
CAPTURE_DIR = Path(__file__).resolve().parent / "captures"


def connect():
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def _capture_file(image_url):
    """Resolve only filenames beneath captures; never trust paths from a client."""
    if not image_url:
        return None
    filename = Path(unquote(urlparse(str(image_url)).path)).name
    if not filename or filename in {".", ".."} or Path(filename).suffix.lower() not in {".jpg", ".jpeg"}:
        return None
    path = (CAPTURE_DIR / filename).resolve()
    if path.parent != CAPTURE_DIR.resolve() or not path.is_file():
        return None
    return path


def _read_capture(image_url):
    path = _capture_file(image_url)
    if path is None:
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


def _merge_violations(existing_json, incoming):
    try:
        merged = json.loads(existing_json or "[]")
    except (TypeError, json.JSONDecodeError):
        merged = []
    if not isinstance(merged, list):
        merged = []
    if not isinstance(incoming, list):
        incoming = []
    for violation in incoming:
        if violation not in merged:
            merged.append(violation)
    return merged


def initialize():
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS leanbots (
            id TEXT PRIMARY KEY, plate TEXT, last_zone TEXT, approval TEXT NOT NULL DEFAULT 'pending',
            last_seen TEXT, evidence_url TEXT, violations_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            evidence_blob BLOB, evidence_mime TEXT
        )""")
        # Add the image columns to databases created by older versions.
        columns = {row["name"] for row in db.execute("PRAGMA table_info(leanbots)")}
        if "evidence_blob" not in columns:
            db.execute("ALTER TABLE leanbots ADD COLUMN evidence_blob BLOB")
        if "evidence_mime" not in columns:
            db.execute("ALTER TABLE leanbots ADD COLUMN evidence_mime TEXT")

        # Backfill existing approved records from their capture files when possible.
        rows = db.execute(
            "SELECT id, evidence_url FROM leanbots WHERE evidence_blob IS NULL AND evidence_url IS NOT NULL"
        ).fetchall()
        for row in rows:
            image_blob = _read_capture(row["evidence_url"])
            if image_blob:
                db.execute(
                    "UPDATE leanbots SET evidence_blob = ?, evidence_mime = 'image/jpeg' WHERE id = ?",
                    (image_blob, row["id"]),
                )

        # This is the final database: candidates and rejected detections are not retained.
        db.execute("DELETE FROM leanbots WHERE approval <> 'approved'")


def save_approved(bot):
    capture = bot.get("license_plate_capture") or {}
    zone = bot.get("current_zone")
    if isinstance(zone, dict):
        zone = zone.get("name") or zone.get("type")
    leanbot_id = str(bot.get("id") or "").strip()
    if not leanbot_id:
        raise ValueError("Leanbot id is required")
    plate = bot.get("license_plate")
    # The broker currently uses a boolean to mark plate presence; only persist actual text.
    if not isinstance(plate, str):
        plate = None
    else:
        plate = plate.strip() or None

    evidence_url = capture.get("image_url")
    image_blob = _read_capture(evidence_url)
    if image_blob is None:
        evidence_url = None

    incoming_violations = bot.get("violations") or []
    with connect() as db:
        # Serialize approvals for the same Leanbot so retries merge cleanly.
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT violations_json FROM leanbots WHERE id = ?",
            (leanbot_id,),
        ).fetchone()
        violations = _merge_violations(
            existing["violations_json"] if existing else "[]",
            incoming_violations,
        )
        db.execute("""INSERT INTO leanbots
            (id, plate, last_zone, approval, last_seen, evidence_url, violations_json, evidence_blob, evidence_mime)
            VALUES (?, ?, ?, 'approved', ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET plate=COALESCE(excluded.plate, leanbots.plate), last_zone=excluded.last_zone,
            approval='approved', last_seen=excluded.last_seen,
            evidence_url=COALESCE(excluded.evidence_url, leanbots.evidence_url),
            violations_json=excluded.violations_json,
            evidence_blob=COALESCE(excluded.evidence_blob, leanbots.evidence_blob),
            evidence_mime=COALESCE(excluded.evidence_mime, leanbots.evidence_mime),
            updated_at=CURRENT_TIMESTAMP""",
            (leanbot_id, plate, zone,
             str(bot.get("last_seen") or datetime.now(timezone.utc).isoformat()),
             evidence_url, json.dumps(violations), image_blob,
             "image/jpeg" if image_blob else None))


def list_records():
    with connect() as db:
        rows = db.execute("""SELECT id AS leanbot_id, plate, last_zone, approval, last_seen,
            CASE WHEN evidence_blob IS NOT NULL
                THEN '/api/database/leanbots/' || id || '/plate-image'
                ELSE NULL END AS evidence_url,
            violations_json
            FROM leanbots ORDER BY updated_at DESC""").fetchall()
        return [dict(row) for row in rows]


def update_plate(leanbot_id, plate):
    with connect() as db:
        cursor = db.execute(
            "UPDATE leanbots SET plate = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND approval = 'approved'",
            (plate, str(leanbot_id)),
        )
        return cursor.rowcount > 0


def append_approved_violations(leanbots):
    """Append new violation types to approved, plate-identified Leanbots only."""
    if not isinstance(leanbots, list):
        return 0
    changed = 0
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        for bot in leanbots:
            if not isinstance(bot, dict):
                continue
            leanbot_id = str(bot.get("id") or "").strip()
            incoming = bot.get("violations")
            if not leanbot_id or not isinstance(incoming, list) or not incoming:
                continue
            existing = db.execute(
                "SELECT violations_json FROM leanbots WHERE id = ? AND approval = 'approved' AND plate IS NOT NULL AND trim(plate) <> ''",
                (leanbot_id,),
            ).fetchone()
            if existing is None:
                continue
            merged = _merge_violations(existing["violations_json"], incoming)
            try:
                previous = json.loads(existing["violations_json"] or "[]")
            except (TypeError, json.JSONDecodeError):
                previous = []
            if merged == previous:
                continue
            db.execute(
                "UPDATE leanbots SET violations_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(merged), leanbot_id),
            )
            changed += 1
    return changed


def get_plate_image(leanbot_id):
    with connect() as db:
        row = db.execute(
            "SELECT evidence_blob, evidence_mime FROM leanbots WHERE id = ? AND approval = 'approved'",
            (str(leanbot_id),),
        ).fetchone()
    if row is None or row["evidence_blob"] is None:
        return None
    return bytes(row["evidence_blob"]), row["evidence_mime"] or "image/jpeg"
