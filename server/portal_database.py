"""SQLite-backed driver and portal-administration data."""
import hashlib
import hmac
import json
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone

from database import DB_PATH

PASSWORD_ITERATIONS = 310_000
SESSION_SECONDS = 6 * 60 * 60


def connect():
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize():
    with connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS portal_users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                phone TEXT,
                role TEXT NOT NULL DEFAULT 'driver' CHECK(role IN ('driver', 'admin')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS portal_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES portal_users(id) ON DELETE CASCADE,
                expires_at REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS portal_sessions_user_idx ON portal_sessions(user_id);
            CREATE TABLE IF NOT EXISTS portal_vehicles (
                id TEXT PRIMARY KEY,
                owner_user_id TEXT NOT NULL REFERENCES portal_users(id) ON DELETE CASCADE,
                plate_number TEXT NOT NULL,
                plate_key TEXT NOT NULL,
                vehicle_type TEXT NOT NULL,
                make TEXT,
                model TEXT,
                year TEXT,
                color TEXT,
                or_number TEXT NOT NULL,
                cr_number TEXT NOT NULL,
                registration_expiry TEXT,
                verification_status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(verification_status IN ('pending', 'verified', 'rejected')),
                remarks TEXT,
                reviewed_by TEXT REFERENCES portal_users(id),
                decided_at TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(owner_user_id, plate_key)
            );
            CREATE INDEX IF NOT EXISTS portal_vehicles_status_idx ON portal_vehicles(verification_status, created_at);
            CREATE TABLE IF NOT EXISTS portal_disputes (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES portal_users(id) ON DELETE CASCADE,
                leanbot_id TEXT NOT NULL,
                violation_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'under_review', 'upheld', 'dismissed')),
                staff_note TEXT,
                reviewed_by TEXT REFERENCES portal_users(id),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, leanbot_id, violation_type)
            );
            CREATE TABLE IF NOT EXISTS portal_fines (
                violation_type TEXT PRIMARY KEY,
                amount REAL NOT NULL DEFAULT 0 CHECK(amount >= 0),
                currency TEXT NOT NULL DEFAULT 'PHP',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        db.execute("DELETE FROM portal_sessions WHERE expires_at <= ?", (datetime.now(timezone.utc).timestamp(),))


def _password_hash(password):
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        salt.hex(),
        derived.hex(),
    )


def _verify_password(password, saved_hash):
    try:
        algorithm, iterations, salt_hex, expected = saved_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _user_dict(row):
    return {key: row[key] for key in ("id", "email", "first_name", "last_name", "phone", "role")}


def _create_session(db, user_id):
    token = secrets.token_urlsafe(36)
    expires_at = datetime.now(timezone.utc).timestamp() + SESSION_SECONDS
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db.execute(
        "INSERT INTO portal_sessions(token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (token_hash, user_id, expires_at),
    )
    return token


def signup(email, password, first_name, last_name, phone=""):
    email = str(email or "").strip().lower()
    first_name = str(first_name or "").strip()
    last_name = str(last_name or "").strip()
    phone = str(phone or "").strip()
    if "@" not in email or len(email) > 254:
        raise ValueError("Enter a valid email address")
    if len(password or "") < 10:
        raise ValueError("Use a password with at least 10 characters")
    if not first_name or not last_name:
        raise ValueError("First and last name are required")
    if len(first_name) > 80 or len(last_name) > 80 or len(phone) > 40:
        raise ValueError("One or more profile fields are too long")

    user_id = str(uuid.uuid4())
    try:
        with connect() as db:
            db.execute(
                "INSERT INTO portal_users(id, email, password_hash, first_name, last_name, phone) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, email, _password_hash(password), first_name, last_name, phone),
            )
            token = _create_session(db, user_id)
            user = _user_dict(db.execute("SELECT * FROM portal_users WHERE id = ?", (user_id,)).fetchone())
    except sqlite3.IntegrityError as error:
        raise ValueError("An account with this email already exists") from error
    return token, user


def login(email, password):
    with connect() as db:
        row = db.execute("SELECT * FROM portal_users WHERE email = ? COLLATE NOCASE", (str(email or "").strip(),)).fetchone()
        if row is None or not _verify_password(str(password or ""), row["password_hash"]):
            raise ValueError("Email or password is incorrect")
        token = _create_session(db, row["id"])
        return token, _user_dict(row)


