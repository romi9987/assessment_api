from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_session
from models import PatientDB
from schemas import PatientCreate, PatientResponse, PatientUpdate

router = APIRouter(prefix="/patients", tags=["patients"])

@router.post("", response_model=PatientResponse)
def create_patient(patient: PatientCreate, session: Annotated[Session, Depends(get_session)]):
    patient_db = PatientDB(
        first_name = patient.first_name,
        last_name = patient.last_name,
        birthdate = patient.birthdate
    )
    session.add(patient_db)
    session.commit()
    session.refresh(patient_db)
    return patient_db

@router.get("", response_model=list[PatientResponse])
def list_patients(session: Annotated[Session, Depends(get_session)]):
    statement = select(PatientDB)
    result = session.execute(statement)
    patients = result.scalars().all()
    return patients

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

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: int, session: Annotated[Session, Depends(get_session)]):
    patient = find_patient(patient_id, session)
    return patient

@router.delete("/{patient_id}")
def remove_patient(patient_id: int, session: Annotated[Session, Depends(get_session)]):
    patient = find_patient(patient_id, session)
    session.delete(patient)
    session.commit()
    return f"Patient of id {patient_id} has been removed."

@router.put("/{patient_id}", response_model=PatientResponse)
def replace_patient(patient_id: int, 
                   patient_create: PatientCreate, 
                   session: Annotated[Session, Depends(get_session)],):
    patient = find_patient(patient_id, session)
    patient.first_name = patient_create.first_name
    patient.last_name = patient_create.last_name
    patient.birthdate = patient_create.birthdate
    session.commit()
    session.refresh(patient)
    return patient

@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(patient_id: int,
                 patient_update: PatientUpdate,
                 session: Annotated[Session, Depends(get_session)]):
    patient = find_patient(patient_id, session)
    update_data = patient_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="At least one field must be provided."
        )
    for field, value in update_data.items():
        setattr(patient, field, value)
    session.commit()
    session.refresh(patient)
    return patient
