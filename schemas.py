from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator


class PatientCreate(BaseModel):
    first_name: str = Field(min_length=3)
    last_name: str = Field(min_length=3)
    birthdate: date
    email: EmailStr | None = None

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
    email: EmailStr | None = None

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

class AssessmentCreate(BaseModel):
    assessment_date: date = Field()
    score: int = Field(ge=0, le=100)

    @field_validator("assessment_date")
    @classmethod
    def validate_assessment_date(cls, value):
        if value > date.today():
            raise ValueError("Value cannot be in the future.")
        return value

class AssessmentResponse(AssessmentCreate):
    id: int
    patient_id: int
