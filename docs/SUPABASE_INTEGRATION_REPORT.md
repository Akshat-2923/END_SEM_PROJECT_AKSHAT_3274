# DharaScope — Live Supabase Integration & Conflict Audit Report

- **Date:** 2026-11-26
- **Project Reference:** `yvfeiedyuvdzkoxuycpe`
- **Project Name:** `Akshat-2923's Project`
- **Region:** `ap-southeast-2` (Sydney)
- **Project Status:** `ACTIVE_HEALTHY`
- **Supabase API URL:** `https://yvfeiedyuvdzkoxuycpe.supabase.co`
- **Inspection Channel:** Authenticated Supabase MCP (`supabase_mcp`)

---

## 1. Executive Summary

Live inspection of the connected Supabase project (`yvfeiedyuvdzkoxuycpe`) confirmed:

1. **PostGIS Activation & Spatial Execution (Completed & Verified):** Enabled `postgis` (`3.3.7`) inside the `extensions` schema and verified unqualified WGS84 geometry validation (`ST_IsValid`) and geodetic ellipsoidal area calculation (`ST_Area(ST_GeogFromText(...))`) execute cleanly over the default `search_path`.
2. **Private Storage Bucket Provisioning (Completed & Verified):** Created DharaScope's three missing private buckets — `rasters`, `maps`, and `reports` (`public = false`) — while preserving the existing `posts` (`public = true`) bucket and its policies untouched.
3. **Database Schema & Trigger Conflict (Phase 4 Hard Stop Executed):** The remote `public` schema is **not empty**; it hosts an existing, populated social-media application (`8` users in `auth.users` and `public.profiles`, `12` rows in `public.posts`, `12` rows in `public.follows`, plus `comments`, `conversations`, `conversation_participants`, and `messages`) alongside an active `on_auth_user_created` signup trigger enforcing `@gmail.com` email restrictions. In compliance with non-destructive safety rules, Alembic DDL migrations (`53ebad6d6a09`, `5903f15a19ed`) were **halted cleanly** before altering or overwriting any remote table, row, trigger, or security policy.

---

## 2. Connected Supabase Environment Inspection

| Component | Live Observed Value | Compatibility Note |
| :--- | :--- | :--- |
| **PostgreSQL Engine** | `PostgreSQL 17.11 on aarch64-unknown-linux-gnu, compiled by gcc (GCC) 15.2.0, 64-bit` | Compatible with SQLAlchemy 2.x + `psycopg2-binary` (local verification used PG 16.15) |
| **PostGIS Extension** | `postgis 3.3.7` in schema `extensions` (`GEOS 3.14.1`, `PROJ 9.7.1`) | Compatible with GeoAlchemy2 `GEOMETRY(POLYGON, 4326)` and `Geography` checks |
| **Default `search_path`** | `"\"$user\", public, extensions"` | Allows unqualified PostGIS calls (`ST_GeomFromText`, `ST_IsValid`, `ST_Area`) |
| **Active SQL Role** | `postgres` (`rolbypassrls = true`, `rolcreaterole = true`, not member of `supabase_storage_admin`) | Can enable extensions and manage `public` DDL, cannot alter `supabase_storage_admin`-owned `storage.objects` policies |
| **System `auth` Functions** | `auth.uid()`, `auth.role()`, `auth.jwt()` owned by `supabase_auth_admin` | Preserved untouched; Alembic `5903f15a19ed` detects existing functions cleanly |
| **Client Keys Configured** | Legacy `anon` JWT key + modern `sb_publishable_...` key (`id: cb40021c-6d28-4061-bc7d-7aced9cc62f9`) | Verified present without exposing raw secrets |
| **Alembic State** | `public.alembic_version` absent; `supabase_migrations` empty (`[]`) | Expected until dedicated database migration target is resolved |
| **RLS Role (`dharascope_app`)** | Absent (`dharascope_app_role_exists = false`) | Pending Resolution Option A or Option B below |

---

## 3. Remote Schema vs. DharaScope Expected Schema Comparison

### 3.1 Existing Tables in Remote `public` Schema (Preserved Untouched)

All 7 existing tables have Row-Level Security enabled (`rowsecurity = true`, `relforcerowsecurity = false`) and belong to a pre-existing social application:

| Remote Table | Live Row Count | Purpose / Relationships | Collision with DharaScope |
| :--- | :---: | :--- | :--- |
| `public.profiles` | `8` | FK to `auth.users(id)`; referenced by `posts`, `comments`, `messages`, `conversation_participants` | **DIRECT NAME & SCHEMA COLLISION** with DharaScope `profiles` |
| `public.posts` | `12` | Social posts referencing `public.profiles(id)` | Unrelated external application data |
| `public.follows` | `12` | Follower/following edges | Unrelated external application data |
| `public.comments` | `0` | Comments referencing `posts` and `profiles` | Unrelated external application data |
| `public.conversations` | `0` | Messaging rooms | Unrelated external application data |
| `public.conversation_participants` | `0` | Conversation membership | Unrelated external application data |
| `public.messages` | `0` | Direct messages | Unrelated external application data |

### 3.2 `public.profiles` Detailed Schema & Privacy Mismatch

