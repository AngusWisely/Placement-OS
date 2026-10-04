"""SQLite persistence for placement applications."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

STATUSES = (
    "Saved", "Researching", "Applying", "Applied",
    "Assessment", "Interview", "Offer", "Rejected", "Closed",
)

@dataclass(slots=True)
class Application:
    id: int | None
    company: str
    role: str
    location: str = ""
    job_url: str = ""
    deadline: str = ""
    status: str = "Saved"
    application_date: str = ""
    next_action: str = ""
    next_action_date: str = ""
    contact_name: str = ""
    contact_linkedin: str = ""
    notes: str = ""


def connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            location TEXT NOT NULL DEFAULT '',
            job_url TEXT NOT NULL DEFAULT '',
            deadline TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Saved',
            application_date TEXT NOT NULL DEFAULT '',
            next_action TEXT NOT NULL DEFAULT '',
            next_action_date TEXT NOT NULL DEFAULT '',
            contact_name TEXT NOT NULL DEFAULT '',
            contact_linkedin TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            job_advert TEXT NOT NULL DEFAULT '',
            analysis_json TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_applications_deadline ON applications(deadline);
        CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);

        CREATE TABLE IF NOT EXISTS profile_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL DEFAULT 'project',
            title TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '',
            keywords TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS discovery_items (
            job_key TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '',
            company TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL DEFAULT '',
            hidden INTEGER NOT NULL DEFAULT 0,
            saved_application_id INTEGER,
            first_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(applications)")}
    if "job_advert" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN job_advert TEXT NOT NULL DEFAULT ''")
    if "analysis_json" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN analysis_json TEXT NOT NULL DEFAULT ''")
    conn.commit()


def _validate(app: Application) -> None:
    if not app.company.strip() or not app.role.strip():
        raise ValueError("Company and role are required")
    if app.status not in STATUSES:
        raise ValueError(f"Unknown status: {app.status}")


def create_application(conn: sqlite3.Connection, app: Application) -> int:
    _validate(app)
    cur = conn.execute(
        """INSERT INTO applications
        (company, role, location, job_url, deadline, status, application_date,
         next_action, next_action_date, contact_name, contact_linkedin, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (app.company.strip(), app.role.strip(), app.location.strip(), app.job_url.strip(),
         app.deadline.strip(), app.status, app.application_date.strip(), app.next_action.strip(),
         app.next_action_date.strip(), app.contact_name.strip(), app.contact_linkedin.strip(), app.notes.strip()),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_application(conn: sqlite3.Connection, app_id: int, app: Application) -> None:
    _validate(app)
    cur = conn.execute(
        """UPDATE applications SET
        company=?, role=?, location=?, job_url=?, deadline=?, status=?, application_date=?,
        next_action=?, next_action_date=?, contact_name=?, contact_linkedin=?, notes=?,
        updated_at=CURRENT_TIMESTAMP WHERE id=?""",
        (app.company.strip(), app.role.strip(), app.location.strip(), app.job_url.strip(),
         app.deadline.strip(), app.status, app.application_date.strip(), app.next_action.strip(),
         app.next_action_date.strip(), app.contact_name.strip(), app.contact_linkedin.strip(),
         app.notes.strip(), app_id),
    )
    if cur.rowcount == 0:
        raise KeyError(app_id)
    conn.commit()


def delete_application(conn: sqlite3.Connection, app_id: int) -> None:
    cur = conn.execute("DELETE FROM applications WHERE id=?", (app_id,))
    if cur.rowcount == 0:
        raise KeyError(app_id)
    conn.commit()


def get_application(conn: sqlite3.Connection, app_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
    return dict(row) if row else None


def list_applications(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT * FROM applications
        ORDER BY CASE WHEN deadline='' THEN 1 ELSE 0 END, deadline, company, role"""
    ).fetchall()
    return [dict(r) for r in rows]


def home_summary(conn: sqlite3.Connection) -> dict:
    apps = list_applications(conn)
    active = [a for a in apps if a["status"] not in {"Rejected", "Closed"}]
    due = [a for a in active if a["deadline"]][:5]
    actions = [a for a in active if a["next_action"]][:5]
    counts = {status: 0 for status in STATUSES}
    for app in apps:
        counts[app["status"]] += 1
    return {"applications": apps, "deadlines": due, "actions": actions, "counts": counts}


def list_evidence(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM profile_evidence ORDER BY type, title").fetchall()
    return [dict(r) for r in rows]


def create_evidence(conn: sqlite3.Connection, *, type: str, title: str, detail: str = "", keywords: str = "") -> int:
    title = title.strip()
    if not title:
        raise ValueError("Evidence title is required")
    cur = conn.execute(
        "INSERT INTO profile_evidence(type, title, detail, keywords) VALUES (?, ?, ?, ?)",
        (type.strip() or "project", title, detail.strip(), keywords.strip()),
    )
    conn.commit()
    return int(cur.lastrowid)


def delete_evidence(conn: sqlite3.Connection, evidence_id: int) -> None:
    cur = conn.execute("DELETE FROM profile_evidence WHERE id=?", (evidence_id,))
    if cur.rowcount == 0:
        raise KeyError(evidence_id)
    conn.commit()


def save_job_analysis(conn: sqlite3.Connection, app_id: int, advert: str, analysis_json: str) -> None:
    cur = conn.execute(
        "UPDATE applications SET job_advert=?, analysis_json=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (advert.strip(), analysis_json, app_id),
    )
    if cur.rowcount == 0:
        raise KeyError(app_id)
    conn.commit()


def get_preferences(conn: sqlite3.Connection) -> dict:
    rows = conn.execute("SELECT key, value FROM preferences").fetchall()
    prefs = {row["key"]: row["value"] for row in rows}
    return {
        "location": prefs.get("location", ""),
        "min_relevance": int(prefs.get("min_relevance", "0") or 0),
    }


def save_preferences(conn: sqlite3.Connection, *, location: str, min_relevance: int = 0) -> dict:
    values = {
        "location": location.strip(),
        "min_relevance": str(max(0, min(100, int(min_relevance)))),
    }
    for key, value in values.items():
        conn.execute(
            "INSERT INTO preferences(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
    conn.commit()
    return get_preferences(conn)


def record_discovery(conn: sqlite3.Connection, job: dict) -> dict:
    key = str(job.get("job_key") or "").strip()
    if not key:
        raise ValueError("job_key is required")
    existing = conn.execute(
        "SELECT hidden, saved_application_id, first_seen FROM discovery_items WHERE job_key=?",
        (key,),
    ).fetchone()
    is_new = existing is None
    if existing is None:
        conn.execute(
            "INSERT INTO discovery_items(job_key, title, company, url) VALUES (?, ?, ?, ?)",
            (key, str(job.get("title", "")), str(job.get("company", "")), str(job.get("url", ""))),
        )
        hidden = 0
        saved_application_id = None
    else:
        conn.execute(
            "UPDATE discovery_items SET title=?, company=?, url=?, last_seen=CURRENT_TIMESTAMP WHERE job_key=?",
            (str(job.get("title", "")), str(job.get("company", "")), str(job.get("url", "")), key),
        )
        hidden = int(existing["hidden"])
        saved_application_id = existing["saved_application_id"]
    conn.commit()
    return {"is_new": is_new, "hidden": bool(hidden), "saved_application_id": saved_application_id}


def hide_discovery(conn: sqlite3.Connection, job_key: str) -> None:
    conn.execute(
        "INSERT INTO discovery_items(job_key, hidden) VALUES (?, 1) "
        "ON CONFLICT(job_key) DO UPDATE SET hidden=1, last_seen=CURRENT_TIMESTAMP",
        (job_key,),
    )
    conn.commit()


def mark_discovery_saved(conn: sqlite3.Connection, job_key: str, application_id: int) -> None:
    conn.execute(
        "INSERT INTO discovery_items(job_key, saved_application_id) VALUES (?, ?) "
        "ON CONFLICT(job_key) DO UPDATE SET saved_application_id=excluded.saved_application_id, last_seen=CURRENT_TIMESTAMP",
        (job_key, application_id),
    )
    conn.commit()
