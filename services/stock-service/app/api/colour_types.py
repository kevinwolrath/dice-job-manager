import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.errors import conflict_on_integrity_error
from app.db.session import get_db
from app.repositories import reference as repo
from app.schemas.reference import (
    ColourTypeIn,
    ColourTypeMaterialTypeOut,
    ColourTypeOut,
    MaterialTypeIdsIn,
)

router = APIRouter(prefix="/colour-types", tags=["colour-types"])

# Literal-path routes first — see the note in production_methods.py.


@router.get("/_all/materials", response_model=list[ColourTypeMaterialTypeOut])
def list_all_colour_type_materials(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return repo.list_all_colour_type_materials(db)


@router.get("", response_model=list[ColourTypeOut])
def list_colour_types(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return repo.list_colour_types(db)


@router.post("", response_model=ColourTypeOut, status_code=status.HTTP_201_CREATED)
def create_colour_type(payload: ColourTypeIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    with conflict_on_integrity_error(db, f"Colour type '{payload.description}' already exists, or one of the given material_type_ids does not exist"):
        return repo.create_colour_type(db, payload.description, payload.material_type_ids)


@router.get("/{id}", response_model=ColourTypeOut)
def get_colour_type(id: uuid.UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    row = repo.get_colour_type(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Colour type not found")
    return row


@router.put("/{id}", response_model=ColourTypeOut)
def update_colour_type(id: uuid.UUID, payload: ColourTypeIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    row = repo.get_colour_type(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Colour type not found")
    with conflict_on_integrity_error(db, f"Colour type '{payload.description}' already exists, or one of the given material_type_ids does not exist"):
        return repo.update_colour_type(db, row, payload.description, payload.material_type_ids)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_colour_type(id: uuid.UUID, db: Session = Depends(get_db), _=Depends(require_admin)):
    row = repo.get_colour_type(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Colour type not found")
    repo.delete_colour_type(db, row)


@router.get("/{id}/materials", response_model=list[ColourTypeMaterialTypeOut])
def list_materials_for_colour_type(id: uuid.UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return repo.list_materials_for_colour_type(db, id)


@router.put("/{id}/materials", response_model=list[ColourTypeMaterialTypeOut])
def replace_materials_for_colour_type(
    id: uuid.UUID, payload: MaterialTypeIdsIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    with conflict_on_integrity_error(db, "One or more material_type_ids do not exist"):
        repo.replace_colour_type_materials(db, id, payload.material_type_ids)
    return repo.list_materials_for_colour_type(db, id)
