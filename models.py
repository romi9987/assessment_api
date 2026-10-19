from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class PatientDB(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column()
    last_name: Mapped[str] = mapped_column()
    birthdate: Mapped[date] = mapped_column()
    email: Mapped[str | None] = mapped_column(nullable=True)
    assessments: Mapped[list["AssessmentDB"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True
        )

# And there are actually two consequences of removing ForeignKey("patients.id"):
    # 1. SQLAlchemy won't automatically know how to join the tables. When configuring relationship(), it normally uses foreign key information to determine which columns connect the two models. Without it, you would generally get a NoForeignKeysError, unless you explicitly configure the join.
    # 2. PostgreSQL won't enforce referential integrity. Without a database foreign key constraint, it could accept an assessment with a patient_id that doesn't exist.
# So we need both:
    # - ForeignKey() for database integrity.
    # - relationship() for convenient navigation between Python objects.
# PostgreSQL doesn't provide an ALTER CONSTRAINT operation for changing an existing foreign key's ON DELETE behavior directly.
# Therefore, Alembic needs to drop the previous foreign key constraint and creates a new one in case of change.

class AssessmentDB(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Notice that "patients.id" refers to the database table name
    # The two concepts have different responsibilities:
        # - ForeignKey() establishes a database-level relationship and enforces referential integrity.
        # - relationship() provides convenient navigation between related Python ORM objects.
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    assessment_date: Mapped[date] = mapped_column()
    score: Mapped[int] = mapped_column()
    patient: Mapped["PatientDB"] = relationship(back_populates="assessments")
   