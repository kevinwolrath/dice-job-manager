"""All shared reference-data tables live in one schema, one file — there are
only 7 small tables and they're read together far more often than apart
(architecture doc §9). Splitting them into 7 files would add navigation
overhead with no real separation-of-concerns benefit.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

SCHEMA = "stock_service"


class MaterialType(Base):
    __tablename__ = "material_type"
    __table_args__ = {"schema": SCHEMA}

    material_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductionMethod(Base):
    __tablename__ = "production_method"
    __table_args__ = {"schema": SCHEMA}

    production_method_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    minimum_colour_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maximum_colour_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ColourType(Base):
    __tablename__ = "colour_type"
    __table_args__ = {"schema": SCHEMA}

    colour_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ColourTypeMaterialType(Base):
    __tablename__ = "colour_type_material_type"
    __table_args__ = {"schema": SCHEMA}

    colour_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.colour_type.colour_type_id", ondelete="CASCADE"), primary_key=True
    )
    material_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.material_type.material_type_id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ColourBrand(Base):
    __tablename__ = "colour_brand"
    __table_args__ = {"schema": SCHEMA}

    colour_brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    colour_brand_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MaterialStock(Base):
    __tablename__ = "material_stock"
    __table_args__ = (CheckConstraint("quantity_in_stock >= 0"), {"schema": SCHEMA})

    material_stock_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    colour_name: Mapped[str] = mapped_column(String, nullable=False)
    colour: Mapped[str] = mapped_column(String, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    colour_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.colour_type.colour_type_id"), nullable=False
    )
    colour_brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.colour_brand.colour_brand_id"), nullable=True
    )
    quantity_in_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DiceJobNumberColour(Base):
    __tablename__ = "dice_job_number_colour"
    __table_args__ = {"schema": SCHEMA}

    dice_job_number_colour_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dice_job_number_colour_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductionMethodMaterial(Base):
    __tablename__ = "production_method_material"
    __table_args__ = {"schema": SCHEMA}

    production_method_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.production_method.production_method_id", ondelete="CASCADE"),
        primary_key=True,
    )
    material_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.material_type.material_type_id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
