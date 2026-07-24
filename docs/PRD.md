# PipelinePilot — Product Requirements Document

## Executive Summary

PipelinePilot is a governance-first incident-response teammate for data engineers. It investigates one failed data-pipeline run, assembles sanitized evidence from Airflow, dbt, and Snowflake through isolated skills, retrieves the relevant runbook, recommends a safe recovery, enforces policy and approval, validates the result, and records an explainable incident report. Snowflake CoCo CLI is the workflow orchestrator; it never holds broad production access or performs direct system operations.

## Critical Review of the Handover

The vision is compelling, but it describes a platform-sized surface area for a seven-day solo build. The following changes preserve the core story while making a credible MVP deliverable:

| Handover assumption | Risk | MVP decision and rationale |
| --- | --- | --- |
| Ten fully integrated skills | Integration and credential work overwhelms the demo | Implement six thin skills for one incident path; use deterministic fixtures behind adapters. This proves orchestration without pretending to operate production systems. |
| RAG over all enterprise knowledge | Corpus preparation, embedding quality, and evaluation are a project of their own | Start with 3–5 curated runbooks and incident records, metadata filters, and lexical retrieval; make embeddings an optional adapter. |
| Autonomous recovery for schema drift | Schema changes and rollbacks are high-risk and often deployment-specific | Recommend a controlled recovery; require operator approval; simulate or sandbox the action. |
| Broad RBAC and policy editor | UI and authorization complexity | Enforce three roles server-side and ship one immutable policy file plus a read-only policy view. |
| “96% confidence” | Uncalibrated confidence harms trust | Return evidence-backed confidence bands and explanations, never unsupported precise probabilities. |
| Dashboard, integrations, learning, and multi-pipeline support | Dilutes the end-to-end workflow | Ship one incident detail view and audit timeline; defer external notifications and multi-pipeline operations. |

## Problem Statement

When a production data pipeline fails, engineers manually traverse logs, transformation results, warehouse context, runbooks, and approvals. Existing monitoring tools surface alerts but rarely connect evidence to organization-specific remediation while preserving control and auditability.

## Market Gap and Business Value

Observability tools identify symptoms; generic copilots generate ungrounded suggestions; runbooks are static. PipelinePilot combines incident context, runbook retrieval, policy enforcement, and human approval in one operational path. It can reduce time-to-triage, standardize recovery decisions, preserve institutional knowledge, and create an auditable record without removing operators from consequential actions.

## User Personas

- **Data Engineer (operator):** investigates failures, approves permitted recovery, and needs evidence rather than a black-box answer.
- **Data Platform Lead (admin):** owns policies and runbooks; needs consistent controls and trend visibility.
- **Analytics Consumer (viewer):** needs a trustworthy incident status and business-impact summary, but cannot execute actions.

## Vision, Scope, and Out of Scope

**Vision:** a reliable AI operations teammate that earns trust through evidence, safeguards, and explainability.

**In scope:** one retail ETL schema-drift scenario; incident intake; sanitized context collection; runbook retrieval; CoCo-directed reasoning; policy evaluation; operator approval; recovery invocation; validation; audit trail; RCA display; feedback capture.

**Out of scope:** production write access, arbitrary SQL, real-time fleet monitoring, a policy authoring UI, Slack/Jira/email, autonomous high-risk remediation, multi-tenant isolation, and claims of ML-calibrated root-cause probabilities.

## Functional Requirements

1. Create and display an incident for a failed `retail_orders_daily` run.
2. Collect normalized evidence via monitoring, logs, dbt, and Snowflake-metadata skills.
3. Redact configured PII patterns before evidence reaches the reasoning or knowledge layers.
4. Retrieve relevant runbooks and prior incidents, exposing document references and excerpts.
5. Produce a structured recommendation: suspected cause, confidence band, evidence, impact, action, and alternatives.
6. Evaluate action policy and return `ALLOW`, `APPROVAL_REQUIRED`, or `DENY` with a reason.
7. Permit only an Operator or Admin to approve an approval-required action.
8. Invoke recovery only through the recovery skill after policy and approval checks.
9. Validate the post-recovery condition through the validation skill.
10. Persist immutable audit events, execution history, an RCA, and optional operator feedback.

## Non-functional Requirements

- A full seeded demo path completes within 60 seconds and tolerates an unavailable external adapter.
- Every recommendation and action is traceable to incident evidence, runbook references, policy version, and actor.
- Service APIs fail safely: no recovery occurs on missing policy, missing approval, or failed evidence collection.
- The UI clearly distinguishes simulated, sandbox, and live integration modes.
- The system is modular: external systems are accessed only through skills/adapters.

## Enterprise Considerations

Server-side RBAC, least-privilege integration identities, secret references rather than secret values, PII minimization/redaction, append-only audit events, policy versioning, action idempotency keys, and explicit approval identity are mandatory design constraints.

## Success Metrics

For the demo: a viewer sees the incident; an operator receives a grounded schema-drift diagnosis; the action is blocked until approval; recovery and validation complete; the audit timeline and RCA explain every transition. Technical targets: 100% of recovery attempts have policy/audit records, 100% of LLM-bound evidence passes redaction, and seeded retrieval returns the schema-drift runbook in the top three results.

## Demo Story

At 09:02 the daily retail orders DAG fails after a supplier adds `loyalty_tier`. PipelinePilot gathers a parser error, dbt freshness failure, and compatible Snowflake metadata. It retrieves the schema-change runbook and identifies schema drift with a **high confidence band**. Policy marks the proposed controlled recovery as approval-required. An operator approves it, the recovery skill runs in demo/sandbox mode, validation passes, and the incident page presents an evidence-linked RCA and audit trail.

## Seven-Day MVP Scope

Day 1: architecture, contracts, seed fixtures, and policy/runbook data. Day 2: backend incident state, audit, and adapters. Day 3: skills and CoCo orchestration contract. Day 4: retrieval, decision envelope, and PII redaction. Day 5: approval/recovery/validation. Day 6: dashboard and end-to-end tests. Day 7: demo hardening, recording, and judge narrative.

## Stretch Goals

Embedding-backed retrieval, incident similarity, feedback-weighted ranking, real Snowflake read-only metadata, dbt artifact ingestion, Airflow read-only adapter, Slack/Jira notification, and multi-pipeline routing.

## Risks and Assumptions

CoCo CLI availability or its local interface may differ from assumptions; isolate it behind an orchestrator adapter with a deterministic fallback. External credentials may be unavailable; the demo must use labeled fixtures. Runbooks must be short and curated. The operator remains accountable for approval. Policy is the source of authority, not model output.
