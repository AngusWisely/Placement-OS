"""UK placement discovery using Adzuna's official jobs API."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import analyser

API_ROOT = "https://api.adzuna.com/v1/api/jobs/gb/search/1"
CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "adzuna.json"

DEFAULT_QUERIES = (
    "building services placement",
    "energy placement",
    "sustainability placement",
    "environmental engineering placement",
    "digital engineering placement",
    "building performance placement",
)

PLACEMENT_WORDS = (
    "placement",
    "industrial placement",
    "year in industry",
    "sandwich",
    "undergraduate",
    "internship",
    "intern",
)


class DiscoveryError(RuntimeError):
    pass


def credentials() -> tuple[str, str]:
    env_id = os.environ.get("ADZUNA_APP_ID", "").strip()
    env_key = os.environ.get("ADZUNA_APP_KEY", "").strip()
    if env_id and env_key:
        return env_id, env_key
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return str(data.get("app_id", "")).strip(), str(data.get("app_key", "")).strip()
    except (OSError, ValueError, TypeError):
        return "", ""


def configured() -> bool:
    app_id, app_key = credentials()
    return bool(app_id and app_key)


def save_credentials(app_id: str, app_key: str) -> None:
    app_id, app_key = app_id.strip(), app_key.strip()
    if not app_id or not app_key:
        raise ValueError("Both Adzuna App ID and App Key are required")
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"app_id": app_id, "app_key": app_key}), encoding="utf-8")
    try:
        CONFIG_PATH.chmod(0o600)
    except OSError:
        pass


def _fetch_json(url: str, *, opener=urlopen) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "Placement-OS/0.3"})
    try:
        with opener(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise DiscoveryError(f"Job search failed: {exc}") from exc


def _placement_signal(title: str, description: str) -> int:
    blob = f"{title} {description}".lower()
    if "year in industry" in blob or "industrial placement" in blob:
        return 25
    if "placement" in blob:
        return 20
    if "internship" in blob or "undergraduate" in blob:
        return 12
    if "intern" in blob:
        return 8
    return 0


def search(
    evidence: list[dict],
    *,
    location: str = "",
    queries: tuple[str, ...] = DEFAULT_QUERIES,
    per_query: int = 10,
    opener=urlopen,
) -> list[dict]:
    app_id, app_key = credentials()
    if not app_id or not app_key:
        raise DiscoveryError("Adzuna is not configured")

    seen: dict[str, dict] = {}
    for query in queries:
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": max(1, min(per_query, 25)),
            "what": query,
            "content-type": "application/json",
            "sort_by": "date",
        }
        if location.strip():
            params["where"] = location.strip()

        data = _fetch_json(API_ROOT + "?" + urlencode(params), opener=opener)
        for item in data.get("results", []):
            url = str(item.get("redirect_url") or "").strip()
            title = str(item.get("title") or "").strip()
            description = str(item.get("description") or "").strip()
            if not title or not url:
                continue

            key = url.split("?", 1)[0]
            analysis = analyser.analyse(description, evidence)
            placement_signal = _placement_signal(title, description)
            relevance = min(100, analysis["score"] + placement_signal)

            location_name = ""
            loc = item.get("location")
            if isinstance(loc, dict):
                location_name = str(loc.get("display_name") or "")

            company = ""
            employer = item.get("company")
            if isinstance(employer, dict):
                company = str(employer.get("display_name") or "")

            job_key = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
            record = {
                "job_key": job_key,
                "source": "Adzuna",
                "source_id": str(item.get("id") or ""),
                "title": title,
                "company": company,
                "location": location_name,
                "url": url,
                "description": description,
                "created": str(item.get("created") or ""),
                "salary_min": item.get("salary_min"),
                "salary_max": item.get("salary_max"),
                "profile_score": analysis["score"],
                "relevance": relevance,
                "analysis": analysis,
                "query": query,
            }

            existing = seen.get(key)
            if existing is None or record["relevance"] > existing["relevance"]:
                seen[key] = record

    results = list(seen.values())
    results.sort(key=lambda x: (-x["relevance"], x["company"].lower(), x["title"].lower()))
    return results


def status() -> dict:
    return {
        "configured": configured(),
        "source": "Adzuna",
        "queries": list(DEFAULT_QUERIES),
    }
