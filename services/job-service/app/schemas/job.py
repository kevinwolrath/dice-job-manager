import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- dice_job ---
# Deliberately no user_id field anywhere below. The owner is always taken
# from the caller's verified JWT (`sub` claim, app/api/deps.py) — never from
# the request body — so there is no field a client, or an injected prompt
# reaching this API through dice-mcp-server in a later phase, could ever set
# to someone else's user_id.
class DiceJobIn(BaseModel):
    job_name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    colour_count: int = Field(gt=0)
    colour_count_manual: bool = False
    material_type_id: uuid.UUID
    material_type_manual: bool = False
    production_method_id: uuid.UUID
    production_method_manual: bool = False
    dice_job_number_colour_id: uuid.UUID


class DiceJobUpdate(BaseModel):
    job_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    colour_count: int | None = Field(default=None, gt=0)
    colour_count_manual: bool | None = None
    material_type_id: uuid.UUID | None = None
    material_type_manual: bool | None = None
    production_method_id: uuid.UUID | None = None
    production_method_manual: bool | None = None
    dice_job_number_colour_id: uuid.UUID | None = None


class DiceJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dice_job_id: uuid.UUID
    user_id: uuid.UUID
    job_name: str
    description: str | None
    colour_count: int
    colour_count_manual: bool
    material_type_id: uuid.UUID
    material_type_manual: bool
    production_method_id: uuid.UUID
    production_method_manual: bool
    dice_job_number_colour_id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None


# --- dice_job_colour (replace-list pattern, matching the original app's
# replaceDiceJobColours) ---
class MaterialStockIdsIn(BaseModel):
    material_stock_ids: list[uuid.UUID] = Field(default_factory=list)


class DiceJobColourOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dice_job_colour_id: uuid.UUID
    dice_job_id: uuid.UUID
    material_stock_id: uuid.UUID
    colour_order: int | None
    created_at: datetime


# --- dice_job_colour_type_exclusion (replace-list pattern) ---
class ColourTypeIdsIn(BaseModel):
    colour_type_ids: list[uuid.UUID] = Field(default_factory=list)


class DiceJobColourTypeExclusionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dice_job_colour_type_exclusion_id: uuid.UUID
    dice_job_id: uuid.UUID
    colour_type_id: uuid.UUID
