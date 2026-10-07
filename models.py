from datetime import date

from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class PatientDB(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column()
    last_name: Mapped[str] = mapped_column()
    birthdate: Mapped[date] = mapped_column()