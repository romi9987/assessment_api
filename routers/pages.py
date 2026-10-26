from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_session
from models import PatientDB
from schemas import PatientCreate

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

@router.get("/patients/new")
def new_patient_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="patient_form.html",
        context={}
    )

@router.post("/patients")
def create_patient_from_form(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    first_name: Annotated[str, Form()],
    last_name: Annotated[str, Form()],
    birthdate: Annotated[str, Form()],
    email: Annotated[str | None, Form()] = None,
):
    try:
        patient = PatientCreate(
            first_name = first_name,
            last_name = last_name,
            birthdate = birthdate,
            email = email or ""
        )
    except ValidationError as exc:
        if request.headers.get("HX-Request") == "true":
            return templates.TemplateResponse(
                request=request,
                name="partials/form_errors.html",
                context={"errors": exc.errors()},
                status_code=422
            )
        return templates.TemplateResponse(
            request=request,
            name="patient_form.html",
            context={
                "errors": exc.errors(),
                "form_data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    # isoformat() converts a Python date into a string such as "1990-05-15", 
                    # which is the format an HTML date input expects.
                    "birthdate": birthdate,
                    "email": email or ""
                }
            },
            status_code=422
        )
    patient_db = PatientDB(**patient.model_dump())
    session.add(patient_db)
    session.commit()
    if request.headers.get("HX-Request") == "true":
        return HTMLResponse(
            content="<p>Patient created successfully!</p>",
            status_code=200
        )

    return RedirectResponse(
        url="/ui/patients",
        # Why 303?
        # Because after the browser submits a POST request, 
        # we want it to follow the redirect using GET, 
        # not submit the form again.
        # This is known as the Post/Redirect/Get pattern.
        status_code=303
    )
