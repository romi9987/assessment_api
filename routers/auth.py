from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_session
from models import UserDB
from schemas import UserCreate, UserResponse
from security import hash_password

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