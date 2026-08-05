# Hackathon Status

Updated: 2026-08-05

## Readiness verdict

PipelinePilot is submission-ready as a deterministic, fixture-backed governed recovery vertical slice. The primary judge workflow is now visible in the UI:

`Command Center → Exception Workbench → evidence and policy → approval gate → fixture recovery → validation → audit/RCA`

The product remains positioned as the governed recovery layer between CoCo investigation and operational action. It is not presented as a generic incident chatbot or as live production recovery.

## PRD audit

| Area | Status | Evidence / remaining gap |
| --- | --- | --- |
| Incident detection and realistic seeded data | Implemented | Sanitized retail schema-drift fixture, Airflow run, dbt failure, Snowflake metadata, and stale `daily_store_revenue`. |
| Cross-system evidence and citations | Implemented | Typed evidence cards show source, mode, summary, and runbook citation. |
| CoCo context path | Partial | Opt-in CLI bridge and truthful live/fallback labels exist; live verification depends on a locally authenticated `cortex` session. |
| Deterministic policy gate | Implemented | Server-side approval-required rule, default deny, operator identity, fingerprint binding, and no direct production writes. |
| Operator approval / rejection | Implemented | Approval and rejection call the governed API and update incident state. |
| Editable proposed action | Implemented | Operator-facing plan can be edited; the canonical policy action remains `schema_drift_recovery`, and the edited plan is captured in approval justification. |
| Fixture recovery and validation | Implemented | Recovery requires matching approval; validation closes the seeded incident and creates audit/report evidence. |
| Command Center / exception queue | Implemented | Metrics, AI employee health, high-priority exception, and live status update are derived from persisted incident state. |
| Audit history and RCA | Implemented | Timeline includes action, actor, outcome, timestamp, and approval justification; report shows typed evidence-linked RCA, impact, and alternatives. The optional Admin audit index is read-only. |
| Typed recommendation impact and alternatives | Implemented | `recommendation.v2` persists impact and structured alternatives through the fixture and CoCo decision adapters. |
| Prior-incident retrieval | Implemented | Sanitized historical incident records are lexically retrieved and supplied to the CoCo decision prompt. |
| Production integrations, auth, live recovery writes | Deferred | Explicitly outside the final-hour scope and never claimed by the demo. |

## Prioritized checklist

### P0 — completed for the submission slice

- [x] Command Center with operational metrics and deterministic AI employee health.
- [x] Exception queue opens the seeded high-priority incident in Workbench.
- [x] Workbench shows proposed action, why it was raised, evidence, citations, confidence, risk, policy, and business impact.
- [x] Pre-approval execution visibly fails closed with `approval_required`.
- [x] Operator can approve, reject, or edit the operator-facing recovery plan.
- [x] Status and metrics refresh after each governed action.
- [x] Audit timeline shows approval outcome and justification.
- [x] Runbook library provides a matched procedure, searchable fixture catalog, and a direct workbench handoff.
- [x] Audit log provides an incident-scoped event stream with local filtering and explicit fixture-boundary labeling.
- [x] Workspace search covers the seeded incident, evidence, runbook citations, and audit events without implying a production search service.
- [x] Recommendation contract persists typed business impact and structured alternatives.
- [x] CoCo decision context can retrieve sanitized prior incidents without exposing raw records.
- [x] Audit log offers an optional Admin-authorized cross-incident index while preserving the incident-scoped default.
- [x] Fixture recovery and validation reach `VALIDATED`.
- [x] Frontend production build passes.
- [x] README, demo script, fallback path, reset command, and live-mode honesty are documented.

### P1 — useful follow-up, not required for submission

- [ ] Policy editing with version creation and admin review.
- [x] Workbench agent/execution detail panel backed by persisted policy, approval, and execution API state.
- [x] Dedicated agent/execution detail pages backed by first-class `/agent` and `/executions/{execution_id}` API resources.
- [x] Cross-exception queue filtering with multiple sanitized seeded records; secondary records remain read-only and the governed walkthrough stays on the schema-drift incident.
- [x] Browser automation and accessibility smoke coverage for reset, investigation, policy denial, approval, recovery, validation, final metrics, and detail resources.
- [ ] Live Cortex verification in the target environment.

### Deferred by design

- Embeddings, RAG, Slack/Jira, multi-pipeline routing, production recovery adapters, production authentication, and a policy editor.

## Validation evidence

- `frontend`: `npm.cmd run build` passes (TypeScript project build plus Vite production build); `npm.cmd run dev -- --host 127.0.0.1` reaches the Vite ready state using the Windows-safe config loader.
- `frontend`: no lint command is configured in `frontend/package.json`; no unsupported lint command is claimed.
- `backend`: `uv 0.12.1` and the bundled Python 3.12 runtime are available. `uv sync` completes from `backend`, and `uv run pytest` passes the full suite (`50 passed`, with only environment/deprecation warnings).
- Runtime smoke test: `/health` returned `ok`, `/v1/demo/status` returned fixture mode with `database_ready=true`, and `scripts/demo-replay.ps1` completed with `final_status=validated` in `0.97s` against an isolated temporary demo database.
- `scripts/demo-replay.ps1`: now parses PowerShell error envelopes reliably and verifies viewer denial, validation-before-recovery gating, missing approval, recovery, validation, and final report output against `scripts/demo-replay.expected.json`.
- `scripts/verify-submission.ps1 -SkipInstall` passes the clean-checkout preflight: backend tests, frontend build, and tracked-file hygiene report zero sensitive tracked files.
- Browser proof: an isolated frontend/backend run completed reset, investigation, evidence review, pre-approval denial, operator approval, fixture recovery, validation, Command Center refresh, and Audit/RCA verification without database edits.
- Browser automation: `npm run test:e2e` passes two Playwright scenarios, including the complete governed lifecycle, queue filtering, named-control checks, and input-label checks. Chromium installation is required once per clean machine.
- Submission proof captures: sanitized Command Center, Workbench, policy-gate, evidence, audit, RCA, and final-state screenshots are stored outside the repository; a recording is not required for this handoff.
- No credentials, raw logs, committed SQLite database, or live-recovery claims are part of the submission slice.

## Demo risk and mitigation

The only material external dependency is live CoCo verification. If Cortex is not ready, use the clearly labeled `Fixture mode` / `CoCo fallback` path. The governed lifecycle, evidence, citations, policy gate, approval, fixture recovery, validation, and audit trail remain demonstrable without credentials.

Current environment evidence: `cortex.cmd --version` returns `Cortex Code v1.1.53`; connection `QE45776` resolves to `bl63744.ap-southeast-5.aws`; the flattened local Airflow project is healthy on `http://localhost:8080` and both Astro and CoCo see `retail_orders_daily`. The read-only metadata preflight passes, but the full headless CoCo decision response is not yet schema-valid, so the live path remains unverified and must not be claimed in the submission.
