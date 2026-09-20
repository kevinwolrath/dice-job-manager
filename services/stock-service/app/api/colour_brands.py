import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.repositories import reference as repo
from app.schemas.reference import ColourBrandOut

# Read-only — the original app never let anyone create/update/delete colour
# brands either (db/services/colourBrand.ts only exports list/get).
router = APIRouter(prefix="/colour-brands", tags=["colour-brands"])


@router.get("", response_model=list[ColourBrandOut])
def list_colour_brands(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return repo.list_colour_brands(db)


@router.get("/{id}", response_model=ColourBrandOut)
def get_colour_brand(id: uuid.UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    row = repo.get_colour_brand(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Colour brand not found")
    return row
