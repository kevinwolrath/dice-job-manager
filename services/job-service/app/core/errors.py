"""Shared helper: translate a Postgres constraint violation (a duplicate
value in a unique column, or a foreign key pointing at a row that doesn't
exist — e.g. a bogus material_type_id) into a clean 4xx response instead of
letting it bubble up as a bare `Internal Server Error`. Same helper as
dice-stock-service's app/core/errors.py; see that file's docstring for the
story of why this exists.
"""
from contextlib import contextmanager

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@contextmanager
def conflict_on_integrity_error(db: Session, message: str):
    try:
        yield
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
