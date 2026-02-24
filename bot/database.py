"""SQLite database manager with WAL mode and async support."""
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from threading import Lock
from typing import Any

from bot.config import get_settings, DATA_DIR

logger = logging.getLogger(__name__)

_lock = Lock()
_conn: sqlite3.Connection | None = None


def _db_path() -> str:
    rel = get_settings().get("database", {}).get("path", "data/aiabot.db")
    if os.path.isabs(rel):
        return rel
    return os.path.join(DATA_DIR, os.path.basename(rel))


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        path = _db_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _conn = sqlite3.connect(path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _conn.execute("PRAGMA synchronous=NORMAL")
        _conn.commit()
    return _conn


@contextmanager
def get_cursor():
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def init_db():
    """Create all tables if they don't exist."""
    schema = """
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        display_name TEXT,
        role TEXT NOT NULL DEFAULT 'admin',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        phone TEXT,
        is_blocked INTEGER NOT NULL DEFAULT 0,
        first_seen TEXT DEFAULT (datetime('now')),
        last_active TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        event_date TEXT,
        event_time TEXT,
        location TEXT,
        capacity INTEGER NOT NULL DEFAULT 0,
        current_registrations INTEGER NOT NULL DEFAULT 0,
        price INTEGER NOT NULL DEFAULT 0,
        certificate_fee INTEGER NOT NULL DEFAULT 0,
        is_paid INTEGER NOT NULL DEFAULT 0,
        is_university_only INTEGER NOT NULL DEFAULT 0,
        waitlist_enabled INTEGER NOT NULL DEFAULT 0,
        max_waitlist INTEGER NOT NULL DEFAULT 0,
        required_fields TEXT NOT NULL DEFAULT '[]',
        optional_fields TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'draft',
        registration_open INTEGER NOT NULL DEFAULT 0,
        reg_token TEXT UNIQUE,
        created_by INTEGER,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        event_id INTEGER NOT NULL REFERENCES events(id),
        full_name TEXT,
        student_id TEXT,
        national_code TEXT,
        email TEXT,
        phone TEXT,
        registration_type TEXT NOT NULL DEFAULT 'free',
        payment_amount INTEGER NOT NULL DEFAULT 0,
        payment_receipt_file_id TEXT,
        payment_status TEXT NOT NULL DEFAULT 'none',
        approval_status TEXT NOT NULL DEFAULT 'pending',
        approved_by INTEGER,
        approval_note TEXT,
        channel_member INTEGER NOT NULL DEFAULT 0,
        is_waitlist INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, event_id)
    );

    CREATE TABLE IF NOT EXISTS event_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL REFERENCES events(id),
        media_type TEXT NOT NULL,
        file_id TEXT,
        file_path TEXT,
        caption TEXT,
        display_order INTEGER NOT NULL DEFAULT 0,
        uploaded_by INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS broadcasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_text TEXT NOT NULL,
        target TEXT NOT NULL DEFAULT 'all',
        event_id INTEGER,
        media_file_id TEXT,
        media_type TEXT,
        sent_count INTEGER NOT NULL DEFAULT 0,
        failed_count INTEGER NOT NULL DEFAULT 0,
        sent_by INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS required_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id INTEGER NOT NULL,
        channel_username TEXT NOT NULL,
        channel_title TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        added_by INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS user_states (
        telegram_id INTEGER PRIMARY KEY,
        state TEXT NOT NULL,
        state_data TEXT NOT NULL DEFAULT '{}',
        updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        event_id INTEGER NOT NULL REFERENCES events(id),
        message TEXT NOT NULL,
        notification_type TEXT NOT NULL DEFAULT 'reminder',
        is_sent INTEGER NOT NULL DEFAULT 0,
        scheduled_at TEXT NOT NULL,
        sent_at TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
    CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
    CREATE INDEX IF NOT EXISTS idx_registrations_user_id ON registrations(user_id);
    CREATE INDEX IF NOT EXISTS idx_registrations_event_id ON registrations(event_id);
    CREATE INDEX IF NOT EXISTS idx_registrations_approval ON registrations(approval_status);
    CREATE INDEX IF NOT EXISTS idx_notifications_scheduled ON notifications(scheduled_at, is_sent);
    """
    with get_cursor() as cur:
        cur.executescript(schema)

    # Migrations for existing databases (safe to run multiple times)
    migrations = [
        "ALTER TABLE events ADD COLUMN slug TEXT",
        "ALTER TABLE broadcasts ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_slug ON events(slug)",
    ]
    for migration in migrations:
        try:
            with get_cursor() as cur:
                cur.execute(migration)
        except Exception as e:
            err = str(e).lower()
            if "duplicate column" not in err and "already exists" not in err:
                logger.warning("Migration warning (%s): %s", migration[:40], e)

    logger.info("Database initialized.")


# --- User helpers ---

def upsert_user(telegram_id: int, username: str | None,
                first_name: str | None, last_name: str | None) -> int:
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                last_active=datetime('now')
        """, (telegram_id, username, first_name, last_name))
        cur.execute("SELECT id FROM users WHERE telegram_id=?", (telegram_id,))
        row = cur.fetchone()
        return row["id"]


def get_user(telegram_id: int) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_all_users(approved_only: bool = False) -> list[dict]:
    with get_cursor() as cur:
        if approved_only:
            cur.execute("""
                SELECT DISTINCT u.* FROM users u
                JOIN registrations r ON r.user_id=u.id
                WHERE r.approval_status='approved' AND u.is_blocked=0
            """)
        else:
            cur.execute("SELECT * FROM users WHERE is_blocked=0")
        return [dict(r) for r in cur.fetchall()]


# --- Admin helpers ---

def upsert_admin(telegram_id: int, username: str | None,
                 display_name: str | None, role: str = "admin") -> None:
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO admins (telegram_id, username, display_name, role)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                display_name=excluded.display_name,
                role=excluded.role,
                updated_at=datetime('now')
        """, (telegram_id, username, display_name, role))


