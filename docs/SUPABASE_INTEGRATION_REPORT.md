# DharaScope — Live Supabase Integration Report

- **Date:** 2026-11-26
- **Dedicated Project Reference:** `iyjvjapdzbnzsrfvrctl`
- **Project Name:** `Dharascope`
- **Region:** `ap-southeast-1` (Singapore)
- **Project Status:** `ACTIVE_HEALTHY`
- **Supabase API URL:** `https://iyjvjapdzbnzsrfvrctl.supabase.co`
- **Previous Shared Project Status:** `yvfeiedyuvdzkoxuycpe` preserved completely untouched (`public` conflict avoided by using dedicated project `iyjvjapdzbnzsrfvrctl`)

---

## 1. Executive Summary

Dedicated Supabase production database provisioning for DharaScope (`iyjvjapdzbnzsrfvrctl`) completed cleanly without modifying the previously shared project:

1. **Clean Environment Confirmed:** Pre-flight inspection verified `iyjvjapdzbnzsrfvrctl` (`PostgreSQL 17.12`, `ap-southeast-1`) had zero `public` tables, zero `auth.users`, zero custom Auth triggers, and zero Storage buckets.
2. **PostGIS Activated & Verified:** Enabled `postgis` (`3.3.7`) in schema `extensions` (`GEOS 3.14.1`, `PROJ 9.7.1`) and verified `ST_IsValid`, `ST_GeomFromEWKT`, `ST_SRID`, `ST_Area(ST_GeogFromText(...))`, and `ST_Centroid` execute over the default `search_path`.
3. **Alembic Schema & RLS Applied in Order:** Applied `53ebad6d6a09_initial_schema` and `5903f15a19ed_enable_rls_and_policies`, created the non-superuser `dharascope_app` role, stamped `public.alembic_version` at `'5903f15a19ed'` (with RLS enabled), enabled `FORCE ROW LEVEL SECURITY` and all 20 tenant-isolation policies, and verified live RLS behavior in a rolled-back subtransaction (`0` leftover rows).
4. **Private Object Storage & Policy Configured:** Provisioned private buckets `rasters`, `maps`, and `reports` (`public = false`) and applied `"Users read own analysis artifacts"` (`FOR SELECT TO authenticated`) on `storage.objects`.
5. **Auth / JWKS Reachability Verified:** Confirmed `https://iyjvjapdzbnzsrfvrctl.supabase.co/auth/v1/.well-known/jwks.json` returns `HTTP 200` (`1` signing key) while preserving Supabase system-owned `auth.uid()`, `auth.role()`, and `auth.jwt()` (`supabase_auth_admin`).

---

## 2. Live Dedicated Environment Details (`iyjvjapdzbnzsrfvrctl`)

| Component | Live Observed Value | Verification Status |
| :--- | :--- | :--- |
| **PostgreSQL Engine** | `PostgreSQL 17.12 on aarch64-unknown-linux-gnu, compiled by gcc (GCC) 15.2.0, 64-bit` | Verified Live |
| **Direct Host** | `db.iyjvjapdzbnzsrfvrctl.supabase.co:5432` | Verified Live + Local URL Config |
| **Session Pooler Host (IPv4)** | `aws-0-ap-southeast-1.pooler.supabase.com:5432` | Verified Local URL/SSL Config (`sslmode=require`) |
| **Default `search_path`** | `"\"$user\", public, extensions"` | Verified Live |
| **PostGIS Extension** | `postgis 3.3.7` in `extensions` (`GEOS 3.14.1`, `PROJ 9.7.1`) | Verified Live (`ST_IsValid=true`, `area_km2=4.4048`) |
| **System Auth Helpers** | `auth.uid()`, `auth.role()`, `auth.jwt()` owned by `supabase_auth_admin` | Preserved Untouched & Tested Live |
| **Client API Keys** | Legacy `anon` JWT key + publishable `sb_publishable_...` key enabled | Verified Present (No Secrets Stored) |
| **Auth JWKS Endpoint** | `https://iyjvjapdzbnzsrfvrctl.supabase.co/auth/v1/.well-known/jwks.json` | Verified HTTP `200` (`1` key) |
| **Migration State** | MCP migrations (`enable_postgis_extension`, `53ebad6d6a09_initial_schema`, `5903f15a19ed_enable_rls_and_policies`); `alembic_version = 5903f15a19ed` | Verified Live |

---

## 3. Schema, Foreign Keys, Indexes & Role Verification

### 3.1 Tables & Row-Level Security State

| Table | RLS Enabled | RLS Forced | Primary Role / Domain |
| :--- | :---: | :---: | :--- |
| `public.profiles` | `true` | `true` | User profiles, `role` (`'user'`/`'admin'`), monthly quotas |
| `public.aois` | `true` | `true` | PostGIS `geometry(Polygon, 4326)`, `0.10–100.00 km²`, `4–500` vertices |
| `public.analysis_runs` | `true` | `true` | Multi-temporal Sentinel-2 execution metadata & status |
| `public.water_metrics` | `true` | `true` | 1:1 NDWI surface water areas and 4-class transitions |
| `public.analysis_artifacts` | `true` | `true` | Object storage path/bucket metadata and retention expiry |
| `public.alembic_version` | `true` | `false` | Alembic revision tracking (`'5903f15a19ed'`), locked from PostgREST APIs |

