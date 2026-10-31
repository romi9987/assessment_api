from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from database import get_session
from models import PatientDB
from schemas import PatientCreate

router = APIRouter(prefix="/ui", tags=["ui"])

templates = Jinja2Templates(directory="templates")

def find_patient(
        session: Session,
        patient_id: int,
) -> PatientDB:
    patient = session.get(PatientDB, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=404,
            detail=f"Patient of id: {patient_id} not found."
        )
    return patient

@router.get("/patients")
def list_patients(
    request: Request, 
    session: Annotated[Session, Depends(get_session)],
    page: int = Query(default=1, ge=1),
    q: str = "",
    ):
    page_size = 5
    offset = (page - 1) * page_size
    statement = select(PatientDB)
    if q:
        statement = (
            select(PatientDB).where(
                or_(
                    PatientDB.first_name.ilike(f"%{q}%"),
                    PatientDB.last_name.ilike(f"%{q}%"),
                    (PatientDB.first_name + " " + PatientDB.last_name).ilike(f"%{q}%")
                )
            )
        )
    statement = (
        statement
        .order_by(PatientDB.id).
        limit(page_size + 1)
        .offset(offset)
    )
    patients = session.execute(statement).scalars().all()

    has_next = len(patients) > page_size
    visible_patients = patients[:page_size]
    context={
            "patients": visible_patients,
            "page": page,
            "has_next": has_next,
            "has_previous": page > 1,
            "q": q,
            }
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            request=request,
            name="partials/patients_content.html",
            context=context,
        )
    return templates.TemplateResponse(
        request=request,
        name="patients.html",
        context=context,
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

@router.get("/patients/{patient_id}/edit")
def edit_patient(
    request: Request, 
    patient_id: int, 
    session: Annotated[Session, Depends(get_session)],
):
    patient = find_patient(session=session, patient_id=patient_id)
    return templates.TemplateResponse(
        request=request,
        name="partials/patient_edit_row.html",
        context={"patient": patient,}
    )

@router.get("/patients/{patient_id}/row")
def cancel_edit(
    request: Request,
    patient_id: int,
    session: Annotated[Session, Depends(get_session)],
):
    patient = find_patient(session=session, patient_id=patient_id)
    return templates.TemplateResponse(
        request=request,
        name="partials/patient_row.html",
        context={"patient": patient}
    )

@router.patch("/patients/{patient_id}")
def save_edit(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    patient_id: int,
    first_name: Annotated[str, Form()],
    last_name: Annotated[str, Form()],
    birthdate: Annotated[str, Form()],
    email: Annotated[str | None, Form()] = None,
):
    patient = find_patient(session=session, patient_id=patient_id)
    try:
        patient_data = PatientCreate(
            first_name=first_name,
            last_name=last_name,
            birthdate=birthdate,
            email=email or "",
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="partials/patient_edit_row.html",
            context={
                "patient": patient,
                "errors": exc.errors(),
                "form_data": {
                                "first_name": first_name,
                                "last_name": last_name,
                                "birthdate": birthdate,
                                "email": email or ""
                            },
            },
            status_code=422,
        )
    patient.first_name = patient_data.first_name
    patient.last_name = patient_data.last_name
    patient.birthdate = patient_data.birthdate
    patient.email = patient_data.email
    session.commit()
    session.refresh(patient)
    return templates.TemplateResponse(
            request=request,
            name="partials/patient_row.html",
            context={"patient": patient,}
        )