def authenticate(token):
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).timestamp()
    with connect() as db:
        row = db.execute("""SELECT u.* FROM portal_sessions s JOIN portal_users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ?""", (token_hash, now)).fetchone()
        if row is None:
            db.execute("DELETE FROM portal_sessions WHERE token_hash = ? OR expires_at <= ?", (token_hash, now))
            return None
        return _user_dict(row)


def logout(token):
    if token:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with connect() as db:
            db.execute("DELETE FROM portal_sessions WHERE token_hash = ?", (token_hash,))


def update_profile(user_id, first_name, last_name, phone):
    first_name, last_name, phone = (str(value or "").strip() for value in (first_name, last_name, phone))
    if not first_name or not last_name:
        raise ValueError("First and last name are required")
    if len(first_name) > 80 or len(last_name) > 80 or len(phone) > 40:
        raise ValueError("One or more profile fields are too long")
    with connect() as db:
        db.execute("UPDATE portal_users SET first_name = ?, last_name = ?, phone = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (first_name, last_name, phone, user_id))
        return _user_dict(db.execute("SELECT * FROM portal_users WHERE id = ?", (user_id,)).fetchone())


def change_password(user_id, current_password, new_password):
    if len(new_password or "") < 10:
        raise ValueError("Use a password with at least 10 characters")
    with connect() as db:
        row = db.execute("SELECT password_hash FROM portal_users WHERE id = ?", (user_id,)).fetchone()
        if row is None or not _verify_password(str(current_password or ""), row["password_hash"]):
            raise ValueError("Current password is incorrect")
        db.execute("UPDATE portal_users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (_password_hash(new_password), user_id))
        db.execute("DELETE FROM portal_sessions WHERE user_id = ?", (user_id,))
        return _create_session(db, user_id)


def _plate_key(value):
    return "".join(str(value or "").upper().split())


def _vehicle_dict(row):
    return dict(row)


def list_vehicles(user_id):
    with connect() as db:
        rows = db.execute("SELECT * FROM portal_vehicles WHERE owner_user_id = ? AND active = 1 ORDER BY created_at DESC", (user_id,)).fetchall()
        return [_vehicle_dict(row) for row in rows]


def add_vehicle(user_id, data):
    plate = " ".join(str(data.get("plate_number") or "").upper().split())
    plate_key = _plate_key(plate)
    vehicle_type = str(data.get("vehicle_type") or "").strip()
    or_number = str(data.get("or_number") or "").strip()
    cr_number = str(data.get("cr_number") or "").strip()
    if not plate_key or not vehicle_type or not or_number or not cr_number:
        raise ValueError("Plate, vehicle type, OR number and CR number are required")
    if len(plate) > 24 or len(or_number) > 80 or len(cr_number) > 80:
        raise ValueError("One or more vehicle fields are too long")
    values = (
        vehicle_type,
        str(data.get("make") or "").strip()[:80],
        str(data.get("model") or "").strip()[:80],
        str(data.get("year") or "").strip()[:8],
        str(data.get("color") or "").strip()[:40],
        or_number,
        cr_number,
        str(data.get("registration_expiry") or "").strip()[:20] or None,
    )
    with connect() as db:
        existing = db.execute("SELECT * FROM portal_vehicles WHERE owner_user_id = ? AND plate_key = ?", (user_id, plate_key)).fetchone()
        if existing:
            if existing["verification_status"] != "rejected":
                raise ValueError("This plate already has an active registration request")
            db.execute("""UPDATE portal_vehicles SET plate_number=?, vehicle_type=?, make=?, model=?, year=?, color=?,
                or_number=?, cr_number=?, registration_expiry=?, verification_status='pending', remarks=NULL,
                reviewed_by=NULL, decided_at=NULL, active=1, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (plate, *values, existing["id"]))
            return _vehicle_dict(db.execute("SELECT * FROM portal_vehicles WHERE id = ?", (existing["id"],)).fetchone())
        vehicle_id = str(uuid.uuid4())
        db.execute("""INSERT INTO portal_vehicles
            (id, owner_user_id, plate_number, plate_key, vehicle_type, make, model, year, color, or_number, cr_number, registration_expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (vehicle_id, user_id, plate, plate_key, *values))
        return _vehicle_dict(db.execute("SELECT * FROM portal_vehicles WHERE id = ?", (vehicle_id,)).fetchone())


def remove_vehicle(user_id, vehicle_id):
    with connect() as db:
        cursor = db.execute("UPDATE portal_vehicles SET active=0, updated_at=CURRENT_TIMESTAMP WHERE id=? AND owner_user_id=? AND active=1", (vehicle_id, user_id))
        return cursor.rowcount > 0


def admin_vehicles(status="pending"):
    with connect() as db:
        if status in {"pending", "verified", "rejected"}:
            rows = db.execute("""SELECT v.*, u.email AS owner_email, u.first_name AS owner_first_name,
                u.last_name AS owner_last_name, u.phone AS owner_phone FROM portal_vehicles v
                JOIN portal_users u ON u.id=v.owner_user_id WHERE v.active=1 AND v.verification_status=? ORDER BY v.created_at""", (status,)).fetchall()
        else:
            rows = db.execute("""SELECT v.*, u.email AS owner_email, u.first_name AS owner_first_name,
                u.last_name AS owner_last_name, u.phone AS owner_phone FROM portal_vehicles v
                JOIN portal_users u ON u.id=v.owner_user_id WHERE v.active=1 ORDER BY v.created_at DESC""").fetchall()
        return [_vehicle_dict(row) for row in rows]


def decide_vehicle(admin_id, vehicle_id, decision, remarks=""):
    decision = str(decision or "").lower()
    remarks = str(remarks or "").strip()
    if decision not in {"verified", "rejected"}:
        raise ValueError("Decision must be verified or rejected")
    if decision == "rejected" and not remarks:
        raise ValueError("Add a reason when rejecting a registration")
    with connect() as db:
        if decision == "verified":
            duplicate = db.execute("""SELECT v.id FROM portal_vehicles v
                JOIN portal_vehicles target ON target.id=?
                WHERE v.plate_key=target.plate_key AND v.active=1
                  AND v.verification_status='verified' AND v.id<>target.id LIMIT 1""", (vehicle_id,)).fetchone()
            if duplicate is not None:
                raise ValueError("This plate is already linked to another verified account")
        cursor = db.execute("""UPDATE portal_vehicles SET verification_status=?, remarks=?, reviewed_by=?,
            decided_at=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND active=1""",
            (decision, remarks or None, admin_id, datetime.now(timezone.utc).isoformat(), vehicle_id))
        if cursor.rowcount == 0:
            return None
        return _vehicle_dict(db.execute("SELECT * FROM portal_vehicles WHERE id=?", (vehicle_id,)).fetchone())


def _violation_rows(db, vehicle_owner=None, only_unassigned=False):
    verified = db.execute("""SELECT owner_user_id, plate_key FROM portal_vehicles
        WHERE active=1 AND verification_status='verified'""").fetchall()
    owners_by_plate = {row["plate_key"]: row["owner_user_id"] for row in verified}
    bots = db.execute("""SELECT id, plate, last_zone, last_seen, violations_json FROM leanbots
        WHERE approval='approved' AND plate IS NOT NULL AND trim(plate) <> '' ORDER BY last_seen DESC""").fetchall()
    fines = {row["violation_type"]: (row["amount"], row["currency"]) for row in db.execute("SELECT * FROM portal_fines")}
    disputes = {(row["leanbot_id"], row["violation_type"]): row for row in db.execute("SELECT * FROM portal_disputes")}
    result = []
    for bot in bots:
        key = _plate_key(bot["plate"])
        owner = owners_by_plate.get(key)
        if vehicle_owner is not None and owner != vehicle_owner:
            continue
        if only_unassigned and owner is not None:
            continue
        try:
            violation_types = json.loads(bot["violations_json"] or "[]")
        except (TypeError, json.JSONDecodeError):
            violation_types = []
        if not isinstance(violation_types, list):
            continue
        for violation_type in violation_types:
            violation_type = str(violation_type)
            amount, currency = fines.get(violation_type, (None, "PHP"))
            dispute = disputes.get((bot["id"], violation_type))
            dispute_status = dispute["status"] if dispute else None
            if dispute_status in {"pending", "under_review"}:
                status = "Under dispute" if dispute_status == "pending" else "Dispute under review"
            elif dispute_status == "upheld":
                status = "Dispute upheld"
            elif dispute_status == "dismissed":
                status = "Dispute dismissed"
            else:
                status = "Recorded"
            result.append({
                "violation_id": f"{bot['id']}:{violation_type}",
                "leanbot_id": bot["id"],
                "plate_number": bot["plate"],
                "violation_type": violation_type,
                "location": bot["last_zone"],
                "occurred_at": bot["last_seen"],
                "status": status,
                "dispute_status": dispute_status,
                "dispute_note": dispute["reason"] if dispute else None,
                "amount": amount,
                "currency": currency,
                "owner_user_id": owner,
            })
    return result


def user_violations(user_id):
    with connect() as db:
        return _violation_rows(db, vehicle_owner=user_id)


def unassigned_violations():
    with connect() as db:
        return _violation_rows(db, only_unassigned=True)


def create_dispute(user_id, leanbot_id, violation_type, reason):
    reason = str(reason or "").strip()
    if len(reason) < 10 or len(reason) > 2000:
        raise ValueError("Explain the dispute in 10 to 2000 characters")
    with connect() as db:
        violation = next((item for item in _violation_rows(db, vehicle_owner=user_id)
                          if item["leanbot_id"] == str(leanbot_id) and item["violation_type"] == str(violation_type)), None)
        if violation is None:
            raise ValueError("That violation is not linked to one of your verified vehicles")
        dispute_id = str(uuid.uuid4())
        try:
            db.execute("INSERT INTO portal_disputes(id, user_id, leanbot_id, violation_type, reason) VALUES (?, ?, ?, ?, ?)",
                       (dispute_id, user_id, str(leanbot_id), str(violation_type), reason))
        except sqlite3.IntegrityError as error:
            raise ValueError("A dispute has already been submitted for this violation") from error
        return dict(db.execute("SELECT * FROM portal_disputes WHERE id=?", (dispute_id,)).fetchone())


def admin_disputes():
    with connect() as db:
        rows = db.execute("""SELECT d.*, u.email AS user_email, u.first_name, u.last_name, l.plate AS plate_number,
            l.last_zone AS location, l.last_seen AS occurred_at FROM portal_disputes d
            JOIN portal_users u ON u.id=d.user_id LEFT JOIN leanbots l ON l.id=d.leanbot_id
            ORDER BY d.created_at DESC""").fetchall()
        return [dict(row) for row in rows]


def decide_dispute(admin_id, dispute_id, status, staff_note=""):
    status = str(status or "").lower()
    if status not in {"under_review", "upheld", "dismissed"}:
        raise ValueError("Choose under review, upheld, or dismissed")
    with connect() as db:
        cursor = db.execute("""UPDATE portal_disputes SET status=?, staff_note=?, reviewed_by=?,
            updated_at=CURRENT_TIMESTAMP WHERE id=?""", (status, str(staff_note or "").strip() or None, admin_id, dispute_id))
        if not cursor.rowcount:
            return None
        return dict(db.execute("SELECT * FROM portal_disputes WHERE id=?", (dispute_id,)).fetchone())


def list_fines():
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM portal_fines ORDER BY violation_type")]


def set_fine(violation_type, amount, currency="PHP"):
    violation_type = str(violation_type or "").strip()
    try:
        amount = float(amount)
    except (ValueError, TypeError) as error:
        raise ValueError("Enter a valid fine amount") from error
    if not violation_type or amount < 0 or amount > 10_000_000:
        raise ValueError("Enter a violation type and a non-negative amount")
    with connect() as db:
        db.execute("""INSERT INTO portal_fines(violation_type, amount, currency) VALUES (?, ?, ?)
            ON CONFLICT(violation_type) DO UPDATE SET amount=excluded.amount, currency=excluded.currency, updated_at=CURRENT_TIMESTAMP""",
            (violation_type, amount, str(currency or "PHP").upper()[:3]))
        return dict(db.execute("SELECT * FROM portal_fines WHERE violation_type=?", (violation_type,)).fetchone())


def list_payments(user_id=None):
    # No payment provider is configured; never imply that a payment was processed.
    return []
