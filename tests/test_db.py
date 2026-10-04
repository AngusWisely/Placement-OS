from placement_os import db


def test_crud_and_summary(tmp_path):
    conn = db.connect(tmp_path / "placements.sqlite3")
    app = db.Application(None, "Arup", "Building Services Placement", location="Manchester", deadline="2026-11-06", next_action="Finish application")
    app_id = db.create_application(conn, app)
    saved = db.get_application(conn, app_id)
    assert saved["company"] == "Arup"
    assert saved["status"] == "Saved"
    summary = db.home_summary(conn)
    assert summary["deadlines"][0]["id"] == app_id
    assert summary["actions"][0]["next_action"] == "Finish application"

    changed = db.Application(None, "Arup", "Building Services Placement", status="Applied", application_date="2026-10-04")
    db.update_application(conn, app_id, changed)
    assert db.get_application(conn, app_id)["status"] == "Applied"

    db.delete_application(conn, app_id)
    assert db.get_application(conn, app_id) is None


def test_validation(tmp_path):
    conn = db.connect(tmp_path / "placements.sqlite3")
    try:
        db.create_application(conn, db.Application(None, "", ""))
    except ValueError as exc:
        assert "required" in str(exc)
    else:
        raise AssertionError("Expected validation error")
