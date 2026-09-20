import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.errors import conflict_on_integrity_error
from app.db.session import get_db
from app.repositories import reference as repo
from app.schemas.reference import DiceJobNumberColourIn, DiceJobNumberColourOut

router = APIRouter(prefix="/dice-job-number-colours", tags=["dice-job-number-colours"])


@router.get("", response_model=list[DiceJobNumberColourOut])
def list_dice_job_number_colours(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return repo.list_dice_job_number_colours(db)


@router.post("", response_model=DiceJobNumberColourOut, status_code=status.HTTP_201_CREATED)
def create_dice_job_number_colour(
    payload: DiceJobNumberColourIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    with conflict_on_integrity_error(
        db, f"Dice job number colour '{payload.dice_job_number_colour_name}' already exists"
    ):
        return repo.create_dice_job_number_colour(db, payload.dice_job_number_colour_name)


@router.get("/{id}", response_model=DiceJobNumberColourOut)
def get_dice_job_number_colour(id: uuid.UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    row = repo.get_dice_job_number_colour(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dice job number colour not found")
    return row


@router.put("/{id}", response_model=DiceJobNumberColourOut)
def update_dice_job_number_colour(
    id: uuid.UUID, payload: DiceJobNumberColourIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    row = repo.get_dice_job_number_colour(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dice job number colour not found")
    with conflict_on_integrity_error(
        db, f"Dice job number colour '{payload.dice_job_number_colour_name}' already exists"
    ):
        return repo.update_dice_job_number_colour(db, row, payload.dice_job_number_colour_name)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dice_job_number_colour(id: uuid.UUID, db: Session = Depends(get_db), _=Depends(require_admin)):
    row = repo.get_dice_job_number_colour(db, id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dice job number colour not found")
    repo.delete_dice_job_number_colour(db, row)