### 3.2 Foreign Keys & Key Indexes Verified (`pg_constraint` / `pg_indexes`)

- **5 Foreign Keys Verified:**
  - `aois.user_id` $\to$ `profiles.id` (`ON DELETE CASCADE`)
  - `analysis_runs.aoi_id` $\to$ `aois.id` (`ON DELETE SET NULL`)
  - `analysis_runs.user_id` $\to$ `profiles.id` (`ON DELETE CASCADE`)
  - `water_metrics.analysis_run_id` $\to$ `analysis_runs.id` (`ON DELETE CASCADE`)
  - `analysis_artifacts.analysis_run_id` $\to$ `analysis_runs.id` (`ON DELETE CASCADE`)
- **18 Indexes Verified:** Including GiST spatial index `idx_aois_geometry ON public.aois USING gist (geometry)` plus unique indexes (`ix_profiles_email`, `ix_water_metrics_analysis_run_id`) and lookup indexes across `aois`, `analysis_runs`, `analysis_artifacts`, and primary keys.
- **Application RLS Role (`dharascope_app`) Verified:**
  - `rolsuper = false`, `rolbypassrls = false`, `rolcanlogin = true`
  - `pg_has_role(current_user, 'dharascope_app', 'MEMBER') = true` (allows `SET LOCAL ROLE dharascope_app;` by `postgres` without superuser)
  - `has_schema_privilege('dharascope_app', 'public', 'USAGE') = true`
  - `has_schema_privilege('dharascope_app', 'extensions', 'USAGE') = true`
- **20 RLS Policies & Live Isolation Test Verified:**
  - Confirmed 4 policies each (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) across `profiles`, `aois`, `analysis_runs`, `water_metrics`, and `analysis_artifacts`.
  - Executed transactional subtransaction test switching via `SET LOCAL ROLE dharascope_app;` and setting `request.jwt.claim.sub` / `request.jwt.claim.role`: verified User A visibility, User A self-promotion (`UPDATE profiles SET role='admin'`) blocked (`insufficient_privilege`), User B isolation (sees `public` AOI only, `0` User A `analysis_runs`), Admin override, and clean rollback (`0` rows persisted).

---

## 4. Private Storage Buckets & Policies Verification

| Bucket | Public Flag | Access Model |
| :--- | :---: | :--- |
| `rasters` | `false` | Private; backend `SUPABASE_SERVICE_ROLE_KEY` writes/reads; authenticated user `SELECT` scoped by top-level folder `{auth.uid()}/...` |
| `maps` | `false` | Private; backend `SUPABASE_SERVICE_ROLE_KEY` writes/reads; authenticated user `SELECT` scoped by top-level folder `{auth.uid()}/...` |
| `reports` | `false` | Private; backend `SUPABASE_SERVICE_ROLE_KEY` writes/reads; authenticated user `SELECT` scoped by top-level folder `{auth.uid()}/...` |

Applied policy verified in `pg_policies` on `storage.objects`:
- `"Users read own analysis artifacts"` (`FOR SELECT TO authenticated`):
  `bucket_id = ANY (ARRAY['maps'::text, 'reports'::text, 'rasters'::text]) AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)`

---

## 5. Supabase Advisors Summary (`get_advisors`)

- **Security Advisors:**
  - `0008_rls_enabled_no_policy` (`INFO`): Intentional on `public.alembic_version` (blocks external PostgREST access while allowing `postgres` with `rolbypassrls = true` to run Alembic).
  - `0028`/`0029` (`WARN`): Supabase built-in `public.rls_auto_enable()` event-trigger helper flagged by default template.
- **Performance Advisors:**
  - `0003_auth_rls_initplan` (`WARN`): Existing upstream `5903f15a19ed` RLS policies use `auth.uid()`/`auth.role()` directly instead of `(select auth.uid())` (kept faithful to the existing migration; optional future query optimization).
  - `0005_unused_index` (`INFO`): Expected on empty newly created tables (`0` production queries executed yet).

---

## 6. Pending Verification & Manual Deployment Boundaries

- **Local FastAPI vs. Remote DB:** Direct local Python `psycopg2` / Service-Role Storage roundtrip against `iyjvjapdzbnzsrfvrctl` was not run because the database password, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_JWT_SECRET` are not stored locally (`MCP` OAuth does not expose raw secrets). FastAPI `/health` and `/health/db` were verified against local PostgreSQL 16.15 + PostGIS 3.6.2, alongside `iyjvjapdzbnzsrfvrctl` URL/SSL parsing and HTTPS JWKS reachability.
- **Render Deployment:** No Render MCP/CLI integration is present; deploy via [render.yaml](../render.yaml) once GitHub push is confirmed and supply backend/frontend environment variables in Render Dashboard (see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)).
