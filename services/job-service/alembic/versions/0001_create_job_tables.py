"""create job_service tables

dice_job.user_id has no FK to user_service.app_user — deliberate (architecture
doc §13.a). Ownership is enforced entirely at the application layer (every
repository function in app/repositories/job.py takes and filters by user_id).

material_type_id / production_method_id / dice_job_number_colour_id /
material_stock_id / colour_type_id DO carry real FKs into stock_service — the
one deliberate cross-schema exception (§13.b). Creating those FKs requires
job_service_role to hold REFERENCES (not just SELECT) on the target tables,
granted by stock-service's own migration 0003 — run that before this one.

Revision ID: 0001
Revises:
Create Date: 2026-09-17
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "job_service"
STOCK_SCHEMA = "stock_service"


def upgrade() -> None:
    op.create_table(
        "dice_job",
        sa.Column("dice_job_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("colour_count", sa.Integer(), nullable=False),
        sa.Column("colour_count_manual", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "material_type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{STOCK_SCHEMA}.material_type.material_type_id"),
            nullable=False,
        ),
        sa.Column("material_type_manual", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "production_method_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{STOCK_SCHEMA}.production_method.production_method_id"),
            nullable=False,
        ),
        sa.Column("production_method_manual", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "dice_job_number_colour_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{STOCK_SCHEMA}.dice_job_number_colour.dice_job_number_colour_id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("colour_count > 0", name="ck_dice_job_colour_count_positive"),
        schema=SCHEMA,
    )
    op.create_index("ix_dice_job_user", "dice_job", ["user_id"], schema=SCHEMA)

    op.create_table(
        "dice_job_colour",
        sa.Column("dice_job_colour_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "dice_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.dice_job.dice_job_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "material_stock_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{STOCK_SCHEMA}.material_stock.material_stock_id"),
            nullable=False,
        ),
        sa.Column("colour_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("dice_job_id", "material_stock_id", name="uq_dice_job_colour_job_stock"),
        schema=SCHEMA,
    )
    op.create_index("ix_dice_job_colour_job", "dice_job_colour", ["dice_job_id"], schema=SCHEMA)

    op.create_table(
        "dice_job_colour_type_exclusion",
        sa.Column(
            "dice_job_colour_type_exclusion_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "dice_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.dice_job.dice_job_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "colour_type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{STOCK_SCHEMA}.colour_type.colour_type_id"),
            nullable=False,
        ),
        sa.UniqueConstraint("dice_job_id", "colour_type_id", name="uq_dice_job_colour_type_exclusion_job_type"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_dice_job_colour_type_exclusion_job", "dice_job_colour_type_exclusion", ["dice_job_id"], schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_table("dice_job_colour_type_exclusion", schema=SCHEMA)
    op.drop_table("dice_job_colour", schema=SCHEMA)
    op.drop_index("ix_dice_job_user", table_name="dice_job", schema=SCHEMA)
    op.drop_table("dice_job", schema=SCHEMA)
