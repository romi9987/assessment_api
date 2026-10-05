from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

app = FastAPI()

DATABASE_URL = "sqlite:///./assessment.db"
engine = create_engine(DATABASE_URL)

class Base(DeclarativeBase):
    pass

class PatientDB(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column()
    last_name: Mapped[str] = mapped_column()
    birthdate: Mapped[date] = mapped_column()

Base.metadata.create_all(bind=engine)

class PatientCreate(BaseModel):
    first_name: str = Field(min_length=3)
    last_name: str = Field(min_length=3)
    birthdate: date

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def validate_name(cls, value):
        cleaned_value = value.strip()
        if not all(char.isalpha() or char in " -'" for char in cleaned_value):
            raise ValueError("Value must contain only letter, hyphen, apostrophe or space.")
        if not any(char.isalpha() for char in cleaned_value):
            raise ValueError("Value must contain at least one letter.")
        return cleaned_value

    @field_validator("birthdate")
    @classmethod
    def validate_birthdate(cls, value):
        if value >= date.today():
            raise ValueError("Value must be in the past.")
        return value

class PatientResponse(PatientCreate):
    id: int

class PatientUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=3)
    last_name: str | None = Field(default=None, min_length=3)
    birthdate: date | None = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def validate_name(cls, value):
        if value is None:
            raise ValueError("Value cannot be null.")
        cleaned_value = value.strip()
        if not all(char.isalpha() or char in " -'" for char in cleaned_value):
            raise ValueError("Value must contain only letter, hyphen, apostrophe or space.")
        if not any(char.isalpha() for char in cleaned_value):
            raise ValueError("Value must contain at least one letter.")
        return cleaned_value

    @field_validator("birthdate")
    @classmethod
    def validate_birthdate(cls, value):
        if value is None:
            raise ValueError("Value cannot be null.")
        if value >= date.today():
            raise ValueError("Value must be in the past.")
        return value

def get_session():
    with Session(engine) as session:
        yield session

@app.get("/")
def main():
    return {
        "app_name": "Assessment API",
        "version": 1,
        "description": "Assess and keep patient data.",
        "status": "active"
    }

@app.post("/patients", response_model=PatientResponse)
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

@app.get("/patients", response_model=list[PatientResponse])
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

@app.get("/patients/{patient_id}", response_model=PatientResponse)
def list_patient(patient_id: int, session: Annotated[Session, Depends(get_session)]):
    patient = find_patient(patient_id, session)
    return patient

@app.delete("/patients/{patient_id}")
def remove_patient(patient_id: int, session: Annotated[Session, Depends(get_session)]):
    patient = find_patient(patient_id, session)
    session.delete(patient)
    session.commit()
    return f"Patient of id {patient_id} has been removed."

@app.put("/patients/{patient_id}", response_model=PatientResponse)
def modify_patient(patient_id: int, 
                   patient_create: PatientCreate, 
                   session: Annotated[Session, Depends(get_session)],):
    patient = find_patient(patient_id, session)
    patient.first_name = patient_create.first_name
    patient.last_name = patient_create.last_name
    patient.birthdate = patient_create.birthdate
    session.commit()
    session.refresh(patient)
    return patient

@app.patch("/patients/{patient_id}", response_model=PatientResponse)
def modify_field(patient_id: int,
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
        