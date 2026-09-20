"""grant job_service_role REFERENCES on stock_service (architecture doc §13.b/n)

Migration 0002 granted job_service_role plain SELECT on stock_service, which
is enough for job-service's own queries that validate a material_type_id /
production_method_id / etc. actually exists. It is NOT enough to create a
foreign key constraint that points at those tables — Postgres requires the
REFERENCES privilege (separate from SELECT) on a table you don't own before
you can add a FK referencing it. This was only discovered when job-service's
first migration tried to create job_service.dice_job with FKs into
stock_service and failed; this migration grants exactly the missing
privilege, nothing more.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-17
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SCHEMA = "stock_service"
READER = "job_service_role"


def upgrade() -> None:
    op.execute(f"GRANT REFERENCES ON ALL TABLES IN SCHEMA {SCHEMA} TO {READER}")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} GRANT REFERENCES ON TABLES TO {READER}")


def downgrade() -> None:
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} REVOKE REFERENCES ON TABLES FROM {READER}")
    op.execute(f"REVOKE REFERENCES ON ALL TABLES IN SCHEMA {SCHEMA} FROM {READER}")
