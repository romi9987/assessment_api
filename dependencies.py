from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_session
from models import SessionDB, UserDB
from security import hash_session_token


def get_current_user(
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
    return user_db