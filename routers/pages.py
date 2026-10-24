from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_session
from models import PatientDB

router = APIRouter(prefix="/ui", tags=["ui"])

templates = Jinja2Templates(directory="templates")

@router.get("/patients")
def list_patients(request: Request, session: Annotated[Session, Depends(get_session)]):
    statement = select(PatientDB)
    patients = session.execute(statement).scalars().all()
    return templates.TemplateResponse(
        request=request,
        name="patients.html",
        context={"patients": patients}
    )
