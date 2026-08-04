# PipelinePilot — Snowflake CoCo CLI Hackathon Strategy

## Submission Positioning

PipelinePilot is a governed operational workflow, not a chat interface. Snowflake CoCo CLI directs a sequence of purpose-built skills, correlates sanitized evidence with organization-specific runbooks, and returns a structured recommendation. A deterministic policy engine and human approval control whether any recovery can happen.

## Judging Criteria Mapping

| Criterion | Feature proof | What to show |
| --- | --- | --- |
| Real-World Relevancy (30%) | Airflow/dbt/Snowflake incident flow, PII redaction, RBAC, runbook-grounded RCA | Start with the engineer’s painful manual workflow; show impact and safeguards. |
| Technical Execution (40%) | Typed skills, parallel context, CoCo CLI bridge, retrieval citations, deterministic policy/approval gate, audit events | Show the CoCo-backed read-only path when credentials are available and the deterministic fallback when they are not. |
| Solution Completeness (30%) | Failure → evidence → decision → policy → approval → recovery → validation → report | Complete the one seeded scenario live, including the initial blocked state. |

## Five-Minute Demo Script

**0:00–0:35 — Problem.** “A daily retail pipeline is failing. The normal workflow is logs, dbt, warehouse metadata, runbook, approvals, retry, validation, then an RCA. PipelinePilot makes that lifecycle governed and explainable.”

**0:35–1:20 — Detection and investigation.** Open the seeded failed incident and click `Investigate fixture incident`. Show the timeline: monitoring, log signature, dbt failure, and intentionally degraded read-only metadata. Point out the persistent Fixture mode and adapter status labels.

**1:20–2:10 — Recommendation and knowledge.** Show the typed deterministic fixture recommendation and retrieved schema-change runbook. Emphasize that only sanitized evidence and cited documents reach the reasoning boundary. Read the structured diagnosis: schema drift, high confidence band, evidence references, and a proposed controlled recovery.

**2:10–3:05 — Governance.** Show policy result: risk and `APPROVAL_REQUIRED`. Attempting execution is unavailable. Explain that the model cannot override the deterministic rule or call Airflow directly.

**3:05–4:00 — Human approval and recovery.** Use the Operator fixture identity to approve. Start the idempotent recovery through the Recovery skill. Show the audit event containing actor, action, policy version, correlation ID, and fixture reference.

**4:00–4:40 — Validation and RCA.** Show validation checks passing and the incident report with evidence, timeline, impact, and next prevention step.

**4:40–5:00 — Close.** “This is not autonomy for its own sake. It is CoCo-orchestrated, organization-aware recovery that preserves operator control and becomes auditable knowledge.”

## Judge Talking Points

- The decision boundary is typed and adapter-based; the demo defaults to a deterministic fallback, while the opt-in path invokes the Snowflake CoCo CLI for structured read-only context and decision support.
- Skills enforce least privilege: read skills cannot execute, execution cannot access arbitrary data.
- The recommendation is grounded in retrieved runbooks and evidence IDs, not generic text.
- Policy is deterministic, versioned, default-deny, and separate from AI output.
- The demo completes a full lifecycle, including deliberate friction at the approval checkpoint.

## Why It Is Distinct

| Typical project | PipelinePilot difference |
| --- | --- |
| Chatbot | Starts from an incident state and progresses through authorized operations. |
| RAG app | Uses retrieval as evidence inside a recovery decision, with citations and policy gates. |
| Dashboard | Explains cause, proposes a constrained action, validates outcome, and records an audit trail. |

## MVP vs Stretch

**Must have:** seeded schema-drift lifecycle; six skills/adapters; CoCo structured decision or clearly labeled fallback; lexical runbook retrieval; PII redaction; deterministic policy; approval; simulated/sandbox recovery; validation; audit/RCA UI.

**Should have:** one read-only live connector, feedback capture, incident list/filtering, polished loading/error states, end-to-end tests, and a backup recording.

**Nice to have:** embeddings/Cortex Search, historical similarity, Slack/Jira, policy editor, multi-pipeline routing, predictive alerts, real write-enabled recovery.

## Risk Assessment and Alternatives

| Risk | Mitigation / fallback |
| --- | --- |
| CoCo CLI setup or output reliability | Put it behind one adapter, validate structured output and citations, and demonstrate a deterministic labeled fallback; never block the governed lifecycle. |
| External credentials/network | Use sanitized fixtures and a visible mode badge; add one read-only connector only if stable. |
| RAG quality | Curate a tiny tagged corpus and show citations; avoid an untested large corpus. |
| Live recovery is unsafe | Use sandbox/simulation with the exact same Recovery skill contract. |
| Demo runs long | Pre-seed incident and documents; keep interaction to investigate, approve, execute, validate. |
| Overbuilding | Freeze scope after the end-to-end path is tested; spend remaining time on reliability and narrative. |

## Submission Checklist

- A fresh reset produces the failing incident and completes the happy path.
- `docs/DEMO.md` and `scripts/demo-replay.ps1` provide browser and API backup paths.
- Every recovery attempt visibly has a policy result, approval (if required), and audit event.
- The UI identifies fixture/sandbox/live mode truthfully.
- Architecture and README explain CoCo’s orchestration role and skill boundaries.
- A short backup recording should be created externally before submission; the repository provides a sanitized replay script and recording checklist.
