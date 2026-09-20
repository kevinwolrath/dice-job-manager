"""Data access for all reference tables. Mirrors the original app's
db/services/*.ts functions 1:1 in shape (architecture doc §6), just against
Postgres/SQLAlchemy instead of SQLite.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.reference import (
    ColourBrand,
    ColourType,
    ColourTypeMaterialType,
    DiceJobNumberColour,
    MaterialStock,
    MaterialType,
    ProductionMethod,
    ProductionMethodMaterial,
)


# --- material_type ---
def list_material_types(db: Session) -> list[MaterialType]:
    return db.query(MaterialType).order_by(MaterialType.description).all()


def get_material_type(db: Session, id_: uuid.UUID) -> MaterialType | None:
    return db.get(MaterialType, id_)


def create_material_type(db: Session, description: str) -> MaterialType:
    row = MaterialType(description=description)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_material_type(db: Session, row: MaterialType, description: str) -> MaterialType:
    row.description = description
    db.commit()
    db.refresh(row)
    return row


def delete_material_type(db: Session, row: MaterialType) -> None:
    db.delete(row)
    db.commit()


# --- production_method ---
def list_production_methods(db: Session) -> list[ProductionMethod]:
    return db.query(ProductionMethod).order_by(ProductionMethod.description).all()


def get_production_method(db: Session, id_: uuid.UUID) -> ProductionMethod | None:
    return db.get(ProductionMethod, id_)


def create_production_method(
    db: Session, description: str, minimum_colour_count: int | None, maximum_colour_count: int | None
) -> ProductionMethod:
    row = ProductionMethod(
        description=description,
        minimum_colour_count=minimum_colour_count,
        maximum_colour_count=maximum_colour_count,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_production_method(db: Session, row: ProductionMethod, **fields) -> ProductionMethod:
    for key, value in fields.items():
        if value is not None:
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_production_method(db: Session, row: ProductionMethod) -> None:
    db.delete(row)
    db.commit()


def list_allowed_materials_for_method(db: Session, production_method_id: uuid.UUID) -> list[ProductionMethodMaterial]:
    return (
        db.query(ProductionMethodMaterial)
        .filter(ProductionMethodMaterial.production_method_id == production_method_id)
        .all()
    )


def list_all_production_method_materials(db: Session) -> list[ProductionMethodMaterial]:
    return db.query(ProductionMethodMaterial).all()


def replace_production_method_materials(
    db: Session, production_method_id: uuid.UUID, material_type_ids: list[uuid.UUID]
) -> None:
    db.query(ProductionMethodMaterial).filter(
        ProductionMethodMaterial.production_method_id == production_method_id
    ).delete()
    for material_type_id in material_type_ids:
        db.add(
            ProductionMethodMaterial(
                production_method_id=production_method_id, material_type_id=material_type_id
            )
        )
    db.commit()


# --- colour_type (+ its material-type links) ---
def list_colour_types(db: Session) -> list[ColourType]:
    return db.query(ColourType).order_by(ColourType.description).all()


def get_colour_type(db: Session, id_: uuid.UUID) -> ColourType | None:
    return db.get(ColourType, id_)


def create_colour_type(db: Session, description: str, material_type_ids: list[uuid.UUID]) -> ColourType:
    row = ColourType(description=description)
    db.add(row)
    db.flush()  # assigns colour_type_id before linking materials
    for material_type_id in material_type_ids:
        db.add(ColourTypeMaterialType(colour_type_id=row.colour_type_id, material_type_id=material_type_id))
    db.commit()
    db.refresh(row)
    return row


def update_colour_type(
    db: Session, row: ColourType, description: str | None, material_type_ids: list[uuid.UUID] | None
) -> ColourType:
    if description is not None:
        row.description = description
    if material_type_ids is not None:
        replace_colour_type_materials(db, row.colour_type_id, material_type_ids)
    db.commit()
    db.refresh(row)
    return row


def delete_colour_type(db: Session, row: ColourType) -> None:
    db.delete(row)
    db.commit()


def list_materials_for_colour_type(db: Session, colour_type_id: uuid.UUID) -> list[ColourTypeMaterialType]:
    return db.query(ColourTypeMaterialType).filter(ColourTypeMaterialType.colour_type_id == colour_type_id).all()


def list_all_colour_type_materials(db: Session) -> list[ColourTypeMaterialType]:
    return db.query(ColourTypeMaterialType).all()


def replace_colour_type_materials(db: Session, colour_type_id: uuid.UUID, material_type_ids: list[uuid.UUID]) -> None:
    db.query(ColourTypeMaterialType).filter(ColourTypeMaterialType.colour_type_id == colour_type_id).delete()
    for material_type_id in material_type_ids:
        db.add(ColourTypeMaterialType(colour_type_id=colour_type_id, material_type_id=material_type_id))
    db.commit()


# --- colour_brand (read-only) ---
def list_colour_brands(db: Session) -> list[ColourBrand]:
    return db.query(ColourBrand).order_by(ColourBrand.colour_brand_name).all()


def get_colour_brand(db: Session, id_: uuid.UUID) -> ColourBrand | None:
    return db.get(ColourBrand, id_)


# --- material_stock ---
def list_material_stock(db: Session) -> list[MaterialStock]:
    return db.query(MaterialStock).order_by(MaterialStock.colour_name).all()


def get_material_stock(db: Session, id_: uuid.UUID) -> MaterialStock | None:
    return db.get(MaterialStock, id_)


def create_material_stock(db: Session, **fields) -> MaterialStock:
    row = MaterialStock(**fields)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_material_stock(db: Session, row: MaterialStock, **fields) -> MaterialStock:
    import datetime as dt

    for key, value in fields.items():
        if value is not None:
            setattr(row, key, value)
    row.updated_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def delete_material_stock(db: Session, row: MaterialStock) -> None:
    db.delete(row)
    db.commit()


# --- dice_job_number_colour ---
def list_dice_job_number_colours(db: Session) -> list[DiceJobNumberColour]:
    return db.query(DiceJobNumberColour).order_by(DiceJobNumberColour.dice_job_number_colour_name).all()


def get_dice_job_number_colour(db: Session, id_: uuid.UUID) -> DiceJobNumberColour | None:
    return db.get(DiceJobNumberColour, id_)


def create_dice_job_number_colour(db: Session, name: str) -> DiceJobNumberColour:
    row = DiceJobNumberColour(dice_job_number_colour_name=name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_dice_job_number_colour(db: Session, row: DiceJobNumberColour, name: str) -> DiceJobNumberColour:
    row.dice_job_number_colour_name = name
    db.commit()
    db.refresh(row)
    return row


def delete_dice_job_number_colour(db: Session, row: DiceJobNumberColour) -> None:
    db.delete(row)
    db.commit()
