# Azure Database for PostgreSQL Flexible Server Integration Guide

**Document Version:** 1.0.0  
**Phase:** 2.8 — Cloud Deployment Preparation  
**Target Environment:** PostgreSQL 16 + PostGIS 3.6.x on Azure Database for PostgreSQL Flexible Server  
**Application Platform:** DharaScope Backend (FastAPI, SQLAlchemy 2.0, GeoAlchemy2, Alembic)

---

## 1. Executive Summary & Architecture

DharaScope provides dual database compatibility:
1. **Local Development:** Standard local PostgreSQL 16 instance with PostGIS 3.6 running on `localhost:5432`, requiring no mandatory SSL configuration.
2. **Cloud Production Deployment:** Azure Database for PostgreSQL Flexible Server running PostgreSQL 16 with PostGIS 3.6, TLS/SSL 1.2+ encryption enforced, connection pooling optimized for cloud instance limits, and Row-Level Security (RLS) fully preserved.

The architecture decouples the database layer from proprietary cloud-vendor lock-in, enabling zero-code changes between local and cloud runtimes through declarative environment configuration.

```
+-----------------------------------------------------------------------------------+
|                              DharaScope Backend Layer                             |
|                                                                                   |
|   +-----------------------+     +--------------------+     +------------------+   |
|   |   FastAPI Dependency  |     |   SQLAlchemy 2.0   |     |    GeoAlchemy2   |   |
|   |  (RLS Context Inject) | --> |  (QueuePool + SSL) | --> | (PostGIS 3.6 OGC)|   |
|   +-----------------------+     +--------------------+     +------------------+   |
+-----------------------------------------------------------------------------------+
                                          |
                +-------------------------+-------------------------+
                |                                                   |
                v                                                   v
+-------------------------------+               +---------------------------------------+
|       Local Development       |               |     Azure PostgreSQL Flexible Server  |
|  PostgreSQL 16 + PostGIS 3.6  |               |       PostgreSQL 16 + PostGIS 3.6     |
|  - Host: localhost:5432       |               |  - Host: *.postgres.database.azure.com|
|  - SSL: Optional / Off        |               |  - SSL: Enforced (require / verify-ca)|
|  - QueuePool: Default (5/10)  |               |  - QueuePool: Managed (5/10, rec:1800)|
|  - RLS: auth.uid() / SET LOCAL|               |  - RLS: auth.uid() / SET LOCAL        |
+-------------------------------+               +---------------------------------------+
```

---

## 2. Azure Flexible Server Provisioning & Configuration

### 2.1 Recommended SKU Specifications

| Tier | Workload / Purpose | Recommended SKU | vCPU / RAM | Connection Limit | Storage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Development / Evaluation** | Staging, academic evaluation, testing | `Standard_B1ms` or `Standard_B2s` | 1-2 vCPU / 2-4 GiB | 50 – 100 | 32 GiB Premium SSD |
| **Production Workload** | Continuous monitoring, multi-user runs | `Standard_D2s_v5` (General Purpose)| 2 vCPU / 8 GiB | 150 – 250 | 128 GiB Premium SSD |

### 2.2 Server Parameter Configuration (`azure.extensions`)

> [!IMPORTANT]
> Azure Database for PostgreSQL Flexible Server manages extensions through an allow-list server parameter. Before installing PostGIS, the `azure.extensions` parameter must be explicitly configured.

1. Navigate to your Azure PostgreSQL Flexible Server in the **Azure Portal**.
2. Under **Settings**, select **Server parameters**.
3. Search for the parameter: `azure.extensions`.
4. Add `POSTGIS` and `UUID-OSSP` to the comma-separated list:
   ```text
   POSTGIS,UUID-OSSP
   ```
5. Click **Save**. The server dynamically loads the extensions without requiring a full server restart.

Alternatively, configure via Azure CLI:
```bash
az postgres flexible-server parameter set \
  --resource-group <your-resource-group> \
  --server-name <your-server-name> \
  --name azure.extensions \
  --value "POSTGIS,UUID-OSSP"
```

### 2.3 SSL/TLS Security Settings

