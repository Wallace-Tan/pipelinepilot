# PipelinePilot

PipelinePilot is a governed incident workflow demo for a retail schema-drift failure. Milestone 3 includes typed context skills, fixture adapters, concurrent investigation, SQLite persistence, fixture-mode request identity/RBAC, and recursive evidence redaction.

## Prerequisites

- Python 3.12
- `uv`
- Node.js 22
- npm

## Backend

```powershell
cd backend
uv sync
uv run pytest
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Frontend

```powershell
cd frontend
npm install
npm run build
npm run dev
```

The Vite dev server prints the local URL, normally `http://127.0.0.1:5173/`.

## Project Docs

- [Product requirements](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Implementation roadmap](docs/TASKS.md)
- [Hackathon notes](docs/HACKATHON.md)

## Demo Data

Sanitized schema-drift fixtures live under `data/fixtures/schema_drift`. Runbooks live under `data/runbooks`, and the immutable fixture policy is `data/policies/demo_policy.json`.

No real Airflow, dbt, Snowflake, CoCo, or recovery behavior is implemented; external integrations remain fixture-only.

Milestone 3 investigation is service-level and uses the monitoring, Airflow-log, dbt, and Snowflake-metadata fixtures. A future read-only live adapter must use the same skill boundary; fixture mode remains the selected fallback.

## Fixture-mode security

Requests may provide `X-Actor-Id` and `X-Actor-Role` headers with `viewer`, `operator`, or `admin`. Missing identity headers default to the read-only `anonymous-viewer` identity. The backend stores sanitized evidence and rejects unsupported roles or unauthorized transitions.


