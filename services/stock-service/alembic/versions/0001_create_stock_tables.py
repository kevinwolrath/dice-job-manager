"""create stock_service reference tables

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

SCHEMA = "stock_service"


def upgrade() -> None:
    op.create_table(
        "material_type",
        sa.Column("material_type_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("description", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema=SCHEMA,
    )

    op.create_table(
        "production_method",
        sa.Column("production_method_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("description", sa.String(), nullable=False, unique=True),
        sa.Column("minimum_colour_count", sa.Integer(), nullable=True),
        sa.Column("maximum_colour_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema=SCHEMA,
    )

    op.create_table(
        "colour_type",
        sa.Column("colour_type_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("description", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema=SCHEMA,
    )

    op.create_table(
        "colour_type_material_type",
        sa.Column("colour_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.colour_type.colour_type_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("material_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.material_type.material_type_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema=SCHEMA,
    )

    op.create_table(
        "colour_brand",
        sa.Column("colour_brand_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("colour_brand_name", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema=SCHEMA,
    )

    op.create_table(
        "material_stock",
        sa.Column("material_stock_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("colour_name", sa.String(), nullable=False),
        sa.Column("colour", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("colour_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.colour_type.colour_type_id"), nullable=False),
        sa.Column("colour_brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.colour_brand.colour_brand_id"), nullable=True),
        sa.Column("quantity_in_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("quantity_in_stock >= 0", name="ck_material_stock_quantity_non_negative"),
        schema=SCHEMA,
    )
    op.create_index("ix_material_stock_colour_type", "material_stock", ["colour_type_id"], schema=SCHEMA)

    op.create_table(
        "dice_job_number_colour",
        sa.Column("dice_job_number_colour_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("dice_job_number_colour_name", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema=SCHEMA,
    )

    op.create_table(
        "production_method_material",
        sa.Column("production_method_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.production_method.production_method_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("material_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.material_type.material_type_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("production_method_material", schema=SCHEMA)
    op.drop_table("dice_job_number_colour", schema=SCHEMA)
    op.drop_index("ix_material_stock_colour_type", table_name="material_stock", schema=SCHEMA)
    op.drop_table("material_stock", schema=SCHEMA)
    op.drop_table("colour_brand", schema=SCHEMA)
    op.drop_table("colour_type_material_type", schema=SCHEMA)
    op.drop_table("colour_type", schema=SCHEMA)
    op.drop_table("production_method", schema=SCHEMA)
    op.drop_table("material_type", schema=SCHEMA)