Azure Flexible Server enforces encrypted transport by default:
- **`require_secure_transport`**: Set to `ON` (default).
- **`ssl_min_protocol_version`**: Set to `TLSv1.2` or `TLSv1.3`.
- **Root Certificate Authority:** Azure Flexible Server certificates are signed by DigiCert Global Root CA (`DigiCertGlobalRootCA.crt.pem` or `DigiCertGlobalRootG2.crt.pem`).
  - Standard mode: `DB_SSL_MODE=require` verifies encryption without local certificate files.
  - Strict mode: `DB_SSL_MODE=verify-ca` or `verify-full` with `DB_SSL_ROOT_CERT=/path/to/DigiCertGlobalRootCA.crt.pem`.

### 2.4 Firewall & Networking Rules

1. Under **Networking**, ensure **Public access (allowed IP addresses)** or **Private endpoint (VNet)** is configured.
2. If connecting from Azure Container Apps, App Service, or Virtual Machines, enable:
   - **"Allow public access from any Azure service within Azure to this server"**.
3. If connecting from local development or CI/CD runners, add specific client IP ranges under firewall rules.

---

## 3. Environment Configuration & Connection Management

### 3.1 Environment Variables

In your deployment environment (e.g., Azure App Service Configuration or `.env` file):

```bash
# Standard SQLAlchemy connection string using psycopg2 driver
DATABASE_URL=postgresql+psycopg2://<db_admin_user>:<db_admin_password>@<your-server-name>.postgres.database.azure.com:5432/dharascope

# SSL/TLS enforcement for Azure (require, verify-ca, or verify-full)
DB_SSL_MODE=require

# Optional path to Root CA certificate bundle for verify-ca or verify-full
# DB_SSL_ROOT_CERT=/etc/ssl/certs/DigiCertGlobalRootCA.crt.pem

# Connection pool sizing (optimized for Azure burstable SKUs)
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# SQL statement logging (False in production)
DB_ECHO=false
```

### 3.2 URL Sanitization & Security Guarantees

DharaScope strictly handles database URLs using `sqlalchemy.engine.make_url`:
- Credentials are never concatenated as raw strings.
- Passwords are automatically redacted (`***`) in application logs, exception traces, and diagnostic endpoints via `get_sanitized_database_url()`.
- Error messages from failed connection attempts have sensitive passwords masked prior to exposure.

### 3.3 Connection Pooling & Idle Timeout Handling

Azure Flexible Server terminates TCP connections idle for longer than ~4 minutes (240 seconds). DharaScope configures:
- **`pool_pre_ping=True`**: Tests connections using a lightweight `SELECT 1` ping before handing them to requests, transparently reconnecting if an idle socket was severed.
- **`pool_recycle=1800`**: Cycles connections every 30 minutes to prevent stale handle accumulation.
- **`pool_size=5` & `max_overflow=10`**: Prevents bursting applications from exhausting Azure PostgreSQL connection limits.

---

## 4. Row-Level Security (RLS) Portability on Azure

A key design feature of DharaScope is that its Row-Level Security architecture does **not** depend on proprietary Supabase C-extensions.

### 4.1 How RLS Functions on Azure PostgreSQL

DharaScope migration `5903f15a19ed_enable_rls_and_policies.py` establishes standard PostgreSQL functions and roles:
1. **Schema & Functions:**
   ```sql
   CREATE SCHEMA IF NOT EXISTS auth;

   CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid AS $func$
     SELECT coalesce(
       nullif(current_setting('request.jwt.claim.sub', true), ''),
       (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
     )::uuid;
   $func$ LANGUAGE sql STABLE;

   CREATE OR REPLACE FUNCTION auth.role() RETURNS text AS $func$
     SELECT coalesce(
       nullif(current_setting('request.jwt.claim.role', true), ''),
       (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role')
     )::text;
   $func$ LANGUAGE sql STABLE;
   ```
2. **Application Role (`dharascope_app`):**
   ```sql
   CREATE ROLE dharascope_app WITH LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
   GRANT USAGE ON SCHEMA public, auth TO dharascope_app;
   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dharascope_app;
   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dharascope_app;
   ```
3. **Session Context Injection:**
   On every API request, `src/auth.py` binds the database connection to the authenticated user's context:
   ```sql
   SET LOCAL ROLE dharascope_app;
   SELECT set_config('request.jwt.claim.sub', :user_id, true);
   SELECT set_config('request.jwt.claim.role', :user_role, true);
   ```

Because these are standard PostgreSQL session parameters (`SET LOCAL ROLE` and `set_config`), RLS operates identically on Azure Database for PostgreSQL Flexible Server.

