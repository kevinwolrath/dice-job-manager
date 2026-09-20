import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.errors import conflict_on_integrity_error
from app.db.session import get_db
from app.repositories import reference as repo
from app.schemas.reference import MaterialTypeIn, MaterialTypeOut

router = APIRouter(prefix="/material-types", tags=["material-types"])


@router.get("", response_model=list[MaterialTypeOut])
def list_material_types(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return repo.list_material_types(db)


@router.get("/{id}", response_model=MaterialTypeOut)
def get_material_type(id: uuid.UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    row = repo.get_material_type(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material type not found")
    return row


@router.post("", response_model=MaterialTypeOut, status_code=status.HTTP_201_CREATED)
def create_material_type(payload: MaterialTypeIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    with conflict_on_integrity_error(db, f"Material type '{payload.description}' already exists"):
        return repo.create_material_type(db, payload.description)


@router.put("/{id}", response_model=MaterialTypeOut)
def update_material_type(id: uuid.UUID, payload: MaterialTypeIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    row = repo.get_material_type(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material type not found")
    with conflict_on_integrity_error(db, f"Material type '{payload.description}' already exists"):
        return repo.update_material_type(db, row, payload.description)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material_type(id: uuid.UUID, db: Session = Depends(get_db), _=Depends(require_admin)):
    row = repo.get_material_type(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material type not found")
    repo.delete_material_type(db, row)
