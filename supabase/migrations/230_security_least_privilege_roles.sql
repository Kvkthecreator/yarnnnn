-- 230_security_least_privilege_roles.sql
-- Security audit (2026-08-01, Phase 3): stop using the `postgres` superuser for
-- day-to-day work. Two scoped login roles:
--   yarnnn_readonly — SELECT on the public schema; for ad-hoc queries + verify.py
--   yarnnn_migrate  — DDL + DML on public; for running migrations
--
-- NOT run automatically. Fill in the passwords from a secret manager (NEVER commit
-- them), then apply once with the superuser connection:
--   psql "$SUPABASE_DB_URL" -f supabase/migrations/230_security_least_privilege_roles.sql
-- After creating, export the scoped connection strings per docs/database/ACCESS.md
-- (SUPABASE_DB_URL_RO / SUPABASE_DB_URL_MIGRATE) and use those instead of postgres.
--
-- Passwords below are PLACEHOLDERS — replace <SET_...> before running. If you
-- accidentally commit a real one, this repo is public: rotate it immediately.

-- ── read-only role ────────────────────────────────────────────────────────────
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'yarnnn_readonly') THEN
    CREATE ROLE yarnnn_readonly LOGIN PASSWORD '<SET_READONLY_PASSWORD>';
  END IF;
END$$;

GRANT CONNECT ON DATABASE postgres TO yarnnn_readonly;
GRANT USAGE ON SCHEMA public TO yarnnn_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO yarnnn_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO yarnnn_readonly;
-- read-only must NOT bypass RLS
ALTER ROLE yarnnn_readonly NOBYPASSRLS;

-- ── migration role (DDL) ──────────────────────────────────────────────────────
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'yarnnn_migrate') THEN
    CREATE ROLE yarnnn_migrate LOGIN PASSWORD '<SET_MIGRATE_PASSWORD>';
  END IF;
END$$;

GRANT CONNECT ON DATABASE postgres TO yarnnn_migrate;
GRANT USAGE, CREATE ON SCHEMA public TO yarnnn_migrate;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO yarnnn_migrate;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO yarnnn_migrate;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO yarnnn_migrate;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO yarnnn_migrate;

-- Note: the application runtime keeps using SUPABASE_SERVICE_KEY (service_role)
-- and the pooled DATABASE_URL — these roles are for HUMAN operator access only.
