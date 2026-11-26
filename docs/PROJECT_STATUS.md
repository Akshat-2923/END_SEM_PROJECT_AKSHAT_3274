# DharaScope — Project & Cloud Deployment Status

- **Project:** DharaScope — Satellite-Based River Surface Water Dynamics Platform
- **Last Updated:** 2026-11-26
**Overall Readiness:** `LIVE SUPABASE POSTGIS & PRIVATE STORAGE VERIFIED / SCHEMA CONFLICT DOCUMENTED (v1.1.0)`

---

## 1. Deployment Verification Classification Matrix

| Verification Category | Item / Subsystem | Detailed Observed Status |
| :--- | :--- | :--- |
| **Verified Against Live Supabase** | **Project Identity & PostgreSQL Engine (`yvfeiedyuvdzkoxuycpe`)** | Verified via `supabase_mcp`: project `Akshat-2923's Project` (`yvfeiedyuvdzkoxuycpe`, region `ap-southeast-2`, `ACTIVE_HEALTHY`, URL `https://yvfeiedyuvdzkoxuycpe.supabase.co`), engine `PostgreSQL 17.11` (`aarch64-unknown-linux-gnu`), `search_path = "\"$user\", public, extensions"`, legacy `anon` + publishable client keys enabled. |
| **Verified Against Live Supabase** | **PostGIS Extension & Spatial Query Execution** | Enabled `CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;`. Confirmed `postgis 3.3.7` (`GEOS 3.14.1`, `PROJ 9.7.1`) and verified unqualified `ST_IsValid(ST_GeomFromText(..., 4326)) = true` and `ST_Area(ST_GeogFromText(...)) = 4.4048 km²`. |
| **Verified Against Live Supabase** | **Private Object Storage Buckets (`storage.buckets`)** | Provisioned `rasters`, `maps`, and `reports` as strictly private (`public = false`) while preserving pre-existing external bucket `posts` (`public = true`) untouched. Confirmed `storage.objects` has RLS enabled with zero public policies on DharaScope buckets. |
| **Verified Against Live Supabase** | **Schema, Trigger & Security Advisor Audit** | Audited all 7 existing social-app tables (`profiles` 8 rows, `posts` 12, `follows` 12, `comments`/`conversations`/`conversation_participants`/`messages` 0), `on_auth_user_created` (`public.handle_new_user()` `@gmail.com` filter), system-owned `auth.*` helpers, and 4 Security Advisor warnings. Zero existing objects or rows modified. |
| **Verified Locally** | **Backend Pytest Suite** | Local suite ready (`pytest tests/ -v`) covering unit, FastAPI subsystem, Docker/cloud config, and local PostgreSQL 16.15 + PostGIS 3.6.2 RLS/migration verification; re-verified after final Phase 9 edits. |
| **Verified Locally** | **Frontend Vitest, Lint & Production Build** | Vitest (`19` unit/component tests), Oxlint (`0` errors), and Vite production build (`dist/` with `_redirects`, zero localhost/secret leaks) verified locally. |
| **Verified Locally** | **Docker Image, Non-Root Container & Config Parsing** | Verified `dharascope-backend:verify` (`875MB`, `python:3.11-slim-bookworm`, non-root `appuser`, `PROJ_DATA`, geospatial imports, `/health`, `/health/db`, CORS, `alembic current`), plus `get_engine()`/`normalize_database_url()`/`sslmode=require` parsing for `yvfeiedyuvdzkoxuycpe` Direct and `ap-southeast-2` Session Pooler URLs. |
| **Verified Locally** | **Render Blueprint Static Validation (`render.yaml`)** | Validated `type: web` + `runtime: docker`, `runtime: static`, `rootDir: frontend`, `staticPublishPath: dist`, `healthCheckPath: /health`, `envVarKey: RENDER_EXTERNAL_URL`, SPA `/* -> /index.html` rewrite, and zero embedded secrets. |
| **Pending Render Configuration** | **Render Blueprint Provisioning & Env Vars** | **No Render MCP, CLI, or `RENDER_API_KEY` connected automatically.** Pending manual user connection of the GitHub repository in Render Dashboard (**Blueprints $\to$ New Blueprint Instance** using `render.yaml`), entering `sync: false` credentials (`DATABASE_URL` Session Pooler, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` or `SUPABASE_JWKS_URL`, `FRONTEND_URL`), configuring Supabase Auth Redirect URLs, and verifying live deployed `/health`, `/health/db`, CORS, and E2E flows. |
| **Blocked by Credentials or Permissions** | **Dedicated Supabase Project Provisioning (MCP Target)** | Shared project `yvfeiedyuvdzkoxuycpe` was **stopped cleanly** before Alembic `public` DDL due to collision with pre-existing `public.profiles` (`8` rows) and `handle_new_user()`. `supabase_mcp` currently remains pinned to `yvfeiedyuvdzkoxuycpe`; awaiting user reconnection/re-authentication of `supabase_mcp` to the newly created dedicated DharaScope project reference (never modifying `yvfeiedyuvdzkoxuycpe`). See [SUPABASE_INTEGRATION_REPORT.md](SUPABASE_INTEGRATION_REPORT.md). |
| **Blocked by Credentials or Permissions** | **Direct Python `psycopg2` / Service-Role Storage Roundtrip & `storage.objects` Policies** | Local host lacks remote `DATABASE_URL` password, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_JWT_SECRET` (not returned via MCP OAuth). Additionally, `storage.objects` is owned by `supabase_storage_admin` (`postgres` lacks membership), so client Storage `SELECT` policies must be added via **Supabase Dashboard $\to$ Storage $\to$ Policies** if direct client access is ever needed. |

---

## 2. Completed Tasks Summary

- [x] **Phase 1 — Repository Audit ([DEPLOYMENT_AUDIT.md](DEPLOYMENT_AUDIT.md)):** Completed pre-edit audit across backend, frontend, Alembic, RLS, Docker, and storage.
- [x] **Phase 2 — Supabase PostgreSQL + PostGIS Compatibility:** URL scheme normalization (`postgres://`/`postgresql://` $\to$ `postgresql+psycopg2://`), cloud host auto-SSL (`sslmode=require`), Session Pooler pooling defaults, `alembic/env.py` `DATABASE_URL` precedence + `.env` loading, conditional `auth.uid()`/`auth.role()` + `extensions` schema RLS safety (`5903f15a19ed`).
- [x] **Phase 3 — Environment Configuration & CORS:** Startup validation (`validate_startup_config`), dynamic `FRONTEND_URL`/`CORS_ORIGINS` allowlisting, non-secret `.env.example`, production `reload=False` safety.
- [x] **Phase 4 — Docker Backend Verification:** Created [Dockerfile](../Dockerfile) and [.dockerignore](../.dockerignore); built `875MB` image; verified non-root `appuser`, `PROJ_DATA`, geospatial imports, `$PORT` binding, curl healthcheck, `/health`, `/health/db`, CORS, and `alembic current` inside running container.
- [x] **Phase 5 — Frontend Render Readiness:** Removed production `localhost` fallback in [api.ts](../frontend/src/services/api.ts); added `frontend/public/_redirects` SPA fallback; verified production build and Vitest suite.
- [x] **Phase 6 — Storage Hardening:** Added `_normalize_object_path()` traversal prevention, `ensure_private_buckets()`, run-deletion cleanup, and run-specific PDF figure resolution.
- [x] **Phase 7 — Render Blueprint ([render.yaml](../render.yaml)):** Configured Docker Web Service + Static Site linked cleanly via `envVarKey: RENDER_EXTERNAL_URL` without secrets.
- [x] **Phase 8 & 9 — Live Supabase Integration & Conflict Audit ([SUPABASE_INTEGRATION_REPORT.md](SUPABASE_INTEGRATION_REPORT.md)):** Activated PostGIS `3.3.7` on `yvfeiedyuvdzkoxuycpe`, created private buckets (`rasters`, `maps`, `reports`), verified backend Supabase URL/SSL/engine wiring, audited pre-existing `public` schema collision, and halted `public` DDL before modifying external tables.

---

## 3. Next Required User Actions

1. **Point `supabase_mcp` to the Dedicated DharaScope Project:** Reconnect/refresh `supabase_mcp` with your new dedicated `project_ref` (leaving `yvfeiedyuvdzkoxuycpe` untouched) so `postgis`, Alembic migrations (`53ebad6d6a09`, `5903f15a19ed`), `dharascope_app` role, and private Storage buckets/policies can be provisioned cleanly.
2. **Confirm GitHub Push:** Review the clean deployment commit on `main` and explicitly authorize `git push origin main`.
3. **Connect GitHub & Authorize Render Blueprint (`render.yaml`):** In Render Dashboard (**Blueprints** $\to$ **New Blueprint Instance**), authorize the GitHub repo, enter `DATABASE_URL` (Session Pooler `:5432`), `SUPABASE_*`, and `FRONTEND_URL`, configure Supabase Auth Redirect URLs, and run live E2E verification.
