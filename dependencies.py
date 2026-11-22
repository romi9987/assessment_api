import hmac
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_session
from models import SessionDB, UserDB
from security import generate_csrf_token, hash_session_token


def get_current_user(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    session_token: Annotated[str | None, Cookie()] = None,
) -> UserDB:
    if session_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The user is not authorized."
        )

    hashed_token = hash_session_token(session_token)

    session_statement = select(SessionDB).where(SessionDB.token_hash == hashed_token)
    session_db = session.scalar(session_statement)

    if session_db is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session."
        )
    if session_db.expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session."
        )

# This is correct because user_id references the primary key of UserDB.
    user_db = session.get(UserDB, session_db.user_id)
    if user_db is None:
        raise HTTPException(
            status_code=401,
            detail="User does not exist."
        )
    if not user_db.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive."
        )
    # request.state allows you to attach information to the current HTTP request.
    request.state.current_user = user_db
    return user_db

def require_admin(
    current_user: Annotated[UserDB, Depends(get_current_user)]
) -> UserDB:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required."
        )

    return current_user

def verify_csrf_token(
    current_user: Annotated[UserDB, Depends(get_current_user)],
    session_token: Annotated[str | None, Cookie()] = None,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    if not session_token or not csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CSRF token."
        )

    expected_csrf_token = generate_csrf_token(session_token)
    # We use compare_digest instead of normal comparison, because it protects against timing attacks.
    # It is designed to avoid content-dependent timing differences when comparing values of the same type.
    # Ordinary string comparison may stop as soon as it finds a difference. 
    # Depending on the implementation, the comparison time can reveal information about matching characters.
    check = hmac.compare_digest(expected_csrf_token, csrf_token)
    if not check:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CSRF token."
        )