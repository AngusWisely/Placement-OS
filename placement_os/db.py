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
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_applications_deadline ON applications(deadline);
        CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
        """
    )
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
