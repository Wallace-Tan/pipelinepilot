# PipelinePilot

PipelinePilot is a governed incident workflow demo for a retail schema-drift failure. The current MVP includes typed context skills, a deterministic fixture decision fallback, SQLite persistence, fixture-mode request identity/RBAC, redaction, governed recovery, a versioned API, and an API-backed dashboard.

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
- [Demo guide](docs/DEMO.md)

## Demo Data

Sanitized schema-drift fixtures live under `data/fixtures/schema_drift`. Runbooks live under `data/runbooks`, and the immutable fixture policy is `data/policies/demo_policy.json`.

No real Airflow, dbt, Snowflake, CoCo, or recovery behavior is connected; external integrations remain fixture-only.

Milestone 6 adds the `/v1` incident lifecycle API and connects the dashboard to persisted fixture-mode state. Milestone 4 provides deterministic runbook retrieval and recommendation validation; Milestone 5 provides policy evaluation, fingerprint-bound approvals, idempotent fixture recovery, and validation-gated transitions. No live integration or recovery write is enabled.

Milestone 7 adds the Admin-only fixture reset, demo readiness status, full lifecycle verification, API replay script, and judge walkthrough. Use `docs/DEMO.md` for the five-minute scenario and recovery instructions.

## Fixture-mode security

Requests may provide `X-Actor-Id` and `X-Actor-Role` headers with `viewer`, `operator`, or `admin`. Missing identity headers default to the read-only `anonymous-viewer` identity. The backend stores sanitized evidence and rejects unsupported roles or unauthorized transitions.


