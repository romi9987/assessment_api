from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from database import get_session
from models import AssessmentDB, PatientDB
from schemas import AssessmentCreate, PatientCreate

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
    statement = select(PatientDB)
    if q:
        statement = (
            statement.where(
                or_(
                    PatientDB.first_name.ilike(f"%{q}%"),
                    PatientDB.last_name.ilike(f"%{q}%"),
                    (PatientDB.first_name + " " + PatientDB.last_name).ilike(f"%{q}%")
                )
            )
        )
    count_statement = select(func.count()).select_from(
        statement.subquery()
    )
    total_patients = session.scalar(count_statement)
    last_page = max(1, (total_patients + page_size - 1) // page_size)
    if page > last_page:
        url = f"/ui/patients?{urlencode({'page': last_page, 'q': q})}"
        if request.headers.get("HX-Request") == "true":
            return Response(
                status_code=200,
                headers={"HX-Redirect": url}
            )
        return RedirectResponse(
                url=url,
                status_code=303
            )
    offset = (page - 1) * page_size
    statement = (
        statement
        .order_by(PatientDB.id).
        limit(page_size)
        .offset(offset)
    )
    patients = session.execute(statement).scalars().all()

    has_next = page < last_page

    context={
            "patients": patients,
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
            email = email or None
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
            email=email or None,
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

@router.delete("/patients/{patient_id}")
def delete_patient(
    patient_id: int,
    session: Annotated[Session, Depends(get_session)]
):
    patient = session.get(PatientDB, patient_id)
    if patient is not None:
        session.delete(patient)
        session.commit()
    return Response(
        status_code=200,
        headers={"HX-Trigger": "patientDeleted"},
    )

@router.get("/patients/{patient_id}/assessments")
def list_patient_assessments(
    request: Request,
    patient_id: int,
    session: Annotated[Session, Depends(get_session)]
    ):
    patient = find_patient(session, patient_id)
    statement = (
        select(AssessmentDB)
        .where(AssessmentDB.patient_id == patient_id)
        .order_by(AssessmentDB.assessment_date.desc())
        )
    assessments = session.execute(statement).scalars().all()
    return templates.TemplateResponse(
        request=request,
        name="assessments.html",
        context={"patient": patient, "assessments": assessments}
    )

@router.get("/patients/{patient_id}/assessments/new")
def new_assessment_form(
    request: Request,
    patient_id: int,
    session: Annotated[Session, Depends(get_session)]
):
    patient = find_patient(session, patient_id)
    return templates.TemplateResponse(
        request=request,
        name="assessment_form.html",
        context={"patient": patient}
    )

@router.post("/patients/{patient_id}/assessments")
def create_assessment_from_form(
    request: Request,
    patient_id: int,
    session: Annotated[Session, Depends(get_session)],
    assessment_date: Annotated[str, Form()],
    score: Annotated[str, Form()],
):
    patient = find_patient(session, patient_id)
    try:
        assessment = AssessmentCreate(
            assessment_date = assessment_date,
            score = score
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="assessment_form.html",
            context={
                "patient": patient,
                "errors": exc.errors(),
                "form_data": {
                    "assessment_date": assessment_date,
                    "score": score
                }
            },
            status_code=422
        )
    assessment_db = AssessmentDB(
        patient_id=patient_id,
        **assessment.model_dump()
        )
    session.add(assessment_db)
    session.commit()
    return RedirectResponse(
        url=f"/ui/patients/{patient_id}/assessments",
        status_code=303
    )
