# PipelinePilot Deployment Guide

This guide covers the deployment shape supported by the repository as it exists today.

PipelinePilot has two deployable parts:

- **Backend:** FastAPI, started with Uvicorn. It persists the demo state in SQLite.
- **Frontend:** React/Vite, compiled to static files in `frontend/dist`. The shipped frontend is [pipelinepilot.vercel.app](https://pipelinepilot.vercel.app/).

The shipped backend is [pipelinepilot-api.onrender.com](https://pipelinepilot-api.onrender.com), with health at `/health`. The repository is configured for this fixture-mode deployment; use the local steps below only when developing or verifying changes.

The default runtime is **fixture mode**. It is suitable for a local demo or a protected evaluation environment. The repository includes starter configuration for Vercel and Render in `frontend/vercel.json` and `render.yaml`. It does not currently provide a production authentication provider or a managed-database adapter.

## 1. Prerequisites

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 22 and npm
- A checkout of this repository

On Windows PowerShell, use `npm.cmd` instead of `npm` if PowerShell resolves `npm` to a broken user-level `npm.ps1`.

## 2. Deploy the backend

From the repository root:

```powershell
cd backend
uv sync
uv run pytest
```

Set the runtime configuration before starting the service. These are the important settings; all settings use the `PIPELINEPILOT_` prefix:

```powershell
$env:PIPELINEPILOT_MODE = "fixture"
$env:PIPELINEPILOT_DATABASE_PATH = "C:\pipelinepilot-data\pipelinepilot.sqlite3"
$env:PIPELINEPILOT_COCO_ENABLED = "false"
```

Start the API. For local-only access, keep the loopback bind:

```powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

For a private server behind a reverse proxy, bind to all interfaces and restrict the port at the firewall:

```powershell
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify the service from another terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected output includes `status: ok` and `mode: fixture`. The application creates the SQLite parent directory, applies migrations, and seeds the sanitized schema-drift fixture on startup.

### Backend configuration reference

| Variable | Default | Guidance |
| --- | --- | --- |
| `PIPELINEPILOT_MODE` | `fixture` | Keep `fixture` for the supported demo deployment. `sandbox` and `live` are enum values, not complete deployment adapters. |
| `PIPELINEPILOT_DATABASE_PATH` | `./pipelinepilot.sqlite3` | Use a persistent, writable path. Do not place the database in an ephemeral deployment directory. |
| `PIPELINEPILOT_CORS_ORIGINS` | `https://pipelinepilot.vercel.app` in `render.yaml` | Comma-separated browser origins allowed to call the API. Add a preview/custom origin only when it is needed. |
| `PIPELINEPILOT_COCO_ENABLED` | `false` | Opt-in only. A CLI login alone does not prove a live PipelinePilot integration. |
| `PIPELINEPILOT_COCO_COMMAND` | `cortex` | Set to the installed CoCo executable, such as `cortex.cmd` on Windows. |
| `PIPELINEPILOT_COCO_CONNECTION` | unset | Use only a dedicated, non-production, read-only connection. |
| `PIPELINEPILOT_COCO_TIMEOUT_SECONDS` | `45` | Increase only when the verified local CoCo workflow requires it. |

Do not commit `.env` files, CoCo connection files, tokens, Airflow credentials, or production logs.

## 3. Deploy the backend to Render

Deploy Render first so you have the API URL to enter in Vercel. The repository includes [`render.yaml`](../render.yaml), so the easiest dashboard path is the Blueprint flow below.

### Option A -- Render Blueprint (recommended)

1. Open [render.com](https://dashboard.render.com/) and sign in.
2. In the top-right, click **New** (or **+ New**) and choose **Blueprint**.
3. Connect GitHub/GitLab if Render asks for permission.
4. Select the repository that contains `render.yaml` and choose the branch to deploy.
5. Review the detected service named `pipelinepilot-api`.
6. Click **Apply** / **Create Blueprint**.
7. If Render asks for values marked as `sync: false`, leave them empty for the initial fixture deployment. Add them later from the service's **Environment** page.
8. Wait for the first deploy to finish. Open the new `pipelinepilot-api` service and copy its public URL, for example `https://pipelinepilot-api.onrender.com`.

The Blueprint creates a Python web service with:

- build command: install `uv`, install the Cortex Code CLI, then run `uv sync --frozen --no-dev` in `backend`;
- start command: create the deployment-local Snowflake connection metadata and run Uvicorn on Render's `$PORT`;
- health check: `/health`;
- a writable `/tmp/pipelinepilot.sqlite3` path for SQLite.

The free-tier Blueprint intentionally uses `/tmp` because persistent disks are not available on the free tier. SQLite state is therefore disposable and can reset when Render restarts or redeploys the service.

### Option B -- Render Web Service (manual dashboard setup)

Use this if you prefer to enter the settings yourself:

1. In the Render Dashboard, click **New** > **Web Service**.
2. Connect the Git provider and select this repository.
3. Set **Name** to `pipelinepilot-api`.
4. Set **Branch** to the branch you want to deploy.
5. Leave **Root Directory** empty because the build must access both `backend` and the repository-level `data` directory.
6. Set **Runtime** to **Python 3**.
7. Set **Build Command** to:

   ```text
   python -m pip install uv && curl -LsS https://ai.snowflake.com/static/cc-scripts/install.sh | sh && cd backend && uv sync --frozen --no-dev
   ```

8. Set **Start Command** to:

   ```text
   bash scripts/render-start.sh
   ```

9. Select the free instance type for a disposable fixture deployment.
10. Click **Advanced**, set **Health Check Path** to `/health`, then create the service.
11. Click the service's **Environment** tab and add the variables in the next section.
12. Add `PIPELINEPILOT_DATABASE_PATH=/tmp/pipelinepilot.sqlite3`.
13. Save with **Save, rebuild, and deploy**.

Render web services must bind to `0.0.0.0` and the platform-provided `PORT`; the repository's `scripts/render-start.sh` already does this. [Render's web-service documentation](https://render.com/docs/web-services) explains this requirement.

The free-tier service uses ephemeral storage. Do not treat its SQLite database as durable, and do not horizontally scale this SQLite-backed service. For durable state, move to a paid Render service with a persistent disk or replace SQLite with a managed database adapter.

After the service is created, verify that the shipped origin is configured. For another Vercel project, open **Environment** in the left sidebar, click **Add Environment Variable**, enter the replacement value, then choose **Save, rebuild, and deploy**:

```text
PIPELINEPILOT_CORS_ORIGINS=https://pipelinepilot.vercel.app
```

You can enter multiple browser origins as a comma-separated value, for example:

```text
https://your-project.vercel.app,https://your-custom-domain.com
```

If you are using fixture mode, leave `PIPELINEPILOT_COCO_ENABLED=false`; no Snowflake credentials are needed. The Render service will still expose the governed fixture workflow.

### Configure the deployment owner's Snowflake account

The service does not contain a Snowflake account ID or a fixed connection name. For a verified read-only CoCo path, set the following Render variables for the account used by that deployment:

```text
PIPELINEPILOT_COCO_ENABLED=true
PIPELINEPILOT_COCO_CONNECTION=pipelinepilot
SNOWFLAKE_ACCOUNT=<org-account>
SNOWFLAKE_USER=<read-only-user>
SNOWFLAKE_PASSWORD=<secret-managed-password>
SNOWFLAKE_ROLE=<read-only-role>
SNOWFLAKE_WAREHOUSE=<read-only-warehouse>
SNOWFLAKE_DATABASE=<database>
SNOWFLAKE_SCHEMA=<schema>
SNOWFLAKE_AUTHENTICATOR=snowflake
```

The Render startup script writes a temporary `connections.toml` containing environment-variable references, sets restrictive file permissions, and passes the selected `PIPELINEPILOT_COCO_CONNECTION` name to CoCo. Replace these values with the deployment owner's account and least-privilege role; never copy the example values from another environment. Snowflake's CoCo CLI supports named connections and environment-backed connection settings; see the [Cortex Code CLI connection documentation](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) and [CLI security guidance](https://docs.snowflake.com/en/user-guide/cortex-code/security).

The connection is deployment-scoped. This repository does not yet implement multi-tenant account onboarding, server-side user authentication, or per-user secret isolation. A single shared Render service therefore uses one configured read-only Snowflake connection. If every user must connect a different account inside one shared deployment, add an authenticated tenant/connection service backed by a secret manager before exposing that capability.

To let another organization use its own Snowflake account today, give it a separate Render service (from the same repository) and a separate Vercel deployment, then set that organization's own `SNOWFLAKE_*`, `PIPELINEPILOT_COCO_CONNECTION`, `PIPELINEPILOT_CORS_ORIGINS`, and `VITE_PIPELINEPILOT_API_URL` values. No source-code change or account-specific constant is required.

Verify the Render service before connecting the frontend:

```powershell
Invoke-RestMethod https://<your-render-service>.onrender.com/health
Invoke-RestMethod https://<your-render-service>.onrender.com/v1/demo/status
```

### Render troubleshooting: `PermissionError: '/var/data'`

If the logs show `PermissionError: [Errno 13] Permission denied: '/var/data'`, the service is still using the paid-tier database path even though the free tier has no mounted disk.

For the free tier, fix it in the Render Dashboard:

1. Open the `pipelinepilot-api` service.
2. Open **Environment**.
3. Set:

   ```text
   PIPELINEPILOT_DATABASE_PATH=/tmp/pipelinepilot.sqlite3
   ```

4. Choose **Save, rebuild, and deploy**.

The service should then start, but all SQLite state is lost when Render restarts or redeploys it. On a paid plan, you can instead attach a disk at `/var/data` and use `/var/data/pipelinepilot.sqlite3`.

## 4. Deploy the frontend to Vercel

First, create the Vercel project. You can build locally first if you want to catch errors:

```powershell
cd frontend
npm install
npm run build
```

### Vercel Dashboard steps

1. Open [vercel.com/dashboard](https://vercel.com/dashboard) and sign in.
2. Click **Add New...** > **Project**.
3. Under **Import Git Repository**, select the repository. If it is not listed, click **Adjust GitHub App Permissions** and grant access to the repository.
4. On **Configure Project**, set **Project Name** to a name such as `pipelinepilot`.
5. Set **Root Directory** to `frontend`, then click **Edit** if Vercel does not automatically detect it.
6. Set **Framework Preset** to **Vite**.
7. Confirm these build settings:

   ```text
   Build Command: npm run build
   Output Directory: dist
   Install Command: npm install
   ```

8. Expand **Environment Variables**.
9. Add the variable below and select **Production** and **Preview**:

   ```text
   Name:  VITE_PIPELINEPILOT_API_URL
   Value: https://<your-render-service>.onrender.com
   ```

10. Click **Deploy**.
11. When the deployment finishes, open the generated Vercel URL. The landing page should load, and `/app` should open the Command Center.

The repository includes [`frontend/vercel.json`](../frontend/vercel.json), which records these settings and keeps the `/app` client-side route working on refresh. Vercel's Git deployment flow exposes the Root Directory, Build Output Settings, and Environment Variables during project creation. [Vercel's deployment documentation](https://vercel.com/docs/git) describes those screens.

If the Render URL was not available when you created the project, open the Vercel project and go to **Settings** > **Environment Variables**. Add or edit this variable for **Production** and **Preview**, click **Save**, then go to **Deployments**, open the latest deployment's **...** menu, and choose **Redeploy**:

```text
VITE_PIPELINEPILOT_API_URL=https://<your-render-service>.onrender.com
```

This variable is intentionally a public frontend URL, not a secret. Vite embeds `VITE_*` values into browser JavaScript at build time. Do not put Snowflake credentials or CoCo tokens in Vercel.

For the Vercel + Render setup, the browser calls the Render API directly using the configured URL. This is cross-origin, so the Render `PIPELINEPILOT_CORS_ORIGINS` value must match the Vercel browser origin. Production builds default to `https://pipelinepilot-api.onrender.com`; `VITE_PIPELINEPILOT_API_URL` can override it. The built frontend calls API paths such as `/health` and `/v1/...` relative to that URL.

```text
https://your-project.vercel.app/       -> frontend
https://your-render-service.onrender.com/health -> backend
https://your-render-service.onrender.com/v1/*   -> backend
```

The `PIPELINEPILOT_API_URL` setting in `frontend/vite.config.ts` configures the Vite development proxy only. The `VITE_PIPELINEPILOT_API_URL` setting configures the compiled frontend for Vercel. Do not put Snowflake credentials in Vercel; only the public Render API URL belongs there.

For a local UI-only preview of the generated files:

```powershell
npm run preview -- --host 127.0.0.1 --port 4173
```

The preview server does not replace the backend reverse-proxy route, so use the normal Vite dev server for the fully working local demo, or place the static files behind a proxy that forwards `/health` and `/v1`.

## 5. Fully working local deployment

Use two terminals.

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

Open `http://127.0.0.1:5173/`. Vite proxies `/health` and `/v1` to `http://127.0.0.1:8000`.

## 6. Smoke test after deployment

Check the backend:

```powershell
Invoke-RestMethod https://your-host/health
Invoke-RestMethod https://your-host/v1/demo/status
```

Then open the frontend and verify:

1. The dashboard loads without an API-unavailable error.
2. The status shows `fixture` and a ready database.
3. The seeded schema-drift incident is visible.
4. Investigation, approval, fixture recovery, and validation complete through the UI.
5. The UI labels recovery as fixture-only.

For repository-level verification before publishing:

```powershell
cd backend
uv run pytest
cd ..\frontend
npm run build
```

The browser proof is documented in [DEMO.md](DEMO.md); it requires Chromium once via `npx playwright install chromium`.

## 7. Production-readiness boundary

Treat the current deployment as a demo or controlled internal evaluation. Before exposing it to production users, implement and verify:

- server-side authentication and real Viewer/Operator/Admin identity mapping;
- HTTPS, secure headers, rate limiting, and a restricted backend network path;
- a managed transactional database with backup, migration, and concurrency handling;
- a production recovery adapter with explicit least-privilege credentials, if recovery writes are ever enabled;
- deployment-managed secrets and log/telemetry redaction;
- a production frontend/API base URL and CORS policy if the services are hosted separately;
- health, readiness, metrics, audit-log retention, rollback, and disaster-recovery procedures.

Do not set `PIPELINEPILOT_MODE=live` or describe the service as live merely because the CoCo CLI is installed. The CoCo path is opt-in and read-only; PipelinePilot must receive valid live evidence before the UI reports a verified live result, and recovery remains fixture-only in this repository.
