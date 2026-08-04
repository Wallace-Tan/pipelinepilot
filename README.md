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
- [Live Airflow/Cortex verification](docs/LIVE_INTEGRATION.md)

## Demo Data

Sanitized schema-drift fixtures live under `data/fixtures/schema_drift`. Runbooks live under `data/runbooks`, and the immutable fixture policy is `data/policies/demo_policy.json`.

Fixture mode remains the default and does not require credentials. An opt-in CoCo path is available: when `PIPELINEPILOT_COCO_ENABLED=true`, the backend invokes the local `cortex` CLI for read-only Airflow/Snowflake context and structured decision support. CoCo is reported as unverified until an investigation completes; successful live evidence, fixture fallback, and safe fallback reasons are exposed through `adapter_status`. Recovery remains fixture-only.

Milestone 6 adds the `/v1` incident lifecycle API and connects the dashboard to persisted fixture-mode state. Milestone 4 provides deterministic runbook retrieval and recommendation validation; Milestone 5 provides policy evaluation, fingerprint-bound approvals, idempotent fixture recovery, and validation-gated transitions. No live integration or recovery write is enabled.

Milestone 7 adds the Admin-only fixture reset, demo readiness status, full lifecycle verification, API replay script, and judge walkthrough. Use `docs/DEMO.md` for the five-minute scenario and recovery instructions.

Milestone 8 adds a read-only Policy view backed by `GET /v1/policies/current`. It exposes the active immutable policy, fixture environment, default-deny behavior, approval requirements, and rule constraints without allowing policy changes.

## CoCo CLI integration

Install and authenticate the Snowflake CoCo CLI, then verify the connection with `cortex --version` and a read-only prompt. CoCo requires a Snowflake connection with `SNOWFLAKE.CORTEX_USER` or `SNOWFLAKE.CORTEX_AGENT_USER`; Airflow access is configured through the CoCo Airflow integration. See `docs/DEMO.md` for the live-mode launch command. Never commit `connections.toml`, tokens, or Airflow credentials.

## Fixture-mode security

Requests may provide `X-Actor-Id` and `X-Actor-Role` headers with `viewer`, `operator`, or `admin`. Missing identity headers default to the read-only `anonymous-viewer` identity. The backend stores sanitized evidence and rejects unsupported roles or unauthorized transitions.


