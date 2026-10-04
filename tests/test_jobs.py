import io
import json

from placement_os import jobs


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def test_discovery_ranks_and_deduplicates(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "CONFIG_PATH", tmp_path / "adzuna.json")
    jobs.save_credentials("id", "key")

    payload = {
        "results": [
            {
                "id": "1",
                "title": "Building Services Industrial Placement",
                "description": "Revit building services sustainability placement role.",
                "redirect_url": "https://example.com/job/1?ref=x",
                "location": {"display_name": "Manchester"},
                "company": {"display_name": "Example Engineers"},
                "created": "2026-10-04T10:00:00Z",
            },
            {
                "id": "1b",
                "title": "Building Services Industrial Placement",
                "description": "Revit building services sustainability placement role.",
                "redirect_url": "https://example.com/job/1?ref=y",
                "location": {"display_name": "Manchester"},
                "company": {"display_name": "Example Engineers"},
                "created": "2026-10-04T10:00:00Z",
            },
        ]
    }

    def opener(request, timeout=15):
        return FakeResponse(payload)

    evidence = [{
        "id": 1,
        "type": "project",
        "title": "Building services design",
        "detail": "Used Revit for building-services design.",
        "keywords": "Revit, BIM, building services, sustainability",
    }]

    results = jobs.search(evidence, queries=("building services placement",), opener=opener)
    assert len(results) == 1
    assert results[0]["company"] == "Example Engineers"
    assert results[0]["location"] == "Manchester"
    assert results[0]["relevance"] >= results[0]["profile_score"]
    assert results[0]["analysis"]["matches"]


def test_credentials_are_local(monkeypatch, tmp_path):
    path = tmp_path / "adzuna.json"
    monkeypatch.setattr(jobs, "CONFIG_PATH", path)
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)
    assert not jobs.configured()
    jobs.save_credentials("abc", "secret")
    assert jobs.configured()
    assert jobs.credentials() == ("abc", "secret")
