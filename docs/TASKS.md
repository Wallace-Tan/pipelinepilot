# PipelinePilot Implementation Roadmap

Priorities: **P0** must ship for the judged lifecycle; **P1** improves credibility if P0 is stable; **P2** is stretch. Estimates are solo-developer hours and include local verification.

## Milestone 1 — Foundation

| ID | Status | Title | Description | Depends on | Priority / effort | Acceptance criteria | Commit / branch |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PP-001 | Achieved | Scaffold applications | Create backend/frontend structure, configuration, and local docs. | — | P0 / 3h | Apps start with documented, verified commands. | `chore: scaffold application` / `chore/pp-001-scaffold` |
| PP-002 | Achieved | Domain contracts | Define incident, evidence, action, policy, approval, execution, and audit schemas/enums. | PP-001 | P0 / 4h | Contracts validate happy and invalid payloads. | `feat(domain): add incident contracts` / `feat/pp-002-domain-contracts` |
| PP-003 | Achieved | Seed demo dataset | Add sanitized retail schema-drift fixtures, three runbooks, policy, and expected outcomes. | PP-002 | P0 / 3h | Fixture data has no PII and reproduces one failure. | `feat(demo): add schema drift fixtures` / `feat/pp-003-demo-fixtures` |

## Milestone 2 — State and Security

| ID | Status | Title | Description | Depends on | Priority / effort | Acceptance criteria | Commit / branch |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PP-004 | Achieved | Persistence and migrations | Implement repositories/tables from architecture. | PP-002 | P0 / 5h | Incident/audit/execution records persist with foreign keys. | `feat(store): add incident persistence` / `feat/pp-004-persistence` |
| PP-005 | Achieved | RBAC and request identity | Add Viewer/Operator/Admin authorization middleware. | PP-001 | P0 / 3h | Viewer cannot approve or execute; tests cover role matrix. | `feat(auth): enforce rbac` / `feat/pp-005-rbac` |
| PP-006 | Achieved | Redaction service | Detect configured email/card/identifier patterns and preserve redaction metadata. | PP-002 | P0 / 3h | No test PII reaches decision/retrieval payloads. | `feat(security): add evidence redaction` / `feat/pp-006-redaction` |

## Milestone 3 — Context Skills

| ID | Status | Title | Description | Depends on | Priority / effort | Acceptance criteria | Commit / branch |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PP-007 | Achieved | Skill contracts and fixture adapters | Implement typed skill interface plus fixture monitoring/log/dbt/metadata adapters. | PP-002, PP-003 | P0 / 6h | Each returns normalized evidence and degraded status. | `feat(skills): add context adapters` / `feat/pp-007-context-skills` |
| PP-008 | Achieved | Investigation workflow | Run context skills, redact output, persist evidence/audit events. | PP-004, PP-006, PP-007 | P0 / 5h | An incident reaches `INVESTIGATED` with evidence timeline. | `feat(incidents): orchestrate investigation` / `feat/pp-008-investigation` |
| PP-009 | Fallback selected | Read-only live adapter spike | Validate one Snowflake or Airflow read-only adapter behind the same interface. | PP-007 | P1 / 4h | Connector works or a documented fallback remains selected. | `feat(integrations): spike read-only connector` / `feat/pp-009-live-adapter-spike` |

## Milestone 4 — Knowledge and CoCo Decision

| ID | Status | Title | Description | Depends on | Priority / effort | Acceptance criteria | Commit / branch |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PP-010 | Achieved | Knowledge ingestion/retrieval | Load curated runbooks and provide filtered lexical retrieval. | PP-003, PP-004 | P0 / 4h | Schema runbook is ranked for seeded incident. | `feat(knowledge): add runbook retrieval` |
| PP-011 | Fallback selected | Decision adapter and fixture fallback | Validate a deterministic fixture recommendation behind a typed adapter boundary; live CoCo remains unconfigured. | PP-007, PP-010 | P0 / 6h | Fallback identifies its adapter mode/reason and cites available evidence and a matching runbook. | `feat(knowledge): add fixture decision fallback` |
| PP-012 | Achieved | Decision evaluation cases | Reject mismatched, uncited, malformed, and knowledge-missing recommendation output. | PP-011 | P0 / 3h | Invalid decisions never reach governed execution. | `test(api): cover decision guardrails` |

## Milestone 5 — Governance and Recovery

| ID | Status | Title | Description | Depends on | Priority / effort | Acceptance criteria | Commit / branch |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PP-013 | Achieved | Policy engine | Evaluate versioned rules, risk, and default-deny decisions. | PP-002, PP-003 | P0 / 4h | Schema-drift action requires approval; unknown action is denied. | `feat(policy): add deterministic evaluator` / `feat/pp-013-policy-engine` |
| PP-014 | Achieved | Approval workflow | Bind approval/rejection to immutable proposed execution. | PP-004, PP-005, PP-013 | P0 / 4h | Only Operator/Admin can approve; changed action invalidates approval. | `feat(approvals): add governed approval` / `feat/pp-014-approvals` |
| PP-015 | Achieved | Recovery and validation skills | Implement idempotent demo/sandbox recovery and validation checks. | PP-007, PP-014 | P0 / 5h | No execution without policy+approval; validation gates closure. | `feat(recovery): add controlled execution` / `feat/pp-015-recovery-validation` |

## Milestone 6 — API and Dashboard

