"""grant job_service_role read-only access to stock_service (architecture doc §13.b)

job-service validates material_type_id / production_method_id / colour_type_id /
material_stock_id when creating or updating a job, and may FK against these
tables. It gets SELECT only, on this one schema, and nothing else — there is
no grant anywhere in the other direction. stock_service_role owns these
tables (it created them in 0001), so it can grant on them without needing
superuser.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-17
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SCHEMA = "stock_service"
READER = "job_service_role"


def upgrade() -> None:
    op.execute(f"GRANT USAGE ON SCHEMA {SCHEMA} TO {READER}")
    op.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA {SCHEMA} TO {READER}")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} GRANT SELECT ON TABLES TO {READER}")


def downgrade() -> None:
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} REVOKE SELECT ON TABLES FROM {READER}")
    op.execute(f"REVOKE SELECT ON ALL TABLES IN SCHEMA {SCHEMA} FROM {READER}")
    op.execute(f"REVOKE USAGE ON SCHEMA {SCHEMA} FROM {READER}")
