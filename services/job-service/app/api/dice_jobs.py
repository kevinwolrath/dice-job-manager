"""dice_job endpoints. Every route below takes its "whose job" from
current_user_id (the verified JWT's `sub` claim) — never from a path, query,
or body parameter — matching the get_my_jobs()-style design the whole
project is built around (architecture doc §13.d/§13.i): there is no
endpoint here shaped like "get jobs for user X", so there is nothing for a
direct request or an injected prompt to exploit.

_get_owned_job_or_404 returns 404 — not 403 — whether the job_id doesn't
exist at all or belongs to someone else. That's deliberate: a 403 would
confirm the job exists but isn't yours, which is itself a small information
leak. Every colour/exclusion sub-resource route calls this first, before
touching any child row, so ownership is always re-checked at the top of
every request rather than assumed from an earlier one.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import current_user_id
from app.core.errors import conflict_on_integrity_error
from app.db.session import get_db
from app.models.job import DiceJob
from app.repositories import job as repo
from app.schemas.job import (
    ColourTypeIdsIn,
    DiceJobColourOut,
    DiceJobColourTypeExclusionOut,
    DiceJobIn,
    DiceJobOut,
    DiceJobUpdate,
    MaterialStockIdsIn,
)

router = APIRouter(prefix="/dice-jobs", tags=["dice-jobs"])

_FK_CONFLICT_MESSAGE = "material_type_id, production_method_id, or dice_job_number_colour_id does not exist"


def _get_owned_job_or_404(db: Session, user_id: uuid.UUID, job_id: uuid.UUID) -> DiceJob:
    row = repo.get_job(db, user_id, job_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dice job not found")
    return row


@router.get("", response_model=list[DiceJobOut])
def list_my_jobs(db: Session = Depends(get_db), user_id: uuid.UUID = Depends(current_user_id)):
    return repo.list_jobs(db, user_id)


@router.post("", response_model=DiceJobOut, status_code=status.HTTP_201_CREATED)
def create_job(payload: DiceJobIn, db: Session = Depends(get_db), user_id: uuid.UUID = Depends(current_user_id)):
    with conflict_on_integrity_error(db, _FK_CONFLICT_MESSAGE):
        return repo.create_job(db, user_id, **payload.model_dump())


@router.get("/{id}", response_model=DiceJobOut)
def get_job(id: uuid.UUID, db: Session = Depends(get_db), user_id: uuid.UUID = Depends(current_user_id)):
    return _get_owned_job_or_404(db, user_id, id)


@router.put("/{id}", response_model=DiceJobOut)
def update_job(
    id: uuid.UUID,
    payload: DiceJobUpdate,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(current_user_id),
):
    row = _get_owned_job_or_404(db, user_id, id)
    with conflict_on_integrity_error(db, _FK_CONFLICT_MESSAGE):
        return repo.update_job(db, row, **payload.model_dump(exclude_unset=True))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(id: uuid.UUID, db: Session = Depends(get_db), user_id: uuid.UUID = Depends(current_user_id)):
    row = _get_owned_job_or_404(db, user_id, id)
    repo.delete_job(db, row)


@router.get("/{id}/colours", response_model=list[DiceJobColourOut])
def list_job_colours(id: uuid.UUID, db: Session = Depends(get_db), user_id: uuid.UUID = Depends(current_user_id)):
    _get_owned_job_or_404(db, user_id, id)
    return repo.list_job_colours(db, id)


@router.put("/{id}/colours", response_model=list[DiceJobColourOut])
def replace_job_colours(
    id: uuid.UUID,
    payload: MaterialStockIdsIn,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(current_user_id),
):
    _get_owned_job_or_404(db, user_id, id)
    with conflict_on_integrity_error(db, "One or more material_stock_ids do not exist"):
        repo.replace_job_colours(db, id, payload.material_stock_ids)
    return repo.list_job_colours(db, id)


@router.get("/{id}/colour-exclusions", response_model=list[DiceJobColourTypeExclusionOut])
def list_job_colour_type_exclusions(
    id: uuid.UUID, db: Session = Depends(get_db), user_id: uuid.UUID = Depends(current_user_id)
):
    _get_owned_job_or_404(db, user_id, id)
    return repo.list_job_colour_type_exclusions(db, id)


@router.put("/{id}/colour-exclusions", response_model=list[DiceJobColourTypeExclusionOut])
def replace_job_colour_type_exclusions(
    id: uuid.UUID,
    payload: ColourTypeIdsIn,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(current_user_id),
):
    _get_owned_job_or_404(db, user_id, id)
    with conflict_on_integrity_error(db, "One or more colour_type_ids do not exist"):
        repo.replace_job_colour_type_exclusions(db, id, payload.colour_type_ids)
    return repo.list_job_colour_type_exclusions(db, id)
