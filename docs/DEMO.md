# PipelinePilot Demo Guide

## Prerequisites

- Python 3.12 and `uv`
- Node.js 22 and npm
- A clean checkout with no committed SQLite database

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

## Reset

```powershell
$headers = @{ "X-Actor-Id" = "demo-admin"; "X-Actor-Role" = "admin" }
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/demo/reset -Headers $headers
```

If the backend is stopped, use `scripts/reset-fixture.ps1`, then restart the backend. Reset recreates the local demo store and seeds the single sanitized schema-drift incident. It is not a production operation.

## Five-Minute Walkthrough

1. **0:00–0:35 — Detect:** Show the failed `retail_orders_daily` incident, high severity, run identifier, and Fixture mode.
2. **0:35–0:55 — Policy:** Open the read-only Policy view; show the immutable fixture policy, version, default-deny behavior, and approval-required schema-drift rule.
3. **0:55–1:35 — Investigate:** Click `Investigate fixture incident`; show monitoring, Airflow log, dbt, and degraded Snowflake metadata evidence.
4. **1:35–2:20 — Recommend:** Show the schema-drift recommendation, high confidence, cited evidence IDs, and `runbook-schema-drift` citation.
5. **2:20–3:05 — Govern:** Show the `APPROVAL_REQUIRED` policy gate. Execution before approval returns a safe `approval_required` error.
6. **3:05–4:00 — Recover:** Approve and execute fixture recovery. Point out the idempotency key, fixture reference, actor, policy version, and audit events.
7. **4:00–4:40 — Validate:** Run validation and show the incident reaching `VALIDATED` only after checks pass.
8. **4:40–5:00 — Report:** Open the report, show evidence-linked RCA, uncertainty, audit trail, and feedback capability.

## Backup API Replay

```powershell
.\scripts\demo-replay.ps1
```

The script resets the fixture, runs the full governed lifecycle, measures elapsed time, and prints the final status. Expected output is represented by `scripts/demo-replay.expected.json`.

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

- [ ] Fresh checkout starts without a committed database or credentials.
- [ ] `uv run pytest` passes.
- [ ] Frontend TypeScript and Vite builds pass.
- [ ] Fixture reset returns the seeded incident in `CREATED` state.
- [ ] Happy path reaches `VALIDATED` and produces a report.
- [ ] Viewer mutations and missing approval are visibly denied.
- [ ] Audit events, evidence, report, and fixture/degraded labels are visible.
- [ ] Backup replay completes successfully.
- [ ] Any recording contains no credentials, raw PII, or generated SQLite files.
