"""JWT verification only — dice-stock-service never issues tokens, only
dice-user-service does. Verifies independently with the public key; no
callback to dice-user-service per request (architecture doc §11).
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
