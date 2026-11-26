# DharaScope — Project & Cloud Deployment Status

- **Project:** DharaScope — Satellite-Based River Surface Water Dynamics Platform
- **Last Updated:** 2026-11-26
- **Overall Readiness:** `DEDICATED SUPABASE PROVISIONED & LOCAL STACK VERIFIED / READY FOR GITHUB PUSH & RENDER ROLLOUT (v1.1.0)`

---

## 1. Deployment Verification Classification Matrix

| Verification Category | Item / Subsystem | Detailed Observed Status |
| :--- | :--- | :--- |
| **Verified Against Live Supabase** | **Dedicated Project Identity (`iyjvjapdzbnzsrfvrctl`)** | Verified via `supabase_mcp`: project `Dharascope` (`iyjvjapdzbnzsrfvrctl`, region `ap-southeast-1`, `ACTIVE_HEALTHY`, URL `https://iyjvjapdzbnzsrfvrctl.supabase.co`), engine `PostgreSQL 17.12` (`aarch64-unknown-linux-gnu`), confirmed empty before migrations (`0` tables/users/buckets/triggers). Shared project `yvfeiedyuvdzkoxuycpe` untouched. |
| **Verified Against Live Supabase** | **PostGIS Extension & Spatial Query Execution** | Applied `enable_postgis_extension` (`extensions` schema). Confirmed `postgis 3.3.7` (`GEOS 3.14.1`, `PROJ 9.7.1`) and verified `ST_IsValid`, `ST_GeomFromEWKT`, `ST_SRID=4326`, `ST_Area(ST_GeogFromText(...))=4.4048 km²`, and `ST_Centroid`. |
| **Verified Against Live Supabase** | **Alembic Migrations, Role & Forced RLS** | Applied `53ebad6d6a09_initial_schema` & `5903f15a19ed_enable_rls_and_policies`; stamped `public.alembic_version='5903f15a19ed'` (RLS enabled); verified 5 tables, 5 FKs, 18 indexes (`idx_aois_geometry` GiST), non-superuser `dharascope_app` role (`extensions` & `public` `USAGE`, member of `current_user`), untouched `auth.*` helpers (`supabase_auth_admin`), 20 RLS policies, and live rolled-back multi-tenant isolation + escalation block test (`0` rows committed). |
| **Verified Against Live Supabase** | **Private Storage Buckets & Policy** | Created private buckets `rasters`, `maps`, and `reports` (`public = false`) and applied `"Users read own analysis artifacts"` (`FOR SELECT TO authenticated`, folder-scoped to `auth.uid()::text`) on `storage.objects`. |
| **Verified Against Live Supabase** | **Public Auth JWKS Endpoint Reachability** | Confirmed `https://iyjvjapdzbnzsrfvrctl.supabase.co/auth/v1/.well-known/jwks.json` responds `HTTP 200` (`1` signing key). |
| **Verified Locally** | **Backend Pytest & Local FastAPI PostGIS Checks** | Verified `FastAPI` `/health` (`200`, `connected`) and `/health/db` (`PostgreSQL` + `PostGIS 3.6.2`) locally, plus `iyjvjapdzbnzsrfvrctl` Direct & `ap-southeast-1` Session Pooler URL/SSL (`sslmode=require`) parsing, Docker build/run, and full `pytest` regression suite (`211 passed, 1 skipped` before final doc update; re-run after these updates). |
| **Verified Locally** | **Frontend Vitest, Oxlint & Production Build** | Vitest (`6` suites, `19 passed`), Oxlint (`0` errors, `4` warnings), Vite build (`dist/` with `_redirects`, zero localhost/secret leaks), and `git diff --check` verified locally (re-run after final doc update). |
| **Verified Locally** | **Render Blueprint Static Validation (`render.yaml`)** | Validated `type: web` + `runtime: docker`, `runtime: static`, `rootDir: frontend`, `staticPublishPath: dist`, `healthCheckPath: /health`, `envVarKey: RENDER_EXTERNAL_URL`, SPA `/* -> /index.html` rewrite, and zero embedded secrets. |
| **Pending Confirmation / Render Setup** | **GitHub Push & Render Blueprint Provisioning** | Clean deployment commit prepared locally on `main` (push held pending confirmation). No Render MCP/CLI connected; awaiting user connection of repo in Render Dashboard (**Blueprints $\to$ New Blueprint Instance** using `render.yaml`), entering `sync: false` secrets, updating Supabase Auth Redirect URLs, and verifying live deployed endpoints. |
| **Blocked by Missing Local Credentials** | **Direct Local Python $\leftrightarrow$ Remote DB & Storage Roundtrip** | Local host `.env` lacks remote DB password, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_JWT_SECRET` for `iyjvjapdzbnzsrfvrctl` (excluded from MCP OAuth). Direct backend connectivity and live E2E verification run once credentials are supplied in Render (or `.env`). |

---

## 2. Completed Tasks Summary

- [x] **Phases 1–8 Cloud Readiness:** Audited repository ([DEPLOYMENT_AUDIT.md](DEPLOYMENT_AUDIT.md)), implemented PostgreSQL/PostGIS/SSL/Alembic compatibility, startup validation & dynamic CORS, non-root `Dockerfile`, Render frontend normalization & `_redirects`, Storage hardening, [render.yaml](../render.yaml) Blueprint, and [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).
- [x] **Dedicated Supabase Database Provisioning (`iyjvjapdzbnzsrfvrctl`):** Verified clean empty DB, enabled PostGIS `3.3.7` in `extensions`, applied DharaScope initial schema & forced RLS (`53ebad6d6a09` $\to$ `5903f15a19ed`), configured `dharascope_app` role, provisioned private `rasters`/`maps`/`reports` buckets with `SELECT` Storage policy, verified live RLS/spatial SQL & JWKS reachability, and documented full results in [SUPABASE_INTEGRATION_REPORT.md](SUPABASE_INTEGRATION_REPORT.md).

---

## 3. Next Required User Actions

1. **Authorize GitHub Push:** Confirm pushing the updated `main` branch to `origin`.
2. **Provision Render Blueprint (`render.yaml`):** Connect `Akshat-2923/END_SEM_PROJECT_AKSHAT_3274` (`main`) in Render Dashboard and supply `iyjvjapdzbnzsrfvrctl` credentials (`DATABASE_URL` Session Pooler `aws-0-ap-southeast-1.pooler.supabase.com:5432`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` / `SUPABASE_JWKS_URL`, `FRONTEND_URL`).
3. **Configure Supabase Auth Redirects & Run Phase 5 Verification:** Set Site URL & Redirect URLs (`https://<frontend>.onrender.com/**`) in Supabase Dashboard and run live E2E checks across health, auth, AOI creation, Sentinel-2 NDWI processing, map streaming, and PDF/CSV downloads.
