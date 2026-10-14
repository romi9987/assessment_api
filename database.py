import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

load_dotenv()

# DATABASE_URL = "sqlite:///./assessment.db"
# postgresql+psycopg://username:password@host:port/database
DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)

class Base(DeclarativeBase):
    pass

def get_session():
    with Session(engine) as session:
        yield session
