# AGENTS.md

## Scope and Current State

- Applies to the repository root unless a deeper `AGENTS.md` exists; read the deepest applicable file first.
- This repository contains a FastAPI backend, Vite React TypeScript dashboard, SQLite persistence, governed fixture recovery workflow, sanitized fixture/runbook data, a read-only Policy view, and an opt-in CoCo CLI bridge for read-only context and structured decision support. Production authentication, live recovery adapters, a formatter, and CI workflow are not present.
- The default runtime is deterministic fixture mode. The CoCo bridge is enabled only with `PIPELINEPILOT_COCO_ENABLED=true`; it must never be represented as live connectivity unless a local `cortex` CLI session has been verified.
- Keep generated caches and build outputs out of source control. Preserve `backend/uv.lock`, `frontend/package-lock.json`, demo scripts, fixtures, tests, and the root `.cortex/` skill configuration.
- Do not invent setup, build, lint, test, or deployment commands. Add them only with the supporting project configuration and update this file in the same change.


## Canonical Local Commands

- Backend setup/test: from `backend`, run `uv sync` and `uv run pytest`.
- Backend dev server: from `backend`, run `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- Frontend setup/build: from `frontend`, run `npm install` and `npm run build`.
- Frontend dev server: from `frontend`, run `npm run dev`.

## Coding Philosophy

- Optimize for a single polished, evidence-backed incident workflow.
- Reliability and governance beat autonomy; prefer deterministic domain behavior around AI reasoning.
- Keep CoCo CLI as the orchestrator and use structured skill contracts for all system interaction.

## Folder, Naming, and Architecture Rules

- Follow the folder boundaries in `docs/ARCHITECTURE.md`; keep domain logic independent of HTTP, UI, and vendor SDKs.
- Use explicit, intent-revealing names: `IncidentService`, `PolicyDecision`, `RecoveryExecution`; avoid `utils`, `helpers`, and untyped catch-all payloads.
- Define skill inputs and outputs as versioned schemas. Each skill has one narrow responsibility.
- Depend inward: API/UI â†’ services â†’ domain. Vendor adapters implement interfaces and do not leak vendor types into domain code.
- Centralize business rules, policy evaluation, redaction, and state transitions; never duplicate them across routes or skills.

## API, Errors, Logging, and Testing

- Version REST endpoints under `/v1`; validate all input; return a stable error code, safe message, and correlation ID.
- Make state-changing endpoints idempotent and authorize every state transition server-side.
- Fail closed for unknown policy, missing approval, invalid skill output, or missing authorization.
- Log structured events with correlation ID, incident/execution ID, actor, action, outcome, and latency. Never log secrets, raw PII, access tokens, or unredacted evidence.
- Add unit tests for domain/policy/redaction logic, contract tests for skills/adapters, and an end-to-end seeded schema-drift path. Do not claim a command is canonical until config or CI establishes it.

## Prompt and Skill Development

- Send CoCo only minimized, sanitized, typed context and retrieved document citations.
- Require structured output with cause, confidence band, evidence IDs, recommendation, and uncertainty. Reject invalid or uncited output.
- Treat model output as advice; Policy Engine determines permission and Recovery Skill performs actions.
- Label fixture, sandbox, and live modes in output and UI.

## Security and Performance

- Enforce Viewer, Operator, and Admin roles on the server. Use least-privilege, per-integration credentials held in a secret manager.
- Audit investigation, policy, approval, execution, validation, and feedback events append-only.
- Fetch independent context in parallel with timeouts; persist partial evidence and make degraded results visible.

## Documentation and Contribution Rules

- Update `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/TASKS.md`, or `docs/HACKATHON.md` when a change affects their contractual decisions.
- Keep demo data sanitized and versioned. Never commit `.env` files, credentials, production logs, or generated secret-bearing artifacts.
- Use Conventional Commit style: `feat(scope): summary`, `fix(scope): summary`, `docs: summary`, `test(scope): summary`.
- PRs should state intent, tests run, security/policy impact, demo-mode impact, and screenshots for UI changes.


## Git Branching Strategy

- Use lightweight trunk-based development: `main` is the always-demo-ready branch.
- Do not create long-lived `develop`, release, or integration branches for normal work.
- Create short-lived branches scoped to one task or architectural boundary, using Conventional Commit-style prefixes such as `feat/policy-engine`, `fix/redaction-leak`, `docs/update-architecture`, `test/schema-drift-path`, or `chore/scaffold-apps`.
- Prefer squash merges into `main` so the final commit follows Conventional Commit style.
- Require review before merging changes that touch policy evaluation, approvals, audit logging, recovery execution, LLM prompts, skill contracts, credentials, or integration code.
- Use git tags for demo and submission milestones, such as `demo-v0.1`, `schema-drift-e2e-ready`, and `hackathon-submission`.
## Code Review Checklist

- Is every external operation behind a skill/adapter?
- Does policy run before recovery and is approval bound to the action?
- Is all LLM-bound context redacted and cited?
- Are errors safe, state transitions idempotent, and audit events written?
- Are new dependencies justified and bounded?

## Things Never to Do

- Never bypass the Policy Engine, approval checks, or audit trail.
- Never call Airflow, dbt, Snowflake, or arbitrary SQL directly from CoCo.
- Never expose PII, secrets, raw production logs, or credentials to an LLM.
- Never tightly couple skills or duplicate business logic.
- Never silently execute a high-risk action or represent fixture behavior as production behavior.