| Aspect | Live Remote `public.profiles` | Expected DharaScope `profiles` ([profile.py](../src/database/models/profile.py)) |
| :--- | :--- | :--- |
| **Columns** | `id (uuid PK)`, `username (text NOT NULL)`, `email (text NOT NULL)`, `avatar_url (text)`, `bio (text)`, `followers_count (int4 default 0)`, `following_count (int4 default 0)`, `created_at (timestamptz)` | `id (uuid PK)`, `email (varchar(255) UNIQUE NOT NULL)`, `full_name (varchar(255) NULL)`, `role (varchar(50) CHECK ('user','admin'))`, `quota_monthly_runs (int CHECK >= 0)`, `created_at (timestamptz)`, `updated_at (timestamptz)` |
| **RLS Policies** | `"Public profiles are viewable by everyone."` (`SELECT`, `roles = {public}`, `qual = true`) | Forced RLS (`FORCE ROW LEVEL SECURITY`) restricting visibility strictly to `auth.uid() = id OR auth.role() = 'admin'` |
| **Auth Signup Trigger** | `on_auth_user_created` $\to$ `public.handle_new_user()` rejects non-`@gmail.com` signups and inserts `username`/`avatar_url`/`bio` into `public.profiles` | App provisions profile via [auth.py](../src/auth.py) `get_or_create_profile()` without setting `username` |

### 3.3 Missing DharaScope Objects in Remote Project

The following objects required by DharaScope are currently absent from `yvfeiedyuvdzkoxuycpe`:

1. `public.aois` (`geometry(Polygon, 4326)` + GiST index `idx_aois_geometry` + area/vertex constraints)
2. `public.analysis_runs` (temporal satellite analysis metadata + status constraints)
3. `public.water_metrics` (`1:1` NDWI areas and 4-class transitions)
4. `public.analysis_artifacts` (object storage metadata + retention tracking)
5. `public.alembic_version` (expected revision: `5903f15a19ed`)
6. `dharascope_app` PostgreSQL non-superuser RLS role (`NOSUPERUSER NOBYPASSRLS`)

---

## 4. Storage Provisioning & Permission Boundary Audit

### 4.1 Bucket Inventory After Phase 6

| Bucket ID / Name | Privacy Flag (`public`) | Ownership / Origin | Status |
| :--- | :---: | :--- | :--- |
| `posts` | `true` | Pre-existing external social app bucket | Preserved untouched (`4` policies on `storage.objects`) |
| `rasters` | `false` | DharaScope GeoTIFF / NDWI raster artifacts | **Created as Private (`public = false`)** |
| `maps` | `false` | DharaScope 300 DPI PNG cartography artifacts | **Created as Private (`public = false`)** |
| `reports` | `false` | DharaScope ReportLab PDF & CSV manifests | **Created as Private (`public = false`)** |

### 4.2 `storage.objects` Policy Permission Boundary

- Live inspection via `pg_class` and `pg_has_role` confirmed `storage.buckets` and `storage.objects` are owned by `supabase_storage_admin` (`rls_enabled = true`), and the `postgres` role does not hold `supabase_storage_admin` membership (`postgres_has_storage_admin_usage = false`).
- Consequently, `CREATE POLICY ... ON storage.objects` cannot be executed directly via SQL MCP (`must be owner of table objects`).
- **Security Impact:** Because `storage.objects` has RLS enabled (`rowsecurity = true`) and zero permissive policies exist for `rasters`, `maps`, or `reports`, unauthenticated/anonymous HTTP clients are **denied by default**, while DharaScope's server-side [storage.py](../src/storage.py) accesses private artifacts safely using `SUPABASE_SERVICE_ROLE_KEY` (`service_role` carries `rolbypassrls = true`). Optional per-user client `SELECT` policies (`(storage.foldername(name))[1] = auth.uid()::text`) can be added directly inside **Supabase Dashboard $\to$ Storage $\to$ Policies**.

---

## 5. Supabase Security Advisor Audit (`get_advisors` `security`)

The live security linter reported 4 warning categories on the pre-existing project configuration (none originating from DharaScope objects):

1. `0011_function_search_path_mutable` (WARN): Existing `public.create_conversation_with_participants` has a mutable `search_path`.
2. `0028_anon_security_definer_function_executable` (WARN): `public.create_conversation_with_participants(user1 uuid, user2 uuid)` and `public.rls_auto_enable()` are executable by `anon`.
3. `0029_authenticated_security_definer_function_executable` (WARN): Same two functions are executable by `authenticated`.
4. `auth_leaked_password_protection` (WARN): Supabase Auth leaked password check (HaveIBeenPwned) is currently disabled.

---

## 6. Recommended Resolution Paths (Awaiting Authorization)

### Option A — Provision a Dedicated Empty Supabase Project (Strongly Recommended)

1. Create a fresh Supabase project dedicated exclusively to DharaScope (keeps DharaScope's `profiles`, `aois`, `analysis_runs`, `water_metrics`, `analysis_artifacts`, `dharascope_app` role, and auth signups completely isolated from existing social-app users and the `@gmail.com` trigger).
2. Enable `postgis` (`CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;`), provision private buckets (`rasters`, `maps`, `reports`), and apply Storage policies in Dashboard.
3. Run `.venv\Scripts\alembic.exe upgrade head` against the dedicated project's IPv4 Session Pooler `DATABASE_URL` cleanly with zero conflicts (`53ebad6d6a09` $\to$ `5903f15a19ed`).

### Option B — Keep Sharing `yvfeiedyuvdzkoxuycpe` via Isolated Schema (`dharascope`)

If DharaScope must share project `yvfeiedyuvdzkoxuycpe` instead of creating a new project:

1. Obtain explicit approval to scope DharaScope's SQLAlchemy models (`Base.metadata = MetaData(schema="dharascope")`), Alembic `version_table_schema="dharascope"`, and migrations into a dedicated PostgreSQL `dharascope` schema so `public.profiles` and `public.posts` remain completely undisturbed.
2. Review/adjust `public.handle_new_user()` on `auth.users` if non-`@gmail.com` accounts need permission to register in Supabase Auth.
