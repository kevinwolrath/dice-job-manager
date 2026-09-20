"""Auth dependencies for dice-job-service.

get_current_user: any valid, verified JWT — same independent RS256 check as
dice-stock-service, no callback to dice-user-service per request
(architecture doc §11).

Unlike dice-stock-service, this service NEVER reads the `role` claim,
anywhere, for anything (§13.h). `role` only ever gates writes to shared
reference data in stock-service; job-service is written so that it
structurally cannot let an admin role widen access to another user's jobs —
there's no code path here that even looks at it.

current_user_id is the single place a caller's identity enters this
service. Every route below depends on it — never on a path, query, or body
user_id — to decide "whose jobs" for any operation.
"""
import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    try:
        return decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def current_user_id(current_user: dict = Depends(get_current_user)) -> uuid.UUID:
    return uuid.UUID(current_user["sub"])
