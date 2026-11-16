from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import AssessmentDB, PatientDB, UserDB


def find_patient(
        session: Session,
        patient_id: int,
        current_user: UserDB,
) -> PatientDB:
    statement = select(PatientDB).where(
        PatientDB.user_id == current_user.id,
        PatientDB.id == patient_id)
    patient = session.execute(statement).scalar_one_or_none()
    if patient is None:
        raise HTTPException(
            status_code=404,
            detail=f"Patient of id: {patient_id} not found."
        )
    return patient

def find_assessment(
        session: Session,
        current_user: UserDB,
        patient_id: int,
        assessment_id: int,
) -> AssessmentDB:
    patient = find_patient(session, patient_id, current_user)
    statement = select(AssessmentDB).where(
        AssessmentDB.patient_id == patient.id,
        AssessmentDB.id == assessment_id
    )
    assessment = session.execute(statement).scalar_one_or_none()
    if assessment is None:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment of id: {assessment_id} for patient of id {patient_id} not found."
        )
    return assessment