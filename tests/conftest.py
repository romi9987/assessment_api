import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database import Base, get_session
from main import app
from models import AssessmentDB, PatientDB

load_dotenv(".env.test", override=True)

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]
test_engine = create_engine(TEST_DATABASE_URL)

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=test_engine)
    yield

@pytest.fixture
def client():
    connection = test_engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint"
    )

    def override_get_test_session():
        yield session

    app.dependency_overrides[get_session] = override_get_test_session

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)
        session.close()
        transaction.rollback()
        connection.close()

assert test_engine.url.database == "assessment_test_db", (
    "Tests must use assessment_test_db!"
)