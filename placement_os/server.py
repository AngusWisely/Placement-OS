"""Small local HTTP server for Placement OS."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import db
from . import analyser

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
DB_PATH = ROOT / "data" / "placements.sqlite3"


def _application_from(data: dict) -> db.Application:
    return db.Application(
        id=None,
        company=str(data.get("company", "")), role=str(data.get("role", "")),
        location=str(data.get("location", "")), job_url=str(data.get("job_url", "")),
        deadline=str(data.get("deadline", "")), status=str(data.get("status", "Saved")),
        application_date=str(data.get("application_date", "")), next_action=str(data.get("next_action", "")),
        next_action_date=str(data.get("next_action_date", "")), contact_name=str(data.get("contact_name", "")),
        contact_linkedin=str(data.get("contact_linkedin", "")), notes=str(data.get("notes", "")),
    )


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass

    def _json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(body)

    def _body(self) -> dict:
        size = int(self.headers.get("Content-Length") or 0)
        if not 0 < size <= 1_000_000:
            return {}
        try:
            value = json.loads(self.rfile.read(size))
        except ValueError:
            return {}
        return value if isinstance(value, dict) else {}

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            body = (STATIC / "index.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        with db.connect(DB_PATH) as conn:
            if path == "/api/home": return self._json(db.home_summary(conn))
            if path == "/api/applications": return self._json(db.list_applications(conn))
            if path == "/api/profile": return self._json(db.list_evidence(conn))
            if path.startswith("/api/applications/") and path.rsplit("/", 1)[-1].isdigit():
                item = db.get_application(conn, int(path.rsplit("/", 1)[-1]))
                return self._json(item, 200 if item else 404)
        self._json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        data = self._body()

        if path == "/api/applications":
            try:
                with db.connect(DB_PATH) as conn:
                    app_id = db.create_application(conn, _application_from(data))
                    return self._json(db.get_application(conn, app_id), 201)
            except ValueError as exc:
                return self._json({"error": str(exc)}, 400)

        if path == "/api/profile":
            try:
                with db.connect(DB_PATH) as conn:
                    evidence_id = db.create_evidence(
                        conn,
                        type=str(data.get("type", "project")),
                        title=str(data.get("title", "")),
                        detail=str(data.get("detail", "")),
                        keywords=str(data.get("keywords", "")),
                    )
                    row = conn.execute("SELECT * FROM profile_evidence WHERE id=?", (evidence_id,)).fetchone()
                    return self._json(dict(row), 201)
            except ValueError as exc:
                return self._json({"error": str(exc)}, 400)

        if path.startswith("/api/analyse/") and path.rsplit("/", 1)[-1].isdigit():
            app_id = int(path.rsplit("/", 1)[-1])
            advert = str(data.get("advert", "")).strip()
            if len(advert) < 40:
                return self._json({"error": "Paste more of the job advert before analysing it"}, 400)
            try:
                with db.connect(DB_PATH) as conn:
                    if db.get_application(conn, app_id) is None:
                        return self._json({"error": "Application not found"}, 404)
                    result = analyser.analyse(advert, db.list_evidence(conn))
                    db.save_job_analysis(conn, app_id, advert, analyser.dumps(result))
                    return self._json(result)
            except KeyError:
                return self._json({"error": "Application not found"}, 404)

        return self._json({"error": "Not found"}, 404)

    def do_PUT(self):
        path = urlparse(self.path).path
        if not (path.startswith("/api/applications/") and path.rsplit("/", 1)[-1].isdigit()):
            return self._json({"error": "Not found"}, 404)
        app_id = int(path.rsplit("/", 1)[-1])
        try:
            with db.connect(DB_PATH) as conn:
                db.update_application(conn, app_id, _application_from(self._body()))
                return self._json(db.get_application(conn, app_id))
        except KeyError:
            self._json({"error": "Not found"}, 404)
        except ValueError as exc:
            self._json({"error": str(exc)}, 400)

    def do_DELETE(self):
        path = urlparse(self.path).path
        try:
            with db.connect(DB_PATH) as conn:
                if path.startswith("/api/applications/") and path.rsplit("/", 1)[-1].isdigit():
                    db.delete_application(conn, int(path.rsplit("/", 1)[-1]))
                    return self._json({"deleted": True})
                if path.startswith("/api/profile/") and path.rsplit("/", 1)[-1].isdigit():
                    db.delete_evidence(conn, int(path.rsplit("/", 1)[-1]))
                    return self._json({"deleted": True})
        except KeyError:
            return self._json({"error": "Not found"}, 404)
        return self._json({"error": "Not found"}, 404)


def run(host="127.0.0.1", port=8766) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Placement OS running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
