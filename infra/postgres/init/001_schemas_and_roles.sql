-- Bootstrap: one schema and one least-privilege login role per service,
-- inside the single shared dice-postgres instance (architecture doc, §9/§13.a/§13.c).
--
-- Runs automatically on first container init (docker-entrypoint-initdb.d).
-- POSTGRES_USER (a superuser, see .env) is for local dev and migrations only;
-- each application service connects with its own role below instead, and
-- never with the superuser.

CREATE SCHEMA IF NOT EXISTS user_service;
CREATE SCHEMA IF NOT EXISTS job_service;
CREATE SCHEMA IF NOT EXISTS stock_service;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'user_service_role') THEN
    CREATE ROLE user_service_role LOGIN PASSWORD 'user_service_dev_pw';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'job_service_role') THEN
    CREATE ROLE job_service_role LOGIN PASSWORD 'job_service_dev_pw';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'stock_service_role') THEN
    CREATE ROLE stock_service_role LOGIN PASSWORD 'stock_service_dev_pw';
  END IF;
END
$$;

-- Each role owns its own schema outright. No role is granted anything in
-- another service's schema by default — see the one deliberate exception below.
GRANT ALL ON SCHEMA user_service TO user_service_role;
ALTER SCHEMA user_service OWNER TO user_service_role;

GRANT ALL ON SCHEMA job_service TO job_service_role;
ALTER SCHEMA job_service OWNER TO job_service_role;

GRANT ALL ON SCHEMA stock_service TO stock_service_role;
ALTER SCHEMA stock_service OWNER TO stock_service_role;

-- Deliberate, scoped exception (architecture doc §13.b): job-service reads
-- stock-service's shared reference tables (material_type, colour_type, etc.)
-- and may FK against them. It gets read-only access to that one schema —
-- nothing else, and never the reverse. There is NO grant anywhere from
-- job_service's private tables (dice_job, etc.) to any other role — that
-- boundary (§13.a) stays absolute.
--
-- NOT applied here — left commented out for documentation only. This grant is
-- actually applied by dice-stock-service's own Alembic migrations
-- (services/stock-service/alembic/versions/0002_grant_job_service_read_access.py
-- for SELECT, plus 0003_grant_job_service_references.py for REFERENCES — the
-- separate privilege Postgres requires before job-service's own migration can
-- create a foreign key pointing into these tables), since stock_service_role
-- owns these tables and can grant on them itself without needing the Postgres
-- superuser. Applying it as normal migrations (rather than by hand here) means
-- it's versioned, reviewable, and reversible like everything else:
--
-- GRANT USAGE ON SCHEMA stock_service TO job_service_role;
-- GRANT SELECT ON ALL TABLES IN SCHEMA stock_service TO job_service_role;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA stock_service GRANT SELECT ON TABLES TO job_service_role;

-- Default search_path per role, so each service's own Alembic migrations and
-- queries land in / read from the right schema(s) without qualifying every
-- statement.
ALTER ROLE user_service_role SET search_path = user_service;
ALTER ROLE job_service_role SET search_path = job_service, stock_service;
ALTER ROLE stock_service_role SET search_path = stock_service;
