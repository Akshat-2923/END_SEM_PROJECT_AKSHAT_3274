"""enable_rls_and_policies

Revision ID: 5903f15a19ed
Revises: 53ebad6d6a09
Create Date: 2026-11-07 23:37:29.374445

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5903f15a19ed'
down_revision: Union[str, Sequence[str], None] = '53ebad6d6a09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to enable PostGIS-compatible Row-Level Security (RLS).

    Safely compatible with both standard/local PostgreSQL (creating auth helpers
    when absent) and Supabase-managed PostgreSQL (preserving existing Supabase
    auth schema/functions owned by supabase_auth_admin and granting extensions
    schema usage for PostGIS).
    """
    # 1. Create auth schema and helper functions only when not already provisioned (e.g. local/Azure)
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'auth') THEN
        CREATE SCHEMA auth;
      END IF;
    EXCEPTION WHEN insufficient_privilege THEN
      NULL;
    END
    $$;
    """)

    op.execute("""
    DO $$
    BEGIN
      IF to_regprocedure('auth.uid()') IS NULL THEN
        CREATE FUNCTION auth.uid() RETURNS uuid AS $func$
          SELECT coalesce(
            nullif(current_setting('request.jwt.claim.sub', true), ''),
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
          )::uuid;
        $func$ LANGUAGE sql STABLE;
      END IF;
    EXCEPTION WHEN insufficient_privilege THEN
      NULL;
    END
    $$;
    """)

    op.execute("""
    DO $$
    BEGIN
      IF to_regprocedure('auth.role()') IS NULL THEN
        CREATE FUNCTION auth.role() RETURNS text AS $func$
          SELECT coalesce(
            nullif(current_setting('request.jwt.claim.role', true), ''),
            (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role')
          )::text;
        $func$ LANGUAGE sql STABLE;
      END IF;
    EXCEPTION WHEN insufficient_privilege THEN
      NULL;
    END
    $$;
    """)

    # 2. Create non-superuser application role dharascope_app for RLS enforcement
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'dharascope_app') THEN
        CREATE ROLE dharascope_app WITH LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
      ELSE
        ALTER ROLE dharascope_app WITH NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
      END IF;
      -- Ensure connecting role can execute SET LOCAL ROLE dharascope_app even without SUPERUSER
      BEGIN
        EXECUTE format('GRANT dharascope_app TO %I', current_user);
      EXCEPTION WHEN insufficient_privilege OR duplicate_object THEN
        NULL;
      END;
    END
    $$;

    GRANT USAGE ON SCHEMA public TO dharascope_app;
    DO $$
    BEGIN
      GRANT USAGE ON SCHEMA auth TO dharascope_app;
    EXCEPTION WHEN insufficient_privilege THEN
      NULL;
    END
    $$;
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'extensions') THEN
        GRANT USAGE ON SCHEMA extensions TO dharascope_app;
      END IF;
    EXCEPTION WHEN insufficient_privilege THEN
      NULL;
    END
    $$;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dharascope_app;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dharascope_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO dharascope_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO dharascope_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO dharascope_app;
    """)

    # 3. Enable and force RLS on all 5 tables
    tables = ["profiles", "aois", "analysis_runs", "water_metrics", "analysis_artifacts"]
    for t in tables:
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY;")

    # 4. Profiles policies (Self access; Anti-Privilege Escalation on update)
    op.execute("""
    CREATE POLICY profiles_select_policy ON profiles
      FOR SELECT
      USING (auth.uid() = id OR auth.role() = 'admin');

    CREATE POLICY profiles_insert_policy ON profiles
      FOR INSERT
      WITH CHECK (auth.uid() = id OR auth.role() = 'admin');

    CREATE POLICY profiles_update_policy ON profiles
      FOR UPDATE
      USING (auth.uid() = id OR auth.role() = 'admin')
      WITH CHECK ((auth.uid() = id AND role = 'user') OR auth.role() = 'admin');

    CREATE POLICY profiles_delete_policy ON profiles
      FOR DELETE
      USING (auth.uid() = id OR auth.role() = 'admin');
    """)

    # 5. AOIs policies (Ownership isolation + public view support + admin override)
    op.execute("""
    CREATE POLICY aois_select_policy ON aois
      FOR SELECT
      USING (user_id = auth.uid() OR is_public = true OR auth.role() = 'admin');

    CREATE POLICY aois_insert_policy ON aois
      FOR INSERT
      WITH CHECK (user_id = auth.uid() OR auth.role() = 'admin');

    CREATE POLICY aois_update_policy ON aois
      FOR UPDATE
      USING (user_id = auth.uid() OR auth.role() = 'admin')
      WITH CHECK (user_id = auth.uid() OR auth.role() = 'admin');

    CREATE POLICY aois_delete_policy ON aois
      FOR DELETE
      USING (user_id = auth.uid() OR auth.role() = 'admin');
    """)

    # 6. Analysis runs policies (Strict user ownership + admin override)
    op.execute("""
    CREATE POLICY analysis_runs_select_policy ON analysis_runs
      FOR SELECT
      USING (user_id = auth.uid() OR auth.role() = 'admin');

    CREATE POLICY analysis_runs_insert_policy ON analysis_runs
      FOR INSERT
      WITH CHECK (user_id = auth.uid() OR auth.role() = 'admin');

    CREATE POLICY analysis_runs_update_policy ON analysis_runs
      FOR UPDATE
      USING (user_id = auth.uid() OR auth.role() = 'admin')
      WITH CHECK (user_id = auth.uid() OR auth.role() = 'admin');

    CREATE POLICY analysis_runs_delete_policy ON analysis_runs
      FOR DELETE
      USING (user_id = auth.uid() OR auth.role() = 'admin');
    """)

    # 7. Water metrics policies (Child record inheritance through analysis_runs)
    op.execute("""
    CREATE POLICY water_metrics_select_policy ON water_metrics
      FOR SELECT
      USING (
        EXISTS (
          SELECT 1 FROM analysis_runs
          WHERE analysis_runs.id = water_metrics.analysis_run_id
          AND (analysis_runs.user_id = auth.uid() OR auth.role() = 'admin')
        )
      );

    CREATE POLICY water_metrics_insert_policy ON water_metrics
      FOR INSERT
      WITH CHECK (
        EXISTS (
          SELECT 1 FROM analysis_runs
          WHERE analysis_runs.id = water_metrics.analysis_run_id
          AND (analysis_runs.user_id = auth.uid() OR auth.role() = 'admin')
        )
      );

    CREATE POLICY water_metrics_update_policy ON water_metrics
      FOR UPDATE
      USING (
        EXISTS (
          SELECT 1 FROM analysis_runs
          WHERE analysis_runs.id = water_metrics.analysis_run_id
          AND (analysis_runs.user_id = auth.uid() OR auth.role() = 'admin')
        )
      )
      WITH CHECK (
        EXISTS (
          SELECT 1 FROM analysis_runs
          WHERE analysis_runs.id = water_metrics.analysis_run_id
          AND (analysis_runs.user_id = auth.uid() OR auth.role() = 'admin')
        )
      );

    CREATE POLICY water_metrics_delete_policy ON water_metrics
      FOR DELETE
      USING (
        EXISTS (
          SELECT 1 FROM analysis_runs
          WHERE analysis_runs.id = water_metrics.analysis_run_id
          AND (analysis_runs.user_id = auth.uid() OR auth.role() = 'admin')
        )
      );
    """)

    # 8. Analysis artifacts policies (Child record inheritance through analysis_runs)
    op.execute("""
    CREATE POLICY analysis_artifacts_select_policy ON analysis_artifacts
      FOR SELECT
      USING (
        EXISTS (
          SELECT 1 FROM analysis_runs
          WHERE analysis_runs.id = analysis_artifacts.analysis_run_id
          AND (analysis_runs.user_id = auth.uid() OR auth.role() = 'admin')
        )
      );

    CREATE POLICY analysis_artifacts_insert_policy ON analysis_artifacts
      FOR INSERT
      WITH CHECK (
        EXISTS (
          SELECT 1 FROM analysis_runs
          WHERE analysis_runs.id = analysis_artifacts.analysis_run_id
          AND (analysis_runs.user_id = auth.uid() OR auth.role() = 'admin')
        )
      );

    CREATE POLICY analysis_artifacts_update_policy ON analysis_artifacts
      FOR UPDATE
      USING (
        EXISTS (
          SELECT 1 FROM analysis_runs
          WHERE analysis_runs.id = analysis_artifacts.analysis_run_id
          AND (analysis_runs.user_id = auth.uid() OR auth.role() = 'admin')
        )
      )
      WITH CHECK (
        EXISTS (
          SELECT 1 FROM analysis_runs
          WHERE analysis_runs.id = analysis_artifacts.analysis_run_id
          AND (analysis_runs.user_id = auth.uid() OR auth.role() = 'admin')
        )
      );

    CREATE POLICY analysis_artifacts_delete_policy ON analysis_artifacts
      FOR DELETE
      USING (
        EXISTS (
          SELECT 1 FROM analysis_runs
          WHERE analysis_runs.id = analysis_artifacts.analysis_run_id
          AND (analysis_runs.user_id = auth.uid() OR auth.role() = 'admin')
        )
      );
    """)


