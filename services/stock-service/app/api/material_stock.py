import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.errors import conflict_on_integrity_error
from app.db.session import get_db
from app.repositories import reference as repo
from app.schemas.reference import MaterialStockIn, MaterialStockOut, MaterialStockUpdate

router = APIRouter(prefix="/material-stock", tags=["material-stock"])


@router.get("", response_model=list[MaterialStockOut])
def list_material_stock(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return repo.list_material_stock(db)


@router.post("", response_model=MaterialStockOut, status_code=status.HTTP_201_CREATED)
def create_material_stock(payload: MaterialStockIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    fields = payload.model_dump()
    if not fields.get("colour"):
        fields["colour"] = "#888888"  # placeholder; the Expo client derives real values from colour_name
    with conflict_on_integrity_error(db, "colour_type_id or colour_brand_id does not exist"):
        return repo.create_material_stock(db, **fields)


@router.get("/{id}", response_model=MaterialStockOut)
def get_material_stock(id: uuid.UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    row = repo.get_material_stock(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material stock not found")
    return row


@router.put("/{id}", response_model=MaterialStockOut)
def update_material_stock(
    id: uuid.UUID, payload: MaterialStockUpdate, db: Session = Depends(get_db), _=Depends(require_admin)
):
    row = repo.get_material_stock(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material stock not found")
    with conflict_on_integrity_error(db, "colour_type_id or colour_brand_id does not exist"):
        return repo.update_material_stock(db, row, **payload.model_dump(exclude_unset=True))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material_stock(id: uuid.UUID, db: Session = Depends(get_db), _=Depends(require_admin)):
    row = repo.get_material_stock(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material stock not found")
    repo.delete_material_stock(db, row)
