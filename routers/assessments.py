from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_session
from models import AssessmentDB
from schemas import AssessmentCreate, AssessmentResponse
from utils import find_patient

router = APIRouter(prefix="/patients/{patient_id}/assessments", tags=["assessments"])

@router.post("", response_model=AssessmentResponse, status_code=201)
def create_assessment(
    patient_id: int,
    assessment_create: AssessmentCreate, 
    session: Annotated[Session, Depends(get_session)]):
    patient = find_patient(patient_id, session)
    assessment_db = AssessmentDB(
        patient_id = patient.id,
        assessment_date = assessment_create.assessment_date,
        score = assessment_create.score
    )
    session.add(assessment_db)
    session.commit()
    session.refresh(assessment_db)
    return assessment_db

@router.get("", response_model=list[AssessmentResponse])
def list_assessments(
    patient_id: int,
    session: Annotated[Session, Depends(get_session)]):
    find_patient(patient_id, session)
    statement = (
        select(AssessmentDB)
        .where(AssessmentDB.patient_id == patient_id)
        .order_by(AssessmentDB.assessment_date.desc())
    )
    result = session.execute(statement).scalars().all()
    return result

@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(
    patient_id: int,
    assessment_id: int,
    session: Annotated[Session, Depends(get_session)]):
    find_patient(patient_id, session)
    statement = (
        select(AssessmentDB)
        .where(AssessmentDB.patient_id == patient_id)
        .where(AssessmentDB.id == assessment_id)
    )
    assessment = session.execute(statement).scalar_one_or_none()
    if assessment is None:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment of id {assessment_id} not found."
        )
    return assessment