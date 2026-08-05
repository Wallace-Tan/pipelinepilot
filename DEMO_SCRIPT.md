# PipelinePilot Judge Demo

## Opening

“PipelinePilot is not another incident chatbot. It is the control plane between AI investigation and operational action. CoCo can assemble the context, but only typed evidence, deterministic policy, and an accountable operator can move a recovery forward.”

## Start

Terminal 1:

```powershell
cd backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`. If PowerShell resolves a broken user-level npm shim, use `npm.cmd` for install/build/dev.

## Three-minute primary path

1. **Command Center:** Point out the four operational metrics, four AI employees, Fixture/CoCo status, and the high-priority `retail_orders_daily` exception. Explain that `daily_store_revenue` is stale and this is a business-impacting freshness problem, not just a failed task.
2. **Open Workbench:** Click `Open workbench`. Show the exception state, five-stage workflow, evidence from monitoring/Airflow/dbt/Snowflake, citations, high-confidence recommendation, and the approval-required policy.
3. **Prove the gate:** Click `Try execution — show approval gate` before approval. The toast must show `approval_required`. This is the governance moat: recommendation is not authorization.
4. **Operator decision:** Optionally click `Edit proposal`, save a clearer recovery plan, then click `Approve fixture recovery`. The status changes to `Approved`, and the audit timeline records the operator decision and justification.
5. **Recover and validate:** Click `Execute fixture recovery`, then `Validate recovery`. The state reaches `Validated`; the audit timeline and RCA show the outcome, evidence IDs, citations, validation checks, and fixture reference.
6. **Return to Command Center:** Click `Overview`. Active exceptions becomes `0`, freshness becomes `Healthy`, and recovery outcome becomes `Validated`.

## CoCo proof and fallback

The sidebar environment card and top readiness banner must match the actual latest investigation result. `CoCo live path` means live evidence and live decision output were schema-validated. `CoCo fallback` or `Fixture mode` is the correct result when Cortex is unavailable or not verified. Never describe fixture recovery as live recovery.

## Reset and replay

For a clean walkthrough:

```powershell
$headers = @{ "X-Actor-Id" = "demo-admin"; "X-Actor-Role" = "admin" }
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/demo/reset -Headers $headers
```

API-only fallback:

```powershell
.\scripts\demo-replay.ps1
```

The fallback is useful if the browser is unavailable. It exercises the same server-side lifecycle, including viewer denial, missing approval denial, recovery, validation, and final report.

## Capture for submission

- Command Center with metrics, AI employees, and exception queue.
- Workbench with citations, business impact, and policy gate.
- `approval_required` blocked execution.
- Validated audit/RCA result and final Command Center metrics.