def get_admin(telegram_id: int) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM admins WHERE telegram_id=? AND is_active=1",
                    (telegram_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_all_admins() -> list[dict]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM admins WHERE is_active=1")
        return [dict(r) for r in cur.fetchall()]


def deactivate_admin(telegram_id: int) -> None:
    with get_cursor() as cur:
        cur.execute("UPDATE admins SET is_active=0 WHERE telegram_id=?",
                    (telegram_id,))


# --- Event helpers ---

def create_event(data: dict) -> int:
    import secrets
    token = secrets.token_urlsafe(16)
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO events
            (title, description, event_date, event_time, location, capacity,
             price, certificate_fee, is_paid, is_university_only,
             waitlist_enabled, max_waitlist, required_fields, optional_fields,
             status, registration_open, reg_token, created_by, slug)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("title"), data.get("description"),
            data.get("event_date"), data.get("event_time"),
            data.get("location"), data.get("capacity", 0),
            data.get("price", 0), data.get("certificate_fee", 0),
            int(data.get("is_paid", False)), int(data.get("is_university_only", False)),
            int(data.get("waitlist_enabled", False)), data.get("max_waitlist", 0),
            json.dumps(data.get("required_fields", [])),
            json.dumps(data.get("optional_fields", [])),
            data.get("status", "draft"),
            int(data.get("registration_open", False)),
            token, data.get("created_by"),
            data.get("slug") or None,
        ))
        return cur.lastrowid


def update_event(event_id: int, data: dict) -> None:
    fields = []
    values = []
    allowed = ["title", "description", "event_date", "event_time", "location",
                "capacity", "price", "certificate_fee", "is_paid",
                "is_university_only", "waitlist_enabled", "max_waitlist",
                "status", "registration_open", "slug"]
    for key in allowed:
        if key in data:
            fields.append(f"{key}=?")
            values.append(data[key] if key != "slug" else (data[key] or None))
    if "required_fields" in data:
        fields.append("required_fields=?")
        values.append(json.dumps(data["required_fields"]))
    if "optional_fields" in data:
        fields.append("optional_fields=?")
        values.append(json.dumps(data["optional_fields"]))
    fields.append("updated_at=datetime('now')")
    values.append(event_id)
    with get_cursor() as cur:
        cur.execute(f"UPDATE events SET {', '.join(fields)} WHERE id=?", values)


def delete_event(event_id: int) -> None:
    with get_cursor() as cur:
        cur.execute("DELETE FROM events WHERE id=?", (event_id,))


def get_event(event_id: int) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM events WHERE id=?", (event_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["required_fields"] = json.loads(d["required_fields"] or "[]")
        d["optional_fields"] = json.loads(d["optional_fields"] or "[]")
        return d