def downgrade() -> None:
    """Downgrade schema to remove RLS policies, disable RLS, and clean up auth helpers."""
    tables_policies = [
        ("profiles", ["profiles_select_policy", "profiles_insert_policy", "profiles_update_policy", "profiles_delete_policy"]),
        ("aois", ["aois_select_policy", "aois_insert_policy", "aois_update_policy", "aois_delete_policy"]),
        ("analysis_runs", ["analysis_runs_select_policy", "analysis_runs_insert_policy", "analysis_runs_update_policy", "analysis_runs_delete_policy"]),
        ("water_metrics", ["water_metrics_select_policy", "water_metrics_insert_policy", "water_metrics_update_policy", "water_metrics_delete_policy"]),
        ("analysis_artifacts", ["analysis_artifacts_select_policy", "analysis_artifacts_insert_policy", "analysis_artifacts_update_policy", "analysis_artifacts_delete_policy"]),
    ]
    for table, policies in tables_policies:
        for p in policies:
            op.execute(f"DROP POLICY IF EXISTS {p} ON {table};")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        JOIN pg_roles r ON r.oid = p.proowner
        WHERE n.nspname = 'auth' AND p.proname = 'uid' AND r.rolname = current_user
      ) THEN
        DROP FUNCTION auth.uid();
      END IF;
      IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        JOIN pg_roles r ON r.oid = p.proowner
        WHERE n.nspname = 'auth' AND p.proname = 'role' AND r.rolname = current_user
      ) THEN
        DROP FUNCTION auth.role();
      END IF;
    EXCEPTION WHEN insufficient_privilege THEN
      NULL;
    END
    $$;
    """)
