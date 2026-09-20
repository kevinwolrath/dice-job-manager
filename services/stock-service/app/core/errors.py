"""Shared helper: translate a Postgres constraint violation (a duplicate
value in a unique column, or a foreign key pointing at a row that doesn't
exist) into a clean 4xx response instead of letting it bubble up as a bare
`Internal Server Error`.

Without this, Postgres is already doing its job correctly by rejecting the
bad write — but FastAPI's default unhandled-exception path turns that into
an opaque 500 with no detail for the caller, which is what happened the
first time this was hit in testing (POST /material-types with a description
that already existed).
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
