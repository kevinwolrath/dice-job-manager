"""job_service tables (architecture doc §9).

dice_job.user_id has NO foreign key to user_service.app_user — deliberate
(§13.a). Ownership is enforced entirely at the application layer: every
function in app/repositories/job.py takes a user_id and filters by it.
There is no ORM relationship, and no mapped class, for anything in
user_service — this service cannot even express a query that reaches it.

material_type_id / production_method_id / dice_job_number_colour_id (on
dice_job), material_stock_id (on dice_job_colour), and colour_type_id (on
dice_job_colour_type_exclusion) DO carry real foreign keys into
stock_service — the one deliberate cross-schema exception (§13.b), enforced
by Postgres itself via the SELECT + REFERENCES grants applied in
stock-service's own migrations 0002/0003. There are no mapped ORM classes
for the stock_service tables here and no relationships declared into them —
job-service never queries them, only has Postgres reject a job that points
at a material/method/colour that doesn't exist.

That said, SQLAlchemy's ORM (not just raw DDL) needs to resolve every FK's
*target* table when it works out insert ordering during a flush — and it
only looks inside its own MetaData registry, not the actual database. The
five _stock_* Table objects below exist solely to satisfy that: each is
just the one primary-key column a job_service FK actually points at, with
no ORM class over it and nothing job-service treats as its own data. Skip
them and every insert into dice_job/dice_job_colour/etc. fails at runtime
with `NoReferencedTableError`, even though the migration that created the
real FK constraints in Postgres succeeds fine (DDL doesn't need this
resolution — only the ORM's flush-ordering logic does).
"""
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

SCHEMA = "job_service"
STOCK_SCHEMA = "stock_service"

_stock_material_type = sa.Table(
    "material_type",
    Base.metadata,
    sa.Column("material_type_id", UUID(as_uuid=True), primary_key=True),
    schema=STOCK_SCHEMA,
)
_stock_production_method = sa.Table(
    "production_method",
    Base.metadata,
    sa.Column("production_method_id", UUID(as_uuid=True), primary_key=True),
    schema=STOCK_SCHEMA,
)
_stock_dice_job_number_colour = sa.Table(
    "dice_job_number_colour",
    Base.metadata,
    sa.Column("dice_job_number_colour_id", UUID(as_uuid=True), primary_key=True),
    schema=STOCK_SCHEMA,
)
_stock_material_stock = sa.Table(
    "material_stock",
    Base.metadata,
    sa.Column("material_stock_id", UUID(as_uuid=True), primary_key=True),
    schema=STOCK_SCHEMA,
)
_stock_colour_type = sa.Table(
    "colour_type",
    Base.metadata,
    sa.Column("colour_type_id", UUID(as_uuid=True), primary_key=True),
    schema=STOCK_SCHEMA,
)


class DiceJob(Base):
    __tablename__ = "dice_job"
    __table_args__ = (
        CheckConstraint("colour_count > 0", name="ck_dice_job_colour_count_positive"),
        {"schema": SCHEMA},
    )

    dice_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    job_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    colour_count: Mapped[int] = mapped_column(Integer, nullable=False)
    colour_count_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    material_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{STOCK_SCHEMA}.material_type.material_type_id"), nullable=False
    )
    material_type_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    production_method_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{STOCK_SCHEMA}.production_method.production_method_id"), nullable=False
    )
    production_method_manual: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    dice_job_number_colour_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{STOCK_SCHEMA}.dice_job_number_colour.dice_job_number_colour_id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DiceJobColour(Base):
    __tablename__ = "dice_job_colour"
    __table_args__ = (
        UniqueConstraint("dice_job_id", "material_stock_id", name="uq_dice_job_colour_job_stock"),
        {"schema": SCHEMA},
    )

    dice_job_colour_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dice_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.dice_job.dice_job_id", ondelete="CASCADE"), nullable=False
    )
    material_stock_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{STOCK_SCHEMA}.material_stock.material_stock_id"), nullable=False
    )
    colour_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiceJobColourTypeExclusion(Base):
    __tablename__ = "dice_job_colour_type_exclusion"
    __table_args__ = (
        UniqueConstraint("dice_job_id", "colour_type_id", name="uq_dice_job_colour_type_exclusion_job_type"),
        {"schema": SCHEMA},
    )

    dice_job_colour_type_exclusion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dice_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.dice_job.dice_job_id", ondelete="CASCADE"), nullable=False
    )
    colour_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{STOCK_SCHEMA}.colour_type.colour_type_id"), nullable=False
    )
