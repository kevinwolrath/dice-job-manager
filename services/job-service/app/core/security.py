"""JWT verification only — dice-job-service never issues tokens, only
dice-user-service does. Verifies independently with the public key; no
callback to dice-user-service per request (architecture doc §11).

This service reads the `sub` claim (the caller's user_id) to scope every
query it runs, and deliberately never reads the `role` claim at all — see
app/api/deps.py for why.
"""
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()

_public_key: str | None = None


def get_public_key() -> str:
    global _public_key
    if _public_key is None:
        _public_key = Path(settings.jwt_public_key_path).read_text()
    return _public_key


def decode_access_token(token: str) -> dict:
    import jwt

    return jwt.decode(
        token,
        get_public_key(),
        algorithms=[settings.jwt_algorithm],
        issuer="dice-user-service",
    )
