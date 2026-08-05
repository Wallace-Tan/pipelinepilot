# PipelinePilot Demo Guide

## Prerequisites

- Python 3.12 and `uv`
- Node.js 22 and npm
- A clean checkout with no committed SQLite database
- For the live CoCo path only: Snowflake CoCo CLI, an authenticated Snowflake connection, and read-only Airflow credentials configured for CoCo

## Start

```powershell
cd backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`. The UI must show `fixture`, `database ready`, and the intentionally degraded Snowflake metadata adapter.

For a clean-checkout preflight, run `scripts/verify-submission.ps1` from the repository root. It verifies `uv` setup, backend tests, the frontend production build, and tracked-file hygiene before the browser walkthrough.

The automated browser proof is configured in `frontend/playwright.config.ts`. From `frontend`, install the browser once and run:

```powershell
npx playwright install chromium
npm run test:e2e
```

The suite starts isolated local services, resets the fixture, verifies the blocked `approval_required` state, completes approval/recovery/validation, checks final metrics, filters the seeded exception queue, and checks that interactive controls have accessible names or labels. If `uv` is not on `PATH`, set `PIPELINEPILOT_UV` to the local `uv.exe` path for the test process.

When port `8000` is already occupied by another local demo process, run the proof workflow against an isolated temporary API/database instead of editing the repository database. Start the backend with `PIPELINEPILOT_DATABASE_PATH` set to a temporary SQLite path and point Vite at it with:

```powershell
$env:PIPELINEPILOT_API_URL = "http://127.0.0.1:8001"
npm run dev -- --host 127.0.0.1 --port 5177
```

The `PIPELINEPILOT_API_URL` override is supported by `frontend/vite.config.ts`; it affects only the Vite proxy. The UI must still show `fixture`, `database ready`, and `recovery fixture-only`.

## Optional CoCo-backed investigation

The safe default demo uses fixtures. To exercise the real CoCo integration, authenticate `cortex`, configure its Snowflake connection and Airflow instance, then start the backend with:

```powershell
$env:PIPELINEPILOT_COCO_ENABLED = "true"
$env:PIPELINEPILOT_COCO_CONNECTION = "your-snowflake-connection"
$env:PIPELINEPILOT_COCO_TIMEOUT_SECONDS = "90"
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

CoCo is invoked in one-shot JSON mode from the backend and is instructed to perform read-only Airflow/Snowflake investigation. The dashboard reports the result of the latest investigation, not merely the configuration flag: `CoCo live path`, `CoCo live context`, `CoCo fallback`, or `Fixture mode`. A newly enabled CoCo process remains `CoCo configured` until an investigation completes successfully. If CoCo is unavailable or returns malformed/uncited output, the typed boundary rejects it, the deterministic fixture recommendation is selected, and the fallback reason remains visible. Recovery remains governed by the backend policy and approval workflow and is always fixture-only.

The investigation response and `GET /v1/demo/status` expose `adapter_status` for each context skill and the decision adapter. Each entry includes the actual `mode`, `status`, `source`, and safe `reason` when degraded. Live evidence is marked `mode: live`; fixture recovery continues to return a `fixture://recovery/...` reference.

Use the current Snowflake CLI reference to confirm the installed command supports the backend's one-shot invocation shape (`--connection`, `--workdir`, `--print`, and `--output-format stream-json`) before claiming a live result. The backend must receive a schema-valid response from the installed CLI.

## Reset

```powershell
$headers = @{ "X-Actor-Id" = "demo-admin"; "X-Actor-Role" = "admin" }
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/demo/reset -Headers $headers
```

If the backend is stopped, use `scripts/reset-fixture.ps1`, then restart the backend. Reset recreates the local demo store and seeds the single sanitized schema-drift incident. It is not a production operation.

## Five-Minute Walkthrough

The judge-facing UI starts on the Command Center. Use `DEMO_SCRIPT.md` for the concise path: open the high-priority exception in Workbench, prove the approval gate, complete fixture recovery and validation, then return to Overview to show the updated metrics. The detailed lifecycle below remains the API and evidence reference.

