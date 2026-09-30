-- MINOVA PostgreSQL Initialization
-- Run against a fresh PostgreSQL 16 instance.

-- Extensions (pgvector must be installed as a shared library first)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- PostGIS & pgvector (loaded via shared_preload_libraries or CREATE EXTENSION)
-- These will error if the .so/.dll is missing; the bootstrap script handles that.
DO $$
BEGIN
  EXECUTE 'CREATE EXTENSION IF NOT EXISTS postgis';
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'PostGIS extension not available: %. Install it and re-run.', SQLERRM;
END $$;

DO $$
BEGIN
  EXECUTE 'CREATE EXTENSION IF NOT EXISTS vector';
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'pgvector extension not available: %. Install it and re-run.', SQLERRM;
END $$;

-- Roles
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'minova_app') THEN
    CREATE ROLE minova_app LOGIN PASSWORD 'minova_app_2026';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'minova_readonly') THEN
    CREATE ROLE minova_readonly LOGIN PASSWORD 'minova_ro_2026';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'minova_audit') THEN
    CREATE ROLE minova_audit LOGIN PASSWORD 'minova_audit_2026';
  END IF;
END $$;

-- Schema
CREATE SCHEMA IF NOT EXISTS minova AUTHORIZATION minova_app;

-- Grants for minova_app (read-write on minova schema)
GRANT USAGE ON SCHEMA minova TO minova_app;
GRANT CREATE ON SCHEMA minova TO minova_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA minova
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO minova_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA minova
  GRANT USAGE, SELECT ON SEQUENCES TO minova_app;

-- Grants for minova_readonly
GRANT USAGE ON SCHEMA minova TO minova_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA minova
  GRANT SELECT ON TABLES TO minova_readonly;

-- Grants for minova_audit (read-only on audit tables, append via function)
GRANT USAGE ON SCHEMA minova TO minova_audit;
ALTER DEFAULT PRIVILEGES IN SCHEMA minova
  GRANT SELECT ON TABLES TO minova_audit;

-- The audit_event table will be created by Alembic migrations.
-- A trigger/rule will prevent UPDATE/DELETE on it (enforced in migration).
-- The hash-chain integrity is enforced at the application layer.

-- Full-text search configuration for English + Hindi
-- Hindi uses 'simple' dictionary; English uses built-in 'english'.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'minova_multilingual') THEN
    CREATE TEXT SEARCH CONFIGURATION minova_multilingual (COPY = simple);
  END IF;
END $$;

-- Search path for convenience
ALTER DATABASE minova SET search_path TO minova, public;

-- Statement timeout for readonly role (guard against runaway LLM-generated queries)
ALTER ROLE minova_readonly SET statement_timeout = '30s';
