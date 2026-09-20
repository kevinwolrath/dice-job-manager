"""Password hashing and RS256 JWT issuing/verification.

dice-user-service holds the private key and signs; every other service
(job-service, stock-service, mcp-server) holds only the public key and
verifies — see architecture doc §11. The `decode_access_token` function here
is the same shape those services will each carry their own copy of.
"""
import time
import uuid
from pathlib import Path

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()

_private_key: str | None = None
_public_key: str | None = None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _load_key(path: str) -> str:
    return Path(path).read_text()


def get_private_key() -> str:
    global _private_key
    if _private_key is None:
        _private_key = _load_key(settings.jwt_private_key_path)
    return _private_key


def get_public_key() -> str:
    global _public_key
    if _public_key is None:
        _public_key = _load_key(settings.jwt_public_key_path)
    return _public_key


def create_access_token(*, user_id: uuid.UUID, username: str, role: str) -> tuple[str, int]:
    now = int(time.time())
    expires_in = settings.jwt_access_token_minutes * 60
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + expires_in,
        "iss": "dice-user-service",
    }
    token = jwt.encode(payload, get_private_key(), algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        get_public_key(),
        algorithms=[settings.jwt_algorithm],
        issuer="dice-user-service",
    )
