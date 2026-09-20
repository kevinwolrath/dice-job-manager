from fastapi import APIRouter, Response
from sqlalchemy import text

from app.db.session import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
def health(response: Response):
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        postgres_status = "ok"
    except Exception:
        postgres_status = "unavailable"
        response.status_code = 503
    return {
        "status": "ok" if postgres_status == "ok" else "degraded",
        "api": "ok",
        "postgres": postgres_status,
    }
