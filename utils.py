from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import PatientDB


def find_patient(patient_id: int, session: Session):
    statement = select(PatientDB).where(PatientDB.id == patient_id)
    result = session.execute(statement)
    patient = result.scalar()
    if patient is None:
        raise HTTPException(
            status_code=404,
            detail=f"Patient of id {patient_id} not found."
        )
    return patient