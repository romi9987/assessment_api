from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_session
from dependencies import get_current_user, verify_csrf_token
from models import PatientDB, UserDB
from schemas import PatientCreate, PatientResponse, PatientUpdate
from utils import find_patient

router = APIRouter(prefix="/patients", tags=["patients"])

@router.post(
    "", 
    response_model=PatientResponse, 
    status_code=201,
    dependencies=[Depends(verify_csrf_token)]
)
def create_patient(patient: PatientCreate, 
                   session: Annotated[Session, Depends(get_session)],
                   current_user: Annotated[UserDB, Depends(get_current_user)]):
    patient_db = PatientDB(
        user_id = current_user.id,
        first_name = patient.first_name,
        last_name = patient.last_name,
        birthdate = patient.birthdate,
        email = patient.email
    )
    session.add(patient_db)
    session.commit()
    session.refresh(patient_db)
    return patient_db

@router.get("", response_model=list[PatientResponse])
def list_patients(session: Annotated[Session, Depends(get_session)],
                  current_user: Annotated[UserDB, Depends(get_current_user)]):
    statement = select(PatientDB).where(PatientDB.user_id == current_user.id)
    patients = session.execute(statement).scalars().all()
    return patients

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: int, 
                session: Annotated[Session, Depends(get_session)],
                current_user: Annotated[UserDB, Depends(get_current_user)]):
    patient = find_patient(session, patient_id, current_user)
    return patient

@router.delete("/{patient_id}",
               dependencies=[Depends(verify_csrf_token)])
def remove_patient(patient_id: int, 
                   session: Annotated[Session, Depends(get_session)],
                   current_user: Annotated[UserDB, Depends(get_current_user)]):
    patient = find_patient(session, patient_id, current_user)
    session.delete(patient)
    session.commit()
    return f"Patient of id {patient_id} has been removed."

@router.put(
    "/{patient_id}", 
    response_model=PatientResponse,
    dependencies=[Depends(verify_csrf_token)]
)
def replace_patient(patient_id: int, 
                   patient_create: PatientCreate, 
                   session: Annotated[Session, Depends(get_session)],
                   current_user: Annotated[UserDB, Depends(get_current_user)]):
    patient = find_patient(session, patient_id, current_user)
    patient.first_name = patient_create.first_name
    patient.last_name = patient_create.last_name
    patient.birthdate = patient_create.birthdate
    patient.email = patient_create.email
    session.commit()
    session.refresh(patient)
    return patient

@router.patch(
    "/{patient_id}", 
    response_model=PatientResponse,
    dependencies=[Depends(verify_csrf_token)]
)
def update_patient(patient_id: int,
                 patient_update: PatientUpdate,
                 session: Annotated[Session, Depends(get_session)],
                 current_user: Annotated[UserDB, Depends(get_current_user)]):
    patient = find_patient(session, patient_id, current_user)
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