1. **0:00–0:35 — Detect:** Show the failed `retail_orders_daily` incident, high severity, run identifier, and Fixture mode.
2. **0:35–0:55 — Policy:** Open the read-only Policy view; show the immutable fixture policy, version, default-deny behavior, and approval-required schema-drift rule.
3. **0:55–1:35 — Investigate:** Click `Investigate fixture incident`; show monitoring, Airflow log, dbt, and degraded Snowflake metadata evidence.
4. **1:35–2:20 — Recommend:** Show the schema-drift recommendation, high confidence, cited evidence IDs, `runbook-schema-drift` citation, and the business impact: stale `stg_orders`, `fct_orders`, and `daily_store_revenue` reporting.
5. **2:20–3:05 — Govern:** Use `Try execution — show approval gate` before approving. Show the safe `approval_required` response, then point to the decision boundary: CoCo proposes, Policy decides, and the Operator authorizes.
6. **3:05–4:00 — Recover:** Approve and execute fixture recovery. Point out the idempotency key, fixture reference, actor, policy version, and audit events.
7. **4:00–4:40 — Validate:** Run validation and show the incident reaching `VALIDATED` only after checks pass.
8. **4:40–5:00 — Report:** Open the report, show evidence-linked RCA, uncertainty, audit trail, and feedback capability.

## Backup API Replay

```powershell
.\scripts\demo-replay.ps1
```

The script resets the fixture, runs the full governed lifecycle, measures elapsed time, and prints the final status. Expected output is represented by `scripts/demo-replay.expected.json`.

The replay also verifies viewer mutation denial, validation-before-recovery gating, and missing-approval denial before exercising the approved fixture recovery path. For the live Airflow/Snowflake path, use [LIVE_INTEGRATION.md](LIVE_INTEGRATION.md); live credentials are never required for the default replay.

## Identity and Troubleshooting

- Anonymous requests are read-only Viewer requests.
- Operator headers: `X-Actor-Id: demo-operator`, `X-Actor-Role: operator`.
- Admin reset headers: `X-Actor-Id: demo-admin`, `X-Actor-Role: admin`.
- API unavailable: start the backend and select `Retry`.
- Stale state: use `Reset fixture` or `scripts/reset-fixture.ps1`.
- Validation blocked: recovery must succeed first.
- No credentials, live integrations, production writes, or raw PII are used.

## Judge Criteria Mapping

| Criterion | Visible proof |
| --- | --- |
| Real-world relevancy | Retail schema drift, failed pipeline context, dbt freshness, warehouse metadata, and runbook guidance. |
| Technical execution | Typed skills, redaction, lexical retrieval, deterministic policy, SQLite persistence, API contracts, and audit records. |
| Solution completeness | Detect → investigate → recommend → approve → recover → validate → report → feedback. |

## Submission Checklist

- [x] Fresh checkout starts without a committed database or credentials.
- [x] `uv sync` and `uv run pytest` pass from `backend`.
- [x] Frontend TypeScript and Vite builds pass; the Windows-safe Vite dev command reaches a ready state.
- [x] Fixture reset returns the seeded incident in `CREATED` state.
- [x] Happy path reaches `VALIDATED` and produces a report.
- [x] Viewer mutations, validation-before-recovery, and missing approval are safely denied.
- [x] Audit events, evidence, report, and fixture/degraded labels are visible through the API path.
- [x] Decision boundary is visible: CoCo evidence or truthful fixture fallback, cited proposal, deterministic policy, operator approval, fixture recovery, and validation.
- [x] Business impact and the rejected alternative are explained in the recommendation view.
- [x] Backup replay completes successfully with `final_status=validated`.
- [x] Backup replay proves viewer denial, validation gating, and missing approval.
- [ ] Any recording contains no credentials, raw PII, or generated SQLite files.

## Submission proof capture

For a live demo, capture these moments in order:

1. The incident and business impact before investigation.
2. The `CoCo live path` badge, or the truthful `CoCo fallback` badge if the live adapter degrades.
3. Evidence cards with citations and the decision-boundary strip.
4. The blocked pre-approval execution showing `approval_required`.
5. Operator approval, fixture recovery reference, validation, audit timeline, and RCA.

The repository remains honest in either mode: live evidence is marked `live`, fallback evidence is marked `fixture`, and recovery is always labeled fixture-only.

The verified browser proof for this checkout was completed in an isolated temporary runtime. The proof captures are stored outside the repository in the Codex submission-proof folder; do not commit them, the temporary SQLite database, or server logs. The external backup recording remains the only unchecked submission asset.