def get_event_by_token(token: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM events WHERE reg_token=?", (token,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["required_fields"] = json.loads(d["required_fields"] or "[]")
        d["optional_fields"] = json.loads(d["optional_fields"] or "[]")
        return d


def get_event_by_slug(slug: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM events WHERE slug=?", (slug,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["required_fields"] = json.loads(d["required_fields"] or "[]")
        d["optional_fields"] = json.loads(d["optional_fields"] or "[]")
        return d


def get_active_events() -> list[dict]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM events WHERE status='active' ORDER BY event_date")
        rows = cur.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["required_fields"] = json.loads(d["required_fields"] or "[]")
            d["optional_fields"] = json.loads(d["optional_fields"] or "[]")
            result.append(d)
        return result


def get_archived_events() -> list[dict]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM events WHERE status='archived' ORDER BY event_date DESC")
        rows = cur.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["required_fields"] = json.loads(d["required_fields"] or "[]")
            d["optional_fields"] = json.loads(d["optional_fields"] or "[]")
            result.append(d)
        return result


def get_all_events() -> list[dict]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM events ORDER BY created_at DESC")
        rows = cur.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["required_fields"] = json.loads(d["required_fields"] or "[]")
            d["optional_fields"] = json.loads(d["optional_fields"] or "[]")
            result.append(d)
        return result


def increment_registration_count(event_id: int) -> None:
    with get_cursor() as cur:
        cur.execute(
            "UPDATE events SET current_registrations=current_registrations+1 WHERE id=?",
            (event_id,)
        )


# --- Registration helpers ---

def create_registration(data: dict) -> int:
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO registrations
            (user_id, event_id, full_name, student_id, national_code,
             email, phone, registration_type, payment_amount,
             payment_receipt_file_id, payment_status, is_waitlist)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["user_id"], data["event_id"],
            data.get("full_name"), data.get("student_id"),
            data.get("national_code"), data.get("email"), data.get("phone"),
            data.get("registration_type", "free"),
            data.get("payment_amount", 0),
            data.get("payment_receipt_file_id"),
            data.get("payment_status", "none"),
            int(data.get("is_waitlist", False)),
        ))
        return cur.lastrowid


def get_registration(reg_id: int) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM registrations WHERE id=?", (reg_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_registration(user_id: int, event_id: int) -> dict | None:
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM registrations WHERE user_id=? AND event_id=?",
            (user_id, event_id)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_event_registrations(event_id: int) -> list[dict]:
    with get_cursor() as cur:
        cur.execute("""
            SELECT r.*, u.telegram_id, u.username, u.first_name, u.last_name
            FROM registrations r
            JOIN users u ON r.user_id=u.id
            WHERE r.event_id=?
            ORDER BY r.created_at
        """, (event_id,))
        return [dict(row) for row in cur.fetchall()]


def update_registration(reg_id: int, data: dict) -> None:
    fields = []
    values = []
    allowed = ["payment_status", "approval_status", "approved_by",
                "approval_note", "channel_member", "payment_receipt_file_id"]
    for key in allowed:
        if key in data:
            fields.append(f"{key}=?")
            values.append(data[key])
    fields.append("updated_at=datetime('now')")
    values.append(reg_id)
    with get_cursor() as cur:
        cur.execute(f"UPDATE registrations SET {', '.join(fields)} WHERE id=?", values)


def get_pending_registrations() -> list[dict]:
    with get_cursor() as cur:
        cur.execute("""
            SELECT r.*, u.telegram_id, u.username, u.first_name, u.last_name,
                   e.title as event_title
            FROM registrations r
            JOIN users u ON r.user_id=u.id
            JOIN events e ON r.event_id=e.id
            WHERE r.approval_status='pending'
            ORDER BY r.created_at
        """)
        return [dict(row) for row in cur.fetchall()]


def get_stats() -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) as cnt FROM events")
        total_events = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) as cnt FROM registrations")
        total_regs = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) as cnt FROM registrations WHERE approval_status='pending'")
        pending = cur.fetchone()["cnt"]
    return {
        "total_users": total_users,
        "total_events": total_events,
        "total_registrations": total_regs,
        "pending_registrations": pending,
    }


# --- Event media helpers ---

def add_event_media(event_id: int, media_type: str, file_id: str | None,
                    file_path: str | None, caption: str | None,
                    order: int, uploaded_by: int | None) -> int:
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO event_media
            (event_id, media_type, file_id, file_path, caption, display_order, uploaded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event_id, media_type, file_id, file_path, caption, order, uploaded_by))
        return cur.lastrowid


