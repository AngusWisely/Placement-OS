from placement_os import analyser, db


def test_profile_evidence_and_analysis(tmp_path):
    conn = db.connect(tmp_path / "placements.sqlite3")
    db.create_evidence(
        conn,
        type="project",
        title="Building services design",
        detail="Designed ventilation and building-services systems in Revit.",
        keywords="Revit, BIM, building services, MEP",
    )
    db.create_evidence(
        conn,
        type="project",
        title="Energy retrofit optimiser",
        detail="Python tool comparing energy, carbon and retrofit options.",
        keywords="Python, energy, sustainability, carbon, automation",
    )

    result = analyser.analyse(
        "We are looking for a student with Revit and building services experience. "
        "Strong communication skills are essential. Python and sustainability are desirable.",
        db.list_evidence(conn),
    )

    names = {m["name"] for m in result["matches"]}
    gaps = {g["name"] for g in result["gaps"]}
    assert "Revit / BIM" in names
    assert "Building services / MEP" in names
    assert "Python / programming" in names
    assert "Sustainability / net zero" in names
    assert "Communication" in gaps
    assert 0 <= result["score"] <= 100


def test_job_analysis_is_saved_on_application(tmp_path):
    conn = db.connect(tmp_path / "placements.sqlite3")
    app_id = db.create_application(conn, db.Application(None, "WSP", "Building Services Placement"))
    result = {"score": 75, "matches": [], "gaps": [], "requirements": [], "summary": "Test"}
    db.save_job_analysis(conn, app_id, "Long enough example advert text for testing purposes.", analyser.dumps(result))
    saved = db.get_application(conn, app_id)
    assert saved["job_advert"].startswith("Long enough")
    assert '"score": 75' in saved["analysis_json"]


def test_profile_evidence_can_be_removed(tmp_path):
    conn = db.connect(tmp_path / "placements.sqlite3")
    evidence_id = db.create_evidence(conn, type="skill", title="Python", keywords="python")
    assert len(db.list_evidence(conn)) == 1
    db.delete_evidence(conn, evidence_id)
    assert db.list_evidence(conn) == []
