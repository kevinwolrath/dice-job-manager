"""Seed a small, working set of reference data (architecture doc §14 Phase 1).

This is NOT a port of the original app's full 400+ row colour catalog
(db/seedColourCatalog.ts, ~76KB) — that's a data-migration task of its own,
separate from standing up the service. This seeds just enough real data
(material types, a few production methods and colour types with their
compatibility links, a couple of brands, a handful of stock colours, and
the 7 dice-number colours) to exercise every endpoint and to give
dice-job-service something real to validate against in Phase 3.

Run once, after migrations:

    docker compose exec dice-stock-service python -m scripts.seed_reference_data

Idempotent — safe to re-run; skips anything that already exists by name.
"""
from app.db.session import SessionLocal
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

DICE_NUMBER_COLOURS = ["Black", "White", "Gold", "Silver", "Red", "Green", "Blue"]

PRODUCTION_METHODS = [
    {"description": "Dirty Pour", "materials": ["Resin"]},
    {"description": "Marble", "materials": ["Resin", "Clay"]},
    {"description": "Mokume gane", "materials": ["Clay"]},
]

COLOUR_TYPES = [
    {"description": "Mica Powder", "materials": ["Resin"]},
    {"description": "Alcohol Ink", "materials": ["Resin"]},
    {"description": "Opaque Pigment", "materials": ["Resin", "Clay"]},
]

COLOUR_BRANDS = ["Pinata", "Generic"]

MATERIAL_STOCK = [
    {"colour_name": "Galaxy Black", "colour": "#1a1a2e", "colour_type": "Mica Powder", "brand": "Pinata", "qty": 5},
    {"colour_name": "Sunset Gold", "colour": "#d4af37", "colour_type": "Mica Powder", "brand": "Pinata", "qty": 3},
    {"colour_name": "Ocean Teal", "colour": "#008080", "colour_type": "Alcohol Ink", "brand": "Generic", "qty": 4},
    {"colour_name": "Ruby Red", "colour": "#9b111e", "colour_type": "Opaque Pigment", "brand": "Generic", "qty": 6},
    {"colour_name": "Snow White", "colour": "#f5f5f5", "colour_type": "Opaque Pigment", "brand": None, "qty": 8},
]


def run() -> None:
    with SessionLocal() as db:
        material_type_by_name: dict[str, MaterialType] = {}
        for name in ("Resin", "Clay"):
            row = db.query(MaterialType).filter(MaterialType.description == name).first()
            if not row:
                row = MaterialType(description=name)
                db.add(row)
                db.flush()
                print(f"created material_type: {name}")
            material_type_by_name[name] = row

        for pm in PRODUCTION_METHODS:
            row = db.query(ProductionMethod).filter(ProductionMethod.description == pm["description"]).first()
            if not row:
                row = ProductionMethod(description=pm["description"])
                db.add(row)
                db.flush()
                print(f"created production_method: {pm['description']}")
            for material_name in pm["materials"]:
                link = (
                    db.query(ProductionMethodMaterial)
                    .filter_by(
                        production_method_id=row.production_method_id,
                        material_type_id=material_type_by_name[material_name].material_type_id,
                    )
                    .first()
                )
                if not link:
                    db.add(
                        ProductionMethodMaterial(
                            production_method_id=row.production_method_id,
                            material_type_id=material_type_by_name[material_name].material_type_id,
                        )
                    )

        colour_type_by_name: dict[str, ColourType] = {}
        for ct in COLOUR_TYPES:
            row = db.query(ColourType).filter(ColourType.description == ct["description"]).first()
            if not row:
                row = ColourType(description=ct["description"])
                db.add(row)
                db.flush()
                print(f"created colour_type: {ct['description']}")
            colour_type_by_name[ct["description"]] = row
            for material_name in ct["materials"]:
                link = (
                    db.query(ColourTypeMaterialType)
                    .filter_by(
                        colour_type_id=row.colour_type_id,
                        material_type_id=material_type_by_name[material_name].material_type_id,
                    )
                    .first()
                )
                if not link:
                    db.add(
                        ColourTypeMaterialType(
                            colour_type_id=row.colour_type_id,
                            material_type_id=material_type_by_name[material_name].material_type_id,
                        )
                    )

        colour_brand_by_name: dict[str, ColourBrand] = {}
        for name in COLOUR_BRANDS:
            row = db.query(ColourBrand).filter(ColourBrand.colour_brand_name == name).first()
            if not row:
                row = ColourBrand(colour_brand_name=name)
                db.add(row)
                db.flush()
                print(f"created colour_brand: {name}")
            colour_brand_by_name[name] = row

        for stock in MATERIAL_STOCK:
            existing = db.query(MaterialStock).filter(MaterialStock.colour_name == stock["colour_name"]).first()
            if existing:
                continue
            db.add(
                MaterialStock(
                    colour_name=stock["colour_name"],
                    colour=stock["colour"],
                    colour_type_id=colour_type_by_name[stock["colour_type"]].colour_type_id,
                    colour_brand_id=colour_brand_by_name[stock["brand"]].colour_brand_id if stock["brand"] else None,
                    quantity_in_stock=stock["qty"],
                    is_active=True,
                )
            )
            print(f"created material_stock: {stock['colour_name']}")

        for name in DICE_NUMBER_COLOURS:
            row = db.query(DiceJobNumberColour).filter(DiceJobNumberColour.dice_job_number_colour_name == name).first()
            if not row:
                db.add(DiceJobNumberColour(dice_job_number_colour_name=name))
                print(f"created dice_job_number_colour: {name}")

        db.commit()


if __name__ == "__main__":
    run()