---

## 5. Database Initialization & Alembic Migrations

To initialize or migrate an Azure Database for PostgreSQL Flexible Server instance:

### Step 1: Create Database
Ensure the target database exists on the Azure server:
```sql
CREATE DATABASE dharascope;
```

### Step 2: Apply Migrations
Execute Alembic migrations from the repository root:
```bash
# Set connection environment variables
export DATABASE_URL="postgresql+psycopg2://<admin_user>:<admin_password>@<server-name>.postgres.database.azure.com:5432/dharascope"
export DB_SSL_MODE="require"

# Apply all migrations up to head
alembic upgrade head
```

Alembic will automatically:
1. Verify `postgis` extension via `CREATE EXTENSION IF NOT EXISTS postgis;`.
2. Generate all spatial tables (`aois`, `analysis_runs`, `profiles`, `system_logs`).
3. Create `auth` schema, `auth.uid()`, and `auth.role()` functions.
4. Create the `dharascope_app` role with `NOBYPASSRLS` and grant table permissions.
5. Apply Row-Level Security policies across all sensitive tables.

To verify migration state:
```bash
alembic current
```

---

## 6. Health Checks & Diagnostic Endpoints

DharaScope provides dedicated, non-sensitive diagnostic endpoints for production monitoring.

### 6.1 Basic Health Check: `GET /health`
Verifies service uptime and basic database ping:
```json
{
  "status": "healthy",
  "app_name": "DharaScope",
  "version": "2.2.0",
  "environment": "production",
  "database": "connected",
  "timestamp": "2026-11-14T14:31:34.995009Z"
}
```

### 6.2 Detailed Database Diagnostics: `GET /health/db`
Returns detailed runtime metrics with credentials completely redacted:
```json
{
  "status": "connected",
  "connected": true,
  "dialect": "postgresql",
  "driver": "psycopg2",
  "host": "dharascope-flexible.postgres.database.azure.com",
  "port": 5432,
  "database_name": "dharascope",
  "username": "dharascope_admin",
  "sanitized_url": "postgresql+psycopg2://dharascope_admin@dharascope-flexible.postgres.database.azure.com:5432/dharascope",
  "ssl_mode": "require",
  "ssl_active": true,
  "server_version": "PostgreSQL 16.15, compiled by Visual C++ build 1944, 64-bit",
  "postgis_version": "POSTGIS=\"3.6.2 3.6.2\" [EXTENSION] PGSQL=\"160\" GEOS=\"3.14.1\" ...",
  "pool": {
    "type": "QueuePool",
    "size": 5,
    "checked_in": 1,
    "checked_out": 0,
    "overflow": -4
  },
  "error": null,
  "timestamp": "2026-11-14T14:31:35.021089Z"
}
```

> [!NOTE]
> Neither the connection password nor secret tokens appear in the diagnostic response or in exception logs.

---

## 7. Troubleshooting & Common Pitfalls

| Symptom / Error | Root Cause | Resolution |
| :--- | :--- | :--- |
| `FATAL: no pg_hba.conf entry for host ..., SSL off` | Client attempted a non-SSL connection while Azure enforces TLS | Ensure `DB_SSL_MODE=require` is set in the environment or append `?sslmode=require` to `DATABASE_URL`. |
| `ERROR: extension "postgis" is not on the allow list` | PostGIS was not enabled in Azure server parameters | In Azure Portal -> Server parameters -> set `azure.extensions = 'POSTGIS,UUID-OSSP'`. |
| `OperationalError: SSL SYSCALL error: EOF detected` | TCP connection was terminated by Azure firewall after 4 minutes idle | Ensure `pool_pre_ping=True` and `pool_recycle=1800` are configured (enabled by default in DharaScope). |
| `FATAL: remaining connection slots are reserved for non-replication superuser connections` | Connection pool exhausted on Burstable SKU (e.g. B1ms with limit 50) | Lower `DB_POOL_SIZE` (e.g., 5) and `DB_MAX_OVERFLOW` (e.g., 10), or upgrade the instance to General Purpose (`Standard_D2s_v5`). |
| `Permission denied for table aois` when executing queries | Role `dharascope_app` lacks permissions on new tables | Run `GRANT ALL ON ALL TABLES IN SCHEMA public TO dharascope_app;` or execute Alembic migration `5903f15a19ed`. |
