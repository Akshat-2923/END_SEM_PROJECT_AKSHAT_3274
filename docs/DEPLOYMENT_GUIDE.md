# DharaScope Cloud Deployment Guide
## Production Deployment on Supabase (PostgreSQL + PostGIS + Auth + Storage) and Render (Docker Web Service + Static Site)

- **Document Version:** 1.0.0
- **Last Updated:** 2026-11-26
**Related Audit:** [DEPLOYMENT_AUDIT.md](DEPLOYMENT_AUDIT.md) | [SUPABASE_INTEGRATION_REPORT.md](SUPABASE_INTEGRATION_REPORT.md)

---

## 1. Architecture Overview

DharaScope deploys across two managed cloud platforms without self-hosting databases or containerizing static web assets:

1. **Database, Auth & Object Storage — Supabase:**
   - **PostgreSQL 16/17 + PostGIS:** Stores `profiles`, `aois` (`GEOMETRY(POLYGON, 4326)` with GiST spatial index), `analysis_runs`, `water_metrics`, and `analysis_artifacts` metadata, protected by PostgreSQL Row-Level Security (RLS). Verified compatible with PostgreSQL `16.15` + PostGIS `3.6.2` locally and Supabase Cloud PostgreSQL `17.11` + PostGIS `3.3.7` (`extensions` schema).
   - **Supabase Auth (GoTrue):** Issues JWT Bearer tokens (`HS256` legacy JWT secret or `ES256`/`RS256` JWKS) and stores authoritative admin roles in `app_metadata.role`.
   - **Supabase Storage:** Three private buckets (`rasters`, `maps`, `reports`) store GeoTIFFs, 300 DPI PNG cartography, CSV exports, and ReportLab PDF reports off-database.
2. **Backend API — Render Docker Web Service (`dharascope-backend`):**
   - Built from [Dockerfile](../Dockerfile) (`python:3.11-slim-bookworm` + non-root `appuser` + geospatial runtime libraries for Rasterio, Shapely, PyProj, NumPy, Psycopg2).
   - Runs FastAPI via `uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers`.
3. **Frontend Client — Render Static Site (`dharascope-frontend`):**
   - Built directly from `frontend/` using `npm install && npm run build` (`vite build`), publishing static assets from `frontend/dist/` with SPA fallback routing (`/* -> /index.html`).

---

## 2. Supabase Project Setup & Enabling PostGIS

