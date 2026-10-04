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


## V0.2 job analysis

V0.2 adds an explainable local matcher:

1. Add concrete projects, skills and experience under **Profile**.
2. Open an application and choose **Analyse advert**.
3. Paste the full job advert.
4. Placement OS identifies recognised requirement themes.
5. It links each requirement to profile evidence, or shows it as a gap.

The match is deliberately deterministic rather than an opaque AI score. No job advert or profile evidence is sent to an external API.


## V0.3 job discovery

V0.3 adds a **Find roles** screen backed by Adzuna's official UK jobs API.

The app searches these placement themes by default:

- building services
- energy
- sustainability
- environmental engineering
- digital engineering
- building performance

Results are deduplicated, analysed against the Profile evidence already stored in Placement OS, and ranked by relevance. A discovered role can be opened in the browser or saved directly into Applications.

### One-time setup

Open **Find roles** in Placement OS and enter an Adzuna App ID and App Key. The credentials are stored only in:

```text
data/adzuna.json
```

The whole `data/` directory is ignored by Git.

You can alternatively set `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` as environment variables.
