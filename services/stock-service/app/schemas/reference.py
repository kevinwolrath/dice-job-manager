import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- material_type ---
class MaterialTypeIn(BaseModel):
    description: str = Field(min_length=1, max_length=128)


class MaterialTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    material_type_id: uuid.UUID
    description: str
    created_at: datetime


# --- production_method ---
class ProductionMethodIn(BaseModel):
    description: str = Field(min_length=1, max_length=128)
    minimum_colour_count: int | None = None
    maximum_colour_count: int | None = None


class ProductionMethodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    production_method_id: uuid.UUID
    description: str
    minimum_colour_count: int | None
    maximum_colour_count: int | None
    created_at: datetime


# --- colour_type (create/update also replaces its allowed material types) ---
class ColourTypeIn(BaseModel):
    description: str = Field(min_length=1, max_length=128)
    material_type_ids: list[uuid.UUID] = Field(default_factory=list)


class ColourTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    colour_type_id: uuid.UUID
    description: str
    created_at: datetime


class ColourTypeMaterialTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    colour_type_id: uuid.UUID
    material_type_id: uuid.UUID
    created_at: datetime


# --- colour_brand (read-only, matches the original app's behaviour) ---
class ColourBrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    colour_brand_id: uuid.UUID
    colour_brand_name: str
    created_at: datetime


# --- material_stock ---
class MaterialStockIn(BaseModel):
    colour_name: str = Field(min_length=1, max_length=128)
    colour: str | None = None
    comment: str | None = None
    colour_type_id: uuid.UUID
    colour_brand_id: uuid.UUID | None = None
    quantity_in_stock: int = 0
    is_active: bool = True


class MaterialStockUpdate(BaseModel):
    colour_name: str | None = None
    colour: str | None = None
    comment: str | None = None
    colour_type_id: uuid.UUID | None = None
    colour_brand_id: uuid.UUID | None = None
    quantity_in_stock: int | None = None
    is_active: bool | None = None


class MaterialStockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    material_stock_id: uuid.UUID
    colour_name: str
    colour: str
    comment: str | None
    colour_type_id: uuid.UUID
    colour_brand_id: uuid.UUID | None
    quantity_in_stock: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None


# --- dice_job_number_colour ---
class DiceJobNumberColourIn(BaseModel):
    dice_job_number_colour_name: str = Field(min_length=1, max_length=64)


class DiceJobNumberColourOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dice_job_number_colour_id: uuid.UUID
    dice_job_number_colour_name: str
    created_at: datetime


# --- production_method_material ---
class ProductionMethodMaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    production_method_id: uuid.UUID
    material_type_id: uuid.UUID
    created_at: datetime


class MaterialTypeIdsIn(BaseModel):
    material_type_ids: list[uuid.UUID]
