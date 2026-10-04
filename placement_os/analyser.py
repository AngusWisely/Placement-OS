"""Deterministic job-advert analysis against stored profile evidence."""

from __future__ import annotations

import json
import re
from collections import defaultdict

REQUIREMENTS = {
    "Revit / BIM": ("revit", "bim", "building information modelling"),
    "Building services / MEP": ("building services", "mep", "mechanical electrical", "hvac"),
    "Energy / building performance": ("energy modelling", "energy model", "building performance", "thermal", "heat transfer", "energy"),
    "Sustainability / net zero": ("sustainability", "sustainable", "net zero", "carbon", "decarbonisation", "decarbonization"),
    "Python / programming": ("python", "programming", "coding", "software development"),
    "Data / automation / AI": ("data analysis", "automation", "artificial intelligence", " ai ", "machine learning", "digital tools"),
    "Engineering design": ("engineering design", "design development", "technical design", "design calculations", "design"),
    "Analysis / problem solving": ("analysis", "analytical", "problem solving", "problem-solving", "numerical"),
    "Communication": ("communication", "present", "presentation", "report writing", "written and verbal"),
    "Teamwork": ("teamwork", "team player", "collaborat", "multidisciplinary", "multi-disciplinary"),
    "Commercial / client awareness": ("client", "commercial", "consultancy", "stakeholder"),
    "Excel / spreadsheets": ("excel", "spreadsheet"),
}

PREFERRED_MARKERS = ("desirable", "preferred", "advantage", "beneficial", "nice to have")
REQUIRED_MARKERS = ("required", "essential", "must", "you will need", "we are looking for")


def _normalise(text: str) -> str:
    return " " + re.sub(r"\s+", " ", text.lower()).strip() + " "


def extract_requirements(text: str) -> list[dict]:
    """Return recognised requirement themes with a short source excerpt."""
    normal = _normalise(text)
    found = []
    for name, aliases in REQUIREMENTS.items():
        hit = next((alias for alias in aliases if alias in normal), None)
        if not hit:
            continue
        idx = normal.find(hit)
        excerpt = normal[max(0, idx - 95): min(len(normal), idx + len(hit) + 120)].strip()
        nearby = normal[max(0, idx - 80): min(len(normal), idx + 100)]
        importance = "preferred" if any(x in nearby for x in PREFERRED_MARKERS) else "required"
        found.append({"name": name, "importance": importance, "excerpt": excerpt})
    return found


def analyse(text: str, evidence: list[dict]) -> dict:
    requirements = extract_requirements(text)
    evidence_terms = []
    for item in evidence:
        terms = {x.strip().lower() for x in (item.get("keywords") or "").split(",") if x.strip()}
        terms.update(re.findall(r"[a-z0-9+#.]{3,}", (item.get("title", "") + " " + item.get("detail", "")).lower()))
        evidence_terms.append((item, terms))

    matches = []
    gaps = []
    for req in requirements:
        aliases = REQUIREMENTS[req["name"]]
        scored = []
        for item, terms in evidence_terms:
            score = 0
            blob = " " + " ".join(terms) + " "
            for alias in aliases:
                words = re.findall(r"[a-z0-9+#.]+", alias.lower())
                if alias.strip() in blob or any(word in terms for word in words if len(word) > 2):
                    score += 1
            if score:
                scored.append((score, item))
        scored.sort(key=lambda x: (-x[0], x[1].get("title", "")))
        if scored:
            matches.append({
                **req,
                "evidence": [
                    {"id": item.get("id"), "title": item.get("title"), "type": item.get("type"), "detail": item.get("detail")}
                    for _, item in scored[:3]
                ],
            })
        else:
            gaps.append(req)

    required = [r for r in requirements if r["importance"] == "required"]
    matched_required = sum(1 for m in matches if m["importance"] == "required")
    denominator = len(required) or len(requirements)
    numerator = matched_required if required else len(matches)
    score = round(100 * numerator / denominator) if denominator else 0

    return {
        "score": score,
        "requirements": requirements,
        "matches": matches,
        "gaps": gaps,
        "summary": _summary(score, len(requirements), len(gaps)),
    }


def _summary(score: int, requirements: int, gaps: int) -> str:
    if not requirements:
        return "No recognised requirement themes were found. Add more of the job description."
    if score >= 80:
        lead = "Strong evidence match"
    elif score >= 55:
        lead = "Good partial match"
    else:
        lead = "Several evidence gaps"
    return f"{lead}: {requirements} requirement themes found, {gaps} without matching profile evidence."


def dumps(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False)
