# Placement OS

A small local-first application for tracking placement-year applications.

V0.1 focuses on one useful workflow:

1. Save a role.
2. Record its deadline and status.
3. Add the next action.
4. Keep applications and companies organised.

## Run locally

Clone the repository, switch to the v0.1 branch, then run:

```bash
python3 scripts/run.py
```

Open:

```text
http://127.0.0.1:8766
```

Application data is stored locally in `data/placements.sqlite3` and is ignored by Git.

## Current sections

- Home — next actions and upcoming deadlines
- Applications — add, edit, delete and track roles
- Companies — see applications grouped by company
- Profile — placeholder for CV evidence and job matching in V0.2

## Next milestone

V0.2 will add job-advert analysis:

```text
paste job advert
      ↓
extract requirements
      ↓
compare against profile evidence
      ↓
show strong matches, gaps and suggested evidence
```

## Tests

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
```