### 2.1 Create Supabase Project
1. Sign in to the [Supabase Dashboard](https://supabase.com/dashboard) and click **New project**.
2. Choose an organization, set a strong database password (avoid special URL-breaking characters or URL-encode them), select a region close to your Render deployment (e.g., `ap-south-1` Mumbai, `ap-southeast-2` Sydney, or `us-east-1` N. Virginia), and wait for provisioning to finish.

> [!WARNING]
> **Use a dedicated Supabase project for DharaScope.** Do not deploy DharaScope's default `public` schema migrations into a shared Supabase project that already defines `public.profiles` or an `auth.users` `handle_new_user()` signup trigger; doing so causes table/column collisions, forces public-read vs. forced-RLS conflicts, and can block signups via foreign application triggers (see [SUPABASE_INTEGRATION_REPORT.md](SUPABASE_INTEGRATION_REPORT.md)).

### 2.2 Enable PostGIS Extension
1. In the Supabase Dashboard sidebar, open **Database** $\to$ **Extensions** (or **SQL Editor**).
2. Search for **`postgis`** and click **Enable** (or run in SQL Editor):
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;
   ```
   > [!NOTE]
   > Supabase installs extensions into the `extensions` schema (which is included in the default `search_path`: `"$user", public, extensions`). Alembic migration `5903f15a19ed` automatically grants `USAGE ON SCHEMA extensions` to the non-superuser `dharascope_app` RLS role when present.

### 2.3 Provision Private Object Storage Buckets & Policies
Create three **private (`Public bucket = OFF`)** buckets in **Storage** $\to$ **Buckets** (or via `INSERT INTO storage.buckets ...` / `SupabaseStorageBackend().ensure_private_buckets()`):
- `rasters`
- `maps`
- `reports`

Although DharaScope streams all downloads through authenticated backend endpoints (`/api/v1/artifacts/{id}/download` and `/api/v1/analyses/{id}/reports/{pdf|csv}`) using `SUPABASE_SERVICE_ROLE_KEY`, you can add defense-in-depth user `SELECT` policies on `storage.objects` in **Supabase Dashboard $\to$ Storage $\to$ Policies** (note that `storage.objects` is owned by `supabase_storage_admin`, so direct `postgres` SQL sessions cannot execute `CREATE POLICY` on `storage.objects`; private `public = false` buckets still deny anonymous clients by default when RLS is enabled):

```sql
-- Restrict direct client object access to each user's top-level UUID folder ({auth.uid()}/...)
CREATE POLICY "Users read own analysis artifacts" ON storage.objects
  FOR SELECT TO authenticated
  USING (bucket_id IN ('maps', 'reports', 'rasters') AND (storage.foldername(name))[1] = auth.uid()::text);
```

### 2.4 Configure Supabase Authentication URLs
1. In the Supabase Dashboard, open **Authentication** $\to$ **URL Configuration**.
2. Set **Site URL** to your deployed Render Static Site origin (e.g., `https://<your-frontend>.onrender.com`).
3. Add `https://<your-frontend>.onrender.com/**` (and `http://localhost:5173/**` if developing locally) under **Redirect URLs**.
4. *(Optional)* To grant administrator privileges to a registered user, set `"role": "admin"` inside `app_metadata` via Supabase Auth Admin API or Dashboard **Authentication** $\to$ **Users** (backend ignores client-writable `user_metadata`).

---

## 3. Obtaining Connection & Auth Credentials

Gather these values from the Supabase Dashboard:

1. **Database Connection String (`DATABASE_URL`):**
   - Open **Project Settings** $\to$ **Database** $\to$ **Connection String** (or **Connect** button in header).
   - Select **Session pooler** (`port 5432`, IPv4-compatible `aws-0-<region>.pooler.supabase.com:5432`, e.g., `aws-0-ap-southeast-2.pooler.supabase.com:5432` for `ap-southeast-2`) for Render Web Services (or Direct connection `db.<project-ref>.supabase.co:5432` if your environment supports IPv6).
   - > [!IMPORTANT]
     > Use **Session Pooler (`:5432`)** or **Direct (`:5432`)**, NOT Transaction Pooler (`:6543`), because DharaScope uses SQLAlchemy prepared statements, `SET LOCAL ROLE`, and Alembic transactional DDL.
   - Example:
     ```text
     postgresql+psycopg2://postgres.<project-ref>:<DB_PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres
     ```
2. **Project API & Auth Keys:**
   - Open **Project Settings** $\to$ **API**:
     - `SUPABASE_URL`: Project URL (`https://<project-ref>.supabase.co`)
     - `SUPABASE_ANON_KEY`: `anon` `public` key
     - `SUPABASE_SERVICE_ROLE_KEY`: `service_role` `secret` key (**backend-only; NEVER pass to frontend**)
3. **JWT Signing Secret:**
   - Under **Project Settings** $\to$ **API** $\to$ **JWT Settings**:
     - `SUPABASE_JWT_SECRET`: JWT Secret (or set `SUPABASE_JWKS_URL` if using asymmetric RS256/ES256 signing keys; note DharaScope automatically resolves `${SUPABASE_URL}/auth/v1/.well-known/jwks.json` for ES256/RS256 tokens).

---

## 4. Running Alembic Database Migrations

Run migrations against your Supabase PostgreSQL instance from your local terminal before (or right after) deploying the backend:

```bash
# In Bash / macOS / Linux:
export DATABASE_URL="postgresql+psycopg2://postgres.<project-ref>:<DB_PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres"
export DB_SSL_MODE="require"
alembic upgrade head
alembic current
```

```powershell
# In Windows PowerShell:
$env:DATABASE_URL="postgresql+psycopg2://postgres.<project-ref>:<DB_PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres"
$env:DB_SSL_MODE="require"
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\alembic.exe current
```

Expected current revision: `5903f15a19ed (head)`.

> [!NOTE]
> Migration `5903f15a19ed` safely detects Supabase's pre-existing `auth` schema (`auth.uid()`, `auth.role()`), avoids modifying system-owned functions, creates `dharascope_app` (`NOSUPERUSER NOBYPASSRLS`), grants `dharascope_app` membership to `current_user`, and enables forced RLS across all 5 tables.

---

## 5. Local Docker Testing (Backend Container)

Before pushing to Render, verify the production container locally using Docker Desktop / Docker Engine:

1. Build the production backend image:
   ```bash
   docker build -t dharascope-backend:local .
   ```
2. Verify geospatial & database driver imports inside the container:
   ```bash
   docker run --rm dharascope-backend:local python -c "import numpy, rasterio, shapely, pyproj, sqlalchemy, geoalchemy2, psycopg2; print('Imports OK:', rasterio.__version__)"
   ```
3. Boot the container wired to your `.env` (containing Supabase `DATABASE_URL`, `SUPABASE_*`, `FRONTEND_URL`):
   ```bash
   docker run --rm -p 8000:8000 --env-file .env \
     -e ENVIRONMENT=production \
     -e PORT=8000 \
     dharascope-backend:local
   ```
4. Verify live health and database connectivity endpoints:
   ```bash
   curl -i http://127.0.0.1:8000/health
   curl -i http://127.0.0.1:8000/health/db
   ```

---

## 6. Deploying to Render

You can deploy both services automatically using [render.yaml](../render.yaml) (**Blueprints** $\to$ **New Blueprint Instance**) or manually via the Render Dashboard. Because no Render MCP/CLI integration is pre-connected in this workspace, authorize the Render GitHub App once in the Render Dashboard when creating the Blueprint.

### 6.1 Option A: Render Blueprint (`render.yaml`)
1. Sign in to [Render Dashboard](https://dashboard.render.com), select **Blueprints** $\to$ **New Blueprint Instance**, and authorize access to your GitHub repository (`Akshat-2923/END_SEM_PROJECT_AKSHAT_3274`, branch `main`).
2. Render automatically parses `render.yaml` and creates:
   - `dharascope-backend` (Docker Web Service)
   - `dharascope-frontend` (Static Site)
   - `VITE_API_BASE_URL` automatically links to `dharascope-backend`'s public `RENDER_EXTERNAL_URL`.
3. Populate all `sync: false` secrets securely in the Render Dashboard when prompted (never commit secrets into `render.yaml`). Note: if your dedicated Supabase project uses asymmetric `ES256`/`RS256` JWT signing keys instead of a legacy `HS256` secret, set `SUPABASE_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json` on `dharascope-backend` (or leave `SUPABASE_JWT_SECRET` set if using `HS256`).
4. Once `dharascope-frontend` provisions, verify its actual `.onrender.com` URL matches `FRONTEND_URL` on `dharascope-backend` (e.g., if Render assigned a random suffix like `-abcd.onrender.com`, update `FRONTEND_URL` and redeploy the backend) and update Supabase **Authentication** $\to$ **URL Configuration**.

### 6.2 Option B: Manual Render Setup

#### Backend Web Service (Docker)
- **Service Type:** Web Service
- **Runtime:** Docker
- **Dockerfile Path:** `./Dockerfile`
- **Health Check Path:** `/health`
- **Environment Variables:**
  - `ENVIRONMENT=production`
  - `DATABASE_URL=<Supabase Session Pooler URL>`
  - `DB_SSL_MODE=require`
  - `DB_POOL_SIZE=5`
  - `DB_MAX_OVERFLOW=10`
  - `DB_POOL_RECYCLE=1800`
  - `SUPABASE_URL=https://<project-ref>.supabase.co`
  - `SUPABASE_ANON_KEY=<Supabase anon key>`
  - `SUPABASE_SERVICE_ROLE_KEY=<Supabase service_role key>`
  - `SUPABASE_JWT_SECRET=<Supabase JWT secret>`
  - `SUPABASE_AUDIENCE=authenticated`
  - `SUPABASE_STORAGE_ENABLED=true`
  - `FRONTEND_URL=https://<your-frontend-service>.onrender.com`
  - *(Optional for live CDSE OData downloads)* `CDSE_USERNAME`, `CDSE_PASSWORD`

#### Frontend Static Site (React + Vite)
- **Service Type:** Static Site
- **Root Directory:** `frontend`
- **Build Command:** `npm install && npm run build`
- **Publish Directory:** `dist`
- **Rewrite / Redirects:** Source `/*` $\to$ Destination `/index.html` (`Action: Rewrite`) — also baked into `frontend/public/_redirects`.
- **Environment Variables:**
  - `VITE_API_BASE_URL=https://<your-backend-service>.onrender.com/api/v1`
  - `VITE_SUPABASE_URL=https://<project-ref>.supabase.co`
  - `VITE_SUPABASE_ANON_KEY=<Supabase anon key>`

---

## 7. CORS & Environment Variable Reference

| Variable | Service | Required in Prod | Description |
| :--- | :--- | :---: | :--- |
| `ENVIRONMENT` | Backend | Yes | Set to `production` to enable strict startup checks & disable dev fallbacks. |
| `DATABASE_URL` | Backend | Yes | Supabase Session Pooler PostgreSQL URL (`postgresql+psycopg2://...`). |
| `DB_SSL_MODE` | Backend | Recommended | TLS mode (`require`); auto-enabled for `.supabase.co`/`.pooler.supabase.com`. |
| `SUPABASE_URL` | Backend | Yes | Supabase project REST base URL (`https://<ref>.supabase.co`). |
| `SUPABASE_ANON_KEY` | Backend & Frontend | Frontend Yes | Public client key; no admin privileges. |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend Only | Yes | Server-side GoTrue & Storage admin key. Never prefix with `VITE_`. |
| `SUPABASE_JWT_SECRET` | Backend Only | Yes (HS256) | JWT verification secret matching Supabase project Auth settings. |
| `SUPABASE_STORAGE_ENABLED` | Backend | Recommended | Set `true` in production so artifacts survive container restarts. |
| `FRONTEND_URL` | Backend | Yes | Primary frontend origin allowed by FastAPI `CORSMiddleware`. |
| `CORS_ORIGINS` | Backend | Optional | Comma-separated additional allowed origins (custom domains). |
| `VITE_API_BASE_URL` | Frontend | Yes | Public URL of deployed Render Backend (`.../api/v1`). |
| `VITE_SUPABASE_URL` | Frontend | Yes | Supabase project URL for browser client login. |
| `VITE_SUPABASE_ANON_KEY` | Frontend | Yes | Supabase anon public key for browser client login. |

### CORS Verification
Confirm CORS headers after deploying:
```bash
curl -i -X OPTIONS "https://<backend>.onrender.com/health" \
  -H "Origin: https://<frontend>.onrender.com" \
  -H "Access-Control-Request-Method: GET"
```
Verify `access-control-allow-origin: https://<frontend>.onrender.com` appears in the response.

---

## 8. Database Verification

Verify connectivity, PostGIS availability, active TLS/SSL, and connection pool health without exposing credentials:

```bash
curl -s https://<backend>.onrender.com/health | jq
curl -s https://<backend>.onrender.com/health/db | jq
```

Expected criteria in `/health/db`:
- `"connected": true`
- `"ssl_active": true`
- `"postgis_version"` populated (e.g. `POSTGIS="3.6..."`)
- `"sanitized_url"` contains `***` instead of any raw password

Verify RLS & tables in Supabase SQL Editor:
```sql
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```
All 5 tables (`analysis_artifacts`, `analysis_runs`, `aois`, `profiles`, `water_metrics`) must report `rowsecurity = true`.

---

## 9. Troubleshooting Common Deployment Failures

| Symptom / Error | Root Cause | Resolution |
| :--- | :--- | :--- |
| **`Invalid production startup configuration; missing or placeholder environment variables`** | Backend container booted with `ENVIRONMENT=production` while required vars are empty or match `.env.example` placeholder strings. | Set all required env vars in Render Dashboard and ensure no placeholder values remain. |
| **`Network is unreachable` / IPv6 error connecting to `db.<ref>.supabase.co`** | Render Web Services use IPv4 egress while Supabase direct connections resolve IPv6 by default. | Switch `DATABASE_URL` to Supabase **Session Pooler** (`aws-0-<region>.pooler.supabase.com:5432`). |
| **`permission denied to set role "dharascope_app"`** | PostgreSQL role membership wasn't granted or migration `5903f15a19ed` wasn't applied. | Ensure you run updated `alembic upgrade head` (`GRANT dharascope_app TO CURRENT_USER`). |
| **`must be owner of function uid` during Alembic migration** | Running an unpatched migration attempting to replace Supabase's `auth.uid()`. | Ensure revision `5903f15a19ed` contains conditional `to_regprocedure('auth.uid()') IS NULL` guards. |
| **Browser blocks API calls with `CORS policy: No 'Access-Control-Allow-Origin'`** | `FRONTEND_URL` missing, has a typo, or lacks exact deployed Render URL scheme/host. | Set `FRONTEND_URL=https://<your-site>.onrender.com` on Render Backend and trigger manual deploy/restart. |
| **404 Not Found on page refresh in React app** | Render Static Site lacks SPA fallback rewrite rule. | Add Rewrite rule `/* -> /index.html` in Render Settings $\to$ Redirects/Rewrites (or deploy via `render.yaml`). |
| **PDF/PNG downloads return 404 after Render restart** | `SUPABASE_STORAGE_ENABLED` is `false`, so files lived only on ephemeral container disk. | Set `SUPABASE_STORAGE_ENABLED=true` and verify `rasters`, `maps`, `reports` private buckets exist in Supabase Storage. |
| **Starter/Free Render tier times out during first request** | Render Free Web Services sleep after 15 min idle (~30–60s cold start). | Wait for cold spin-up on initial `/health` check or upgrade Render instance to `starter`. |