def get_event_media(event_id: int) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM event_media WHERE event_id=? ORDER BY display_order",
            (event_id,)
        )
        return [dict(row) for row in cur.fetchall()]


def delete_media(media_id: int) -> None:
    with get_cursor() as cur:
        cur.execute("DELETE FROM event_media WHERE id=?", (media_id,))


def update_media_file_id(media_id: int, file_id: str) -> None:
    with get_cursor() as cur:
        cur.execute("UPDATE event_media SET file_id=? WHERE id=?", (file_id, media_id))


# --- Channel helpers ---

def get_required_channels() -> list[dict]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM required_channels WHERE is_active=1")
        return [dict(row) for row in cur.fetchall()]


def add_required_channel(channel_id: int, username: str, title: str,
                         added_by: int | None) -> int:
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO required_channels (channel_id, channel_username, channel_title, added_by)
            VALUES (?, ?, ?, ?)
        """, (channel_id, username, title, added_by))
        return cur.lastrowid


def remove_required_channel(channel_id_or_pk: int) -> None:
    with get_cursor() as cur:
        cur.execute(
            "UPDATE required_channels SET is_active=0 WHERE id=? OR channel_id=?",
            (channel_id_or_pk, channel_id_or_pk)
        )


# --- FSM / User state helpers ---

def get_user_state(telegram_id: int) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM user_states WHERE telegram_id=?", (telegram_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["state_data"] = json.loads(d["state_data"] or "{}")
        return d


def set_user_state(telegram_id: int, state: str, state_data: dict | None = None) -> None:
    data_json = json.dumps(state_data or {})
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO user_states (telegram_id, state, state_data)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                state=excluded.state,
                state_data=excluded.state_data,
                updated_at=datetime('now')
        """, (telegram_id, state, data_json))


def clear_user_state(telegram_id: int) -> None:
    with get_cursor() as cur:
        cur.execute("DELETE FROM user_states WHERE telegram_id=?", (telegram_id,))


# --- Notification helpers ---

def create_notification(user_id: int, event_id: int, message: str,
                        notification_type: str, scheduled_at: str) -> int:
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO notifications (user_id, event_id, message, notification_type, scheduled_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, event_id, message, notification_type, scheduled_at))
        return cur.lastrowid


def get_pending_notifications() -> list[dict]:
    with get_cursor() as cur:
        cur.execute("""
            SELECT n.*, u.telegram_id
            FROM notifications n
            JOIN users u ON n.user_id=u.id
            WHERE n.is_sent=0 AND n.scheduled_at <= datetime('now')
        """)
        return [dict(row) for row in cur.fetchall()]


def mark_notification_sent(notif_id: int) -> None:
    with get_cursor() as cur:
        cur.execute("""
            UPDATE notifications SET is_sent=1, sent_at=datetime('now') WHERE id=?
        """, (notif_id,))


# --- Broadcast helpers ---

def create_broadcast(message_text: str, target: str, event_id: int | None,
                     media_file_id: str | None, media_type: str | None,
                     sent_count: int, failed_count: int, sent_by: int | None) -> int:
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO broadcasts
            (message_text, target, event_id, media_file_id, media_type,
             sent_count, failed_count, sent_by, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (message_text, target, event_id, media_file_id, media_type,
              sent_count, failed_count, sent_by))
        return cur.lastrowid


def get_pending_broadcasts() -> list[dict]:
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM broadcasts
            WHERE status='pending'
            ORDER BY created_at
        """)
        return [dict(row) for row in cur.fetchall()]


def update_broadcast_counts(broadcast_id: int, sent_count: int,
                            failed_count: int, status: str = "sent") -> None:
    with get_cursor() as cur:
        cur.execute("""
            UPDATE broadcasts
            SET sent_count=?, failed_count=?, status=?
            WHERE id=?
        """, (sent_count, failed_count, status, broadcast_id))


def get_event_registered_users(event_id: int) -> list[dict]:
    """Return users with approved registrations for a given event."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT DISTINCT u.*
            FROM users u
            JOIN registrations r ON r.user_id = u.id
            WHERE r.event_id=? AND r.approval_status='approved' AND u.is_blocked=0
        """, (event_id,))
        return [dict(row) for row in cur.fetchall()]
