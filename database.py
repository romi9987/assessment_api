from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

# DATABASE_URL = "sqlite:///./assessment.db"
# postgresql+psycopg://username:password@host:port/database
DATABASE_URL = "postgresql+psycopg://assessment_user:assessment_dev_password@localhost:5432/assessment_db"
engine = create_engine(DATABASE_URL)

class Base(DeclarativeBase):
    pass

def get_session():
    with Session(engine) as session:
        yield session
