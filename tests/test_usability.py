import io
import json

from placement_os import db, importer


def test_preferences_are_remembered(tmp_path):
    conn = db.connect(tmp_path / "placements.sqlite3")
    assert db.get_preferences(conn)["location"] == ""
    saved = db.save_preferences(conn, location="Manchester", min_relevance=60)
    assert saved == {"location": "Manchester", "min_relevance": 60}
    assert db.get_preferences(conn) == saved


def test_discovery_new_hide_and_saved_state(tmp_path):
    conn = db.connect(tmp_path / "placements.sqlite3")
    job = {
        "job_key": "abc123",
        "title": "Building Services Placement",
        "company": "Example Engineers",
        "url": "https://example.com/job",
    }
    first = db.record_discovery(conn, job)
    assert first["is_new"] is True
    assert first["hidden"] is False

    second = db.record_discovery(conn, job)
    assert second["is_new"] is False

    db.hide_discovery(conn, "abc123")
    hidden = db.record_discovery(conn, job)
    assert hidden["hidden"] is True

    app_id = db.create_application(conn, db.Application(None, "Example Engineers", "Placement"))
    db.mark_discovery_saved(conn, "abc123", app_id)
    state = db.record_discovery(conn, job)
    assert state["saved_application_id"] == app_id


class FakeHeaders:
    def get(self, key, default=""):
        return "text/html; charset=utf-8" if key.lower() == "content-type" else default


class FakeResponse:
    headers = FakeHeaders()

    def __init__(self, html):
        self.html = html

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, _limit=None):
        return self.html.encode()


def test_job_url_importer_extracts_basic_fields():
    page = """
    <html><head>
      <title>Graduate Building Services Placement | Example Careers</title>
      <meta property="og:site_name" content="Example Engineers">
      <meta name="description" content="A great placement">
    </head>
    <body>
      <h1>Graduate Building Services Placement</h1>
      <p>Join our multidisciplinary building services team using Revit, energy modelling,
      sustainability analysis and engineering design across live projects.</p>
      <p>This industrial placement is for undergraduate engineering students and includes
      structured training, project work, collaboration and technical development.</p>
    </body></html>
    """
    def opener(request, timeout=15):
        return FakeResponse(page)

    result = importer.fetch_job("https://careers.example.com/job/123", opener=opener)
    assert result["company"] == "Example Engineers"
    assert result["role"].startswith("Graduate Building Services Placement")
    assert "Revit" in result["job_advert"]
    assert result["job_url"].endswith("/job/123")
