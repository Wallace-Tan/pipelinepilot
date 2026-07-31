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

| ID | Title | Description | Depends on | Priority / effort | Acceptance criteria | Commit / branch |
| --- | --- | --- | --- | --- | --- | --- |
| PP-007 | Skill contracts and fixture adapters | Implement typed skill interface plus fixture monitoring/log/dbt/metadata adapters. | PP-002, PP-003 | P0 / 6h | Each returns normalized evidence and degraded status. | `feat(skills): add context adapters` / `feat/pp-007-context-skills` |
| PP-008 | Investigation workflow | Run context skills, redact output, persist evidence/audit events. | PP-004, PP-006, PP-007 | P0 / 5h | An incident reaches `INVESTIGATED` with evidence timeline. | `feat(incidents): orchestrate investigation` / `feat/pp-008-investigation` |
| PP-009 | Read-only live adapter spike | Validate one Snowflake or Airflow read-only adapter behind the same interface. | PP-007 | P1 / 4h | Connector works or a documented fallback remains selected. | `feat(integrations): spike read-only connector` / `feat/pp-009-live-adapter-spike` |

## Milestone 4 — Knowledge and CoCo Decision

| ID | Title | Description | Depends on | Priority / effort | Acceptance criteria | Commit / branch |
| --- | --- | --- | --- | --- | --- | --- |
| PP-010 | Knowledge ingestion/retrieval | Chunk/tag curated docs and implement filtered lexical retrieval. | PP-003, PP-004 | P0 / 4h | Schema runbook is ranked top-three for seeded incident. | `feat(knowledge): add runbook retrieval` / `feat/pp-010-knowledge-retrieval` |
| PP-011 | CoCo orchestration adapter | Implement tool catalog, structured decision schema, output validation, deterministic fallback. | PP-007, PP-010 | P0 / 6h | Decision cites retrieved docs/evidence and fallback is visibly labeled. | `feat(coco): add decision orchestration` / `feat/pp-011-coco-orchestration` |
| PP-012 | Decision evaluation cases | Add expected diagnosis, uncited response, malformed output, and no-knowledge tests. | PP-011 | P0 / 3h | Invalid decisions are rejected and never executed. | `test(coco): cover decision guardrails` / `test/pp-012-decision-evals` |

## Milestone 5 — Governance and Recovery

| ID | Title | Description | Depends on | Priority / effort | Acceptance criteria | Commit / branch |
| --- | --- | --- | --- | --- | --- | --- |
| PP-013 | Policy engine | Evaluate versioned rules, risk, and default-deny decisions. | PP-002, PP-003 | P0 / 4h | Schema-drift action requires approval; unknown action is denied. | `feat(policy): add deterministic evaluator` / `feat/pp-013-policy-engine` |
| PP-014 | Approval workflow | Bind approval/rejection to immutable proposed execution. | PP-004, PP-005, PP-013 | P0 / 4h | Only Operator/Admin can approve; changed action invalidates approval. | `feat(approvals): add governed approval` / `feat/pp-014-approvals` |
| PP-015 | Recovery and validation skills | Implement idempotent demo/sandbox recovery and validation checks. | PP-007, PP-014 | P0 / 5h | No execution without policy+approval; validation gates closure. | `feat(recovery): add controlled execution` / `feat/pp-015-recovery-validation` |

## Milestone 6 — API and Dashboard

| ID | Title | Description | Depends on | Priority / effort | Acceptance criteria | Commit / branch |
| --- | --- | --- | --- | --- | --- |
| PP-016 | Incident REST API | Implement endpoints from architecture, error envelope, correlation/idempotency. | PP-008, PP-011, PP-015 | P0 / 5h | API supports full seeded lifecycle and rejects invalid transitions. | `feat(api): expose incident lifecycle` / `feat/pp-016-incident-api` |
| PP-017 | Incident dashboard | Build list/detail, evidence, recommendation, policy, approval, action state, and audit timeline. | PP-016 | P0 / 8h | A judge can complete the scenario without using API tooling. | `feat(ui): build incident command center` / `feat/pp-017-dashboard` |
| PP-018 | RCA and feedback | Render report and capture operator correction. | PP-016 | P1 / 3h | RCA cites evidence; feedback is auditable. | `feat(incidents): add rca feedback` / `feat/pp-018-rca-feedback` |

## Milestone 7 — Verification and Demo

| ID | Title | Description | Depends on | Priority / effort | Acceptance criteria | Commit / branch |
| --- | --- | --- | --- | --- | --- |
| PP-019 | End-to-end tests | Test detect → investigate → approve → recover → validate → report. | PP-016 | P0 / 5h | Tests cover denial, missing approval, and happy path. | `test(e2e): cover governed recovery` / `test/pp-019-e2e` |
| PP-020 | Demo resilience | Add reset seed, loading/error states, adapter-mode banners, and timing rehearsal. | PP-017, PP-019 | P0 / 4h | Demo restarts cleanly and completes in five minutes. | `chore(demo): harden presentation flow` / `chore/pp-020-demo-hardening` |
| PP-021 | Judge assets | Finalize README, architecture visuals, five-minute script, and backup recording. | PP-020 | P0 / 3h | Another person can run/replay the demo. | `docs: finalize hackathon submission` / `docs/pp-021-submission` |

## Milestone 8 — Stretch (only after PP-021)

PP-022 embedding retrieval (P2/5h), PP-023 live dbt/Airflow adapters (P2/8h), PP-024 incident similarity/feedback ranking (P2/6h), PP-025 Slack/Jira notification (P2/4h), PP-026 policy UI (P2/8h), and PP-027 multi-pipeline routing (P2/8h). Each must retain the contracts and guardrails established above.
