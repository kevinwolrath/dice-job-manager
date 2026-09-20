import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.errors import conflict_on_integrity_error
from app.db.session import get_db
from app.repositories import reference as repo
from app.schemas.reference import (
    MaterialTypeIdsIn,
    ProductionMethodIn,
    ProductionMethodMaterialOut,
    ProductionMethodOut,
)

router = APIRouter(prefix="/production-methods", tags=["production-methods"])

# NOTE: literal-path routes (e.g. "/_all/materials") must be registered
# BEFORE parameterized routes (e.g. "/{id}/materials") — FastAPI/Starlette
# matches routes in registration order, and "{id}" would otherwise swallow
# "_all" as a value and fail UUID validation before this route is ever tried.


@router.get("/_all/materials", response_model=list[ProductionMethodMaterialOut])
def list_all_allowed_materials(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return repo.list_all_production_method_materials(db)


@router.get("", response_model=list[ProductionMethodOut])
def list_production_methods(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return repo.list_production_methods(db)


@router.post("", response_model=ProductionMethodOut, status_code=status.HTTP_201_CREATED)
def create_production_method(payload: ProductionMethodIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    with conflict_on_integrity_error(db, f"Production method '{payload.description}' already exists"):
        return repo.create_production_method(
            db, payload.description, payload.minimum_colour_count, payload.maximum_colour_count
        )


@router.get("/{id}", response_model=ProductionMethodOut)
def get_production_method(id: uuid.UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    row = repo.get_production_method(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production method not found")
    return row


@router.put("/{id}", response_model=ProductionMethodOut)
def update_production_method(
    id: uuid.UUID, payload: ProductionMethodIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    row = repo.get_production_method(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production method not found")
    with conflict_on_integrity_error(db, f"Production method '{payload.description}' already exists"):
        return repo.update_production_method(
            db,
            row,
            description=payload.description,
            minimum_colour_count=payload.minimum_colour_count,
            maximum_colour_count=payload.maximum_colour_count,
        )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_production_method(id: uuid.UUID, db: Session = Depends(get_db), _=Depends(require_admin)):
    row = repo.get_production_method(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production method not found")
    repo.delete_production_method(db, row)


@router.get("/{id}/materials", response_model=list[ProductionMethodMaterialOut])
def list_allowed_materials(id: uuid.UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return repo.list_allowed_materials_for_method(db, id)


@router.put("/{id}/materials", response_model=list[ProductionMethodMaterialOut])
def replace_allowed_materials(
    id: uuid.UUID, payload: MaterialTypeIdsIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    with conflict_on_integrity_error(db, "One or more material_type_ids do not exist"):
        repo.replace_production_method_materials(db, id, payload.material_type_ids)
    return repo.list_allowed_materials_for_method(db, id)
