# PipelinePilot

PipelinePilot is the control plane between AI investigation and operational action. It turns sanitized evidence into a cited recovery proposal, applies deterministic policy, requires accountable operator approval, and records the validated result. The submission runs in fixture mode: recovery is simulated, clearly labeled, and never writes to Airflow, dbt, or Snowflake.

## Open the deployed demo

No local services or credentials are required for the demo.

- Frontend: [pipelinepilot.vercel.app](https://pipelinepilot.vercel.app/)
- Backend health: [pipelinepilot-api.onrender.com/health](https://pipelinepilot-api.onrender.com/health)
- Backend API docs: [pipelinepilot-api.onrender.com/docs](https://pipelinepilot-api.onrender.com/docs)

### Demo path

1. Open the frontend and select **Open Command Center**.
2. Use **Reset fixture - Admin demo** if the seeded state needs to be restored.
3. Open the schema-drift workbench and select **Investigate fixture incident**.
4. Try execution to see the policy/approval gate, then approve, execute, and validate the fixture recovery.
5. Review the policy, evidence citations, execution result, and audit timeline.

The API is configured for the deployed Vercel origin. It uses a temporary SQLite database on Render, so fixture state may reset after a service restart or redeploy.

## Repository verification

The repository keeps deterministic backend tests and a production frontend build for review:

```powershell
cd backend
uv sync
uv run pytest

cd ..\frontend
npm install
npm run build
```

The browser suite also checks the deployed-style workflow, narrow layouts, route behavior, retry states, and basic accessible naming. Install Chromium once, then run it from `frontend`:

```powershell
npx playwright install chromium
npm run test:e2e
```

For local development only, run the backend and Vite commands documented in [docs/DEMO.md](docs/DEMO.md). Production builds use `https://pipelinepilot-api.onrender.com` by default; `VITE_PIPELINEPILOT_API_URL` can override it for another environment.

## What is included

- [Architecture](docs/ARCHITECTURE.md)
- [Product requirements](docs/PRD.md)
- [Demo guide](docs/DEMO.md)
- [Deployment configuration](docs/DEPLOYMENT.md)
- [Judge demo script](DEMO_SCRIPT.md)
- [CoCo/Airflow verification boundary](docs/LIVE_INTEGRATION.md)

Sanitized schema-drift fixtures live under `data/fixtures/schema_drift`. Runbooks live under `data/runbooks`, and the immutable fixture policy is `data/policies/demo_policy.json`.

## Safety and operating boundary

- Fixture mode is the default and requires no credentials.
- Policy runs server-side before approval or recovery.
- Viewer, Operator, and Admin roles are enforced server-side in the fixture workflow.
- Evidence sent to decision support is sanitized and cited; invalid or uncited recommendations are rejected.
- CoCo is an opt-in, read-only integration. A configured CLI is not presented as verified live connectivity, and recovery remains fixture-only.
- Do not commit `.env` files, tokens, connection profiles, raw logs, or generated SQLite databases.

Requests may provide `X-Actor-Id` and `X-Actor-Role` headers with `viewer`, `operator`, or `admin`. Missing identity headers default to the read-only `anonymous-viewer` identity.