| ID | Status | Title | Description | Depends on | Priority / effort | Acceptance criteria | Commit / branch |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PP-016 | Achieved | Incident REST API | Expose versioned lifecycle endpoints, error envelopes, correlation, and idempotency. | PP-008, PP-011, PP-015 | P0 / 5h | API supports full seeded lifecycle and rejects invalid transitions. | `feat(api): expose incident lifecycle` |
| PP-017 | Achieved | Incident dashboard | Connect the command center to typed fixture-mode API data and governed controls. | PP-016 | P0 / 8h | A judge can complete the scenario without API tooling. | `feat(ui): connect incident command center` |
| PP-018 | Achieved | RCA and feedback | Expose the typed incident report and auditable operator feedback. | PP-016 | P1 / 3h | RCA cites evidence; feedback is auditable. | `feat(api): add reports and feedback` |

## Milestone 7 — Verification and Demo

| ID | Status | Title | Description | Depends on | Priority / effort | Acceptance criteria | Commit / branch |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PP-019 | Achieved | End-to-end tests | Test the governed lifecycle, denial paths, persistence, idempotency, fallback behavior, and report/feedback output. | PP-016 | P0 / 5h | Automated tests verify API and service behavior, including failure cases. | `test(e2e): cover governed recovery` |
| PP-020 | Achieved | Demo resilience | Provide reset/status services, loading/error states, adapter-mode banners, and timing replay. | PP-017, PP-019 | P0 / 4h | Demo restarts cleanly and has browser/API recovery paths. | `chore(demo): harden presentation flow` |
| PP-021 | Achieved | Judge assets | Provide truthful README, architecture/demo guide, replay output, sanitized browser proof captures, and submission checklist. | PP-020 | P0 / 3h | Another person can run/replay the demo and understand the governed lifecycle from the proof captures and documentation. | `docs: finalize hackathon submission` |

## Milestone 8 — Stretch (only after PP-021)

| ID | Status | Title | Description | Depends on | Priority / effort | Acceptance criteria | Commit / branch |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PP-026 | Achieved | Read-only policy UI | Add a dedicated dashboard view for the active immutable policy, rules, risk, approvals, and default-deny behavior. | PP-016, PP-017 | P2 / 8h | Viewer-readable policy metadata and all active rules are visible with loading/error states; no policy mutation is exposed. | `feat(ui): add policy view` |
| PP-028 | Achieved | Typed agent and execution resources | Expose first-class read-only API resources and dashboard detail views for recommendation provenance, approvals, validation, and execution audit. | PP-016, PP-018 | P1 / 5h | Viewer can load typed agent and execution resources; no resource bypasses policy or fixture boundaries. | `feat(api): add governed detail resources` |
| PP-029 | Achieved | Multi-exception queue | Seed additional sanitized queue records and add status filtering while keeping the schema-drift walkthrough as the only executable recovery path. | PP-017, PP-020 | P1 / 3h | Queue displays multiple records, filters open/resolved states, and secondary records remain read-only. | `feat(ui): add exception queue filtering` |
| PP-030 | Achieved | Browser and accessibility proof | Add Playwright coverage for the primary governed lifecycle and named-control/input-label smoke checks. | PP-020, PP-021 | P1 / 4h | `npm run test:e2e` passes reset, denial, approval, recovery, validation, metrics, queue, and detail-view coverage. | `test(e2e): cover browser governance path` |

The judge-ready frontend also includes lightweight supporting views: a searchable fixture runbook catalog, an incident-scoped audit log with local filtering, an optional Admin-authorized audit index, and local workspace search. Recommendation contracts are now `recommendation.v2` with typed impact and alternatives, and sanitized prior-incident records are available to the decision context. These views remain read-only and clearly label the deferred production boundaries: runbook authoring/version publishing, audit retention/export, identity federation, and a production search index.

The Workbench also exposes a typed agent/execution detail panel, while the dedicated Agent detail and Execution detail views now load first-class read-only resources. Context adapter status, decision status, persisted policy binding, approval actor/justification, validation checks, and fixture execution reference remain rendered from server-owned state.

Remaining stretch: PP-022 embedding retrieval (P2/5h), PP-023 live dbt/Airflow adapters (P2/8h), PP-024 incident similarity/feedback ranking (P2/6h), PP-025 Slack/Jira notification (P2/4h), and PP-027 multi-pipeline routing (P2/8h). Each must retain the contracts and guardrails established above.

Milestone 8 integration note: an opt-in CoCo CLI bridge now covers read-only Airflow/Snowflake context and structured decision support behind the existing contracts. Runtime status is result-based: CoCo is `unverified` until an investigation completes, live evidence is labeled `live`, and unavailable or malformed output retains the deterministic fixture fallback with a visible reason. A deployment supplies its own named, non-production, read-only Snowflake connection; the local Airflow proof is healthy and visible to CoCo, and the read-only metadata preflight can verify the supplied account. The headless structured decision response remains an external prerequisite for a live claim, while recovery remains fixture-only.

Verification assets now include `scripts/prepare-airflow-proof.ps1`, `scripts/verify-coco-live.ps1`, `frontend/playwright.config.ts`, `frontend/tests/demo.spec.ts`, and `docs/LIVE_INTEGRATION.md`. The repository includes a typed CoCo bridge and deterministic fallback; PP-009 remains pending live account/Airflow verification, while PP-011 is achieved through the typed fallback with opt-in live decision support. The clean-checkout preflight, replay, isolated browser walkthrough, automated browser/accessibility suite, and sanitized proof captures are verified; optional video recording support is documented but not required for this handoff.

Milestone 7 status: PP-019, PP-020, and PP-021 are Achieved. Live Cortex verification remains intentionally unverified because credentials and service access are not part of the repository.
