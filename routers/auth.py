from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_session
from dependencies import get_current_user, verify_csrf_token
from models import SessionDB, UserDB
from schemas import UserCreate, UserLogin, UserResponse
from security import (
    generate_csrf_token,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/csrf")
def get_csrf_token(
    response: Response,
    current_user: Annotated[UserDB, Depends(get_current_user)],
    session_token: Annotated[str | None, Cookie()] = None,
):
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized."
        )

    csrf_token = generate_csrf_token(session_token)

    # Prevent caching of the CSRF token response.
    response.headers["Cache-Control"] = "no-store"

    return {"csrf_token": csrf_token}


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
    response: Response,
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
    session_token = generate_session_token()
    token_hash = hash_session_token(session_token)
    csrf_token = generate_csrf_token(session_token)
    csrf_token_hash = hash_session_token(csrf_token)
    expires_at = datetime.now(UTC) + timedelta(hours=24)
    session_db = SessionDB(
        user_id = user.id,
        token_hash = token_hash,
        expires_at = expires_at,
        csrf_token_hash = csrf_token_hash
    )
    session.add(session_db)
    session.commit()

    response.set_cookie(
        key="session_token", # Cookie name
        value=session_token, # Raw random session token
        httponly=True, # Prevent JavaScript from reading it
        # HttpOnly does not prevent CSRF attacks, so we'll need separate CSRF protection 
        # before exposing authenticated patient-modifying routes.
        secure=False, # to send only over HTTPS - must be True in production
        samesite="lax", # Reduce some cross-site request risks
        max_age=86400, # Expire after 24 hours
        path="/" # Make cookie available to application routes
    )
    return {"message": "Credentials valid"}

@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: Annotated[UserDB, Depends(get_current_user)]
):
    return current_user

@router.post("/logout",
            dependencies=[Depends(verify_csrf_token)])
def logout_user(
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    session_token: Annotated[str | None, Cookie()] = None,
):
    if session_token:
        token_hash = hash_session_token(session_token)
        statement = select(SessionDB).where(SessionDB.token_hash == token_hash)
        record = session.scalar(statement)

        if record is not None:
            # deleting the database record is what invalidates the session on the server
            # and server-side invalidation is the essential security measure
            session.delete(record)
            session.commit()

    # deleting the cookie tells the browser to stop sending the token
    response.delete_cookie(key="session_token", path="/")
        
    return {"message": "Logged out successfully"}
