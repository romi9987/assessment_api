from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_session
from models import SessionDB, UserDB
from schemas import UserCreate, UserLogin, UserResponse
from security import generate_session_token, hash_password, hash_session_token, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user: UserCreate,
    session: Annotated[Session, Depends(get_session)]
):
    statement = select(UserDB).where(UserDB.email == user.email)
    existing_user = session.scalar(statement)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User of email {user.email} already exists in database."
        )

    user_db = UserDB(
        email = user.email,
        hashed_password = hash_password(user.password)
    )
    session.add(user_db)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User of email {user.email} already exists in database."
        )
    session.refresh(user_db)

    return user_db

@router.post("/login")
def login_user(
    credentials: UserLogin,
    session: Annotated[Session, Depends(get_session)]
):
    statement = select(UserDB).where(UserDB.email == credentials.email)
    user = session.scalar(statement)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid email or password."
        )
    token = generate_session_token()
    token_hash = hash_session_token(token)
    expires_at = datetime.UTC + timedelta(hours=24)
    session_db = SessionDB(
        user_id = user.id,
        token_hash = token_hash,
        expires_at = expires_at
    )
    session.add(session_db)
    session.commit()
    return {"message": "Credentials valid"}
    