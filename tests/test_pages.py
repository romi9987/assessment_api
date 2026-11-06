from datetime import date

from bs4 import BeautifulSoup
from sqlalchemy import select

from models import PatientDB


def test_list_patients(client):
    response = client.get("/ui/patients")
    assert response.status_code == 200
    assert "Patients" in response.text
    assert "text/html" in response.headers["content-type"]

def test_search_patients(client):
    """
    Checking that this request returns HTTP 200 only verifies that the search endpoint responds successfully. 
    To verify that searching actually works, we'll eventually need controlled test data in an isolated database.
    """
    response = client.get(
        "/ui/patients",
        params={"q": "John"}
    )
    assert response.status_code == 200

def test_search_filters_patients(client, db_session):
    john = PatientDB(
        first_name = "John",
        last_name = "Smith",
        birthdate = date(1990, 4, 26),
        email = "j.smith@example.com",
        
    )

    alice = PatientDB(
        first_name = "Alice",
        last_name = "Brown",
        birthdate = date(2001, 5, 3),
        email = "alice.b@example.com"
    )

    db_session.add_all([john, alice])
    db_session.flush()

    response = client.get(
        "/ui/patients",
        params={"q": "JOHN"}
    )
    assert response.status_code == 200
    assert "John" in response.text
    assert "Smith" in response.text
    assert "Alice" not in response.text

def test_search_no_results(client):
    response = client.get(
        "/ui/patients",
        params={"q": "Zygmunt"}
    )
    assert response.status_code == 200
    assert "No patients found." in response.text

def test_page_out_of_range_redirects(client):
    response = client.get(
        "/ui/patients",
        params={"page": 999},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/ui/patients?page=1&q="

def test_htmx_page_out_of_range_redirects(client):
    response = client.get(
        "/ui/patients",
        params={"page": 999},
        headers={"HX-Request": "true"}
    )
    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == "/ui/patients?page=1&q="

def test_htmx_returns_partial_html(client):
    response = client.get(
        "/ui/patients",
        headers={"HX-Request": "true"}
    )
    assert response.status_code == 200
    assert "No patients found." in response.text
    assert "<html" not in response.text

def test_delete_patient(client, db_session):
    john = PatientDB(
        first_name = "John",
        last_name = "Smith",
        birthdate = date(1990, 4, 26),
        email = "js@example.com"
    )
    db_session.add(john)
    db_session.flush()

    patient_id = john.id
    response = client.delete(f"/ui/patients/{patient_id}")
    assert response.status_code == 200
    assert response.headers["HX-Trigger"] == "patientDeleted"

    john_deleted = db_session.get(PatientDB, patient_id)
    assert john_deleted is None

def test_delete_patient_twice(client, db_session):
    john = PatientDB(
        first_name = "John",
        last_name = "Smith",
        birthdate = date(1990, 4, 26),
        email = "js@example.com"
    )
    db_session.add(john)
    db_session.flush()

    patient_id = john.id
    first_deletion = client.delete(f"/ui/patients/{patient_id}")
    assert first_deletion.status_code == 200
    assert first_deletion.headers["HX-Trigger"] == "patientDeleted"

    second_deletion = client.delete(f"/ui/patients/{patient_id}")
    assert second_deletion.status_code == 200
    assert second_deletion.headers["HX-Trigger"] == "patientDeleted"

    john_deleted = db_session.get(PatientDB, patient_id)
    assert john_deleted is None

def test_pagination(client, db_session):
    patients = []
    for i in range(12):
        patient = PatientDB(
            first_name=f"Patient{i}",
            last_name="Test",
            birthdate=date(1990, 1, 1),
            email=f"patient{i}@example.com"
        )
        patients.append(patient)

    db_session.add_all(patients)
    db_session.flush()

    response = client.get(
        "/ui/patients",
        params={"page": 3}
    )
    assert response.status_code == 200
    assert "Patient10" in response.text
    assert "Patient11" in response.text
    assert "Patient9" not in response.text

    soup = BeautifulSoup(response.text, "html.parser")
    # This selects <tr> elements whose id attribute starts with "patient-".
    patient_rows = soup.select('tr[id^="patient-"]')
    assert len(patient_rows) == 2

    previous_link = soup.find(
        "a",
        attrs={"hx-get": "/ui/patients?page=2&q="}
    )
    next_links = [
        link
        for link in soup.find_all("a")
        if link.get_text(strip=True) == "Next"
    ]
    assert previous_link is not None
    assert len(next_links) == 0

    second_response = client.get(
        "/ui/patients",
        params={"page": 1}
    )
    assert second_response.status_code == 200

    second_soup = BeautifulSoup(second_response.text, "html.parser")
    second_patient_rows = second_soup.select('tr[id^="patient-"]')
    assert len(second_patient_rows) == 5

    second_previous_links = [
        link
        for link in second_soup.find_all("a")
        if link.get_text(strip=True) == "Previous"
    ]
    second_next_link = second_soup.find(
        "a",
        attrs={"hx-get": "/ui/patients?page=2&q="}
    )
    assert len(second_previous_links) == 0
    assert second_next_link is not None

def test_search_pagination(client, db_session):
    patients = []
    for i in range(12):
        patient = PatientDB(
            first_name = f"John{i}" if i < 8 else f"Alice{i}",
            last_name="Test",
            birthdate=date(1990, 1, 1),
            email=f"patient{i}@example.com"
        )
        patients.append(patient)

    db_session.add_all(patients)
    db_session.flush()

    response = client.get(
        "/ui/patients",
        params={"page": 2, "q": "John"}
    )
    assert response.status_code == 200
    assert "John5" in response.text
    assert "John6" in response.text
    assert "John7" in response.text
    assert "John4" not in response.text
    assert "Alice8" not in response.text

    soup = BeautifulSoup(response.text, "html.parser")
    # This selects <tr> elements whose id attribute starts with "patient-".
    patient_rows = soup.select('tr[id^="patient-"]')
    assert len(patient_rows) == 3

    previous_link = soup.find(
        "a",
        attrs={"hx-get": "/ui/patients?page=1&q=John"}
    )
    next_links = [
        link
        for link in soup.find_all("a")
        if link.get_text(strip=True) == "Next"
    ]
    assert previous_link is not None
    assert len(next_links) == 0

    second_response = client.get(
        "/ui/patients",
        params={"page": 3, "q": "John"},
        follow_redirects=False
    )
    assert second_response.status_code == 303
    assert second_response.headers["location"] == "/ui/patients?page=2&q=John"

    third_response = client.get(
        "/ui/patients",
        params={"page": 3, "q": "John"},
        headers={"HX-Request": "true"}
    )
    assert third_response.status_code == 200
    assert third_response.headers["HX-Redirect"] == "/ui/patients?page=2&q=John"

def test_create_patient_from_form(client, db_session):
    response = client.post(
        "/ui/patients",
        data={
            "first_name": "Anna",
            "last_name": "Smith",
            "birthdate": "1990-05-12",
            "email": "anna.smith@example.com"
        },
        follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/ui/patients"

    statement = select(PatientDB).where(PatientDB.email == "anna.smith@example.com")
    saved_patient = db_session.scalar(statement)
    assert saved_patient is not None
    assert saved_patient.first_name == "Anna"
    assert saved_patient.last_name == "Smith"

def test_create_patient_from_form_invalid_email(client, db_session):
    response = client.post(
        "/ui/patients",
        data={
            "first_name": "Anna",
            "last_name": "Smith",
            "birthdate": "1990-05-12",
            "email": "not-an-email"
        },
        follow_redirects=False
    )
    assert response.status_code == 422

    soup = BeautifulSoup(response.text, "html.parser")
    error_items = soup.select("ul li")
    assert any(
        "email" in item.get_text(strip=True).lower()
        for item in error_items
    )

    statement = select(PatientDB).where(PatientDB.email == "not-an-email")
    saved_patient = db_session.scalar(statement)
    assert saved_patient is None

def test_create_patient_from_form_invalid_email_htmx(client):
    response = client.post(
        "/ui/patients",
        data={
            "first_name": "Anna",
            "last_name": "Smith",
            "birthdate": "1990-05-12",
            "email": "not-an-email"
        },
        headers={"HX-Request": "true"}
    )
    assert response.status_code == 422
    assert "email" in response.text.lower()

    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.find("html") is None
 
def test_create_patient_from_form_htmx(client, db_session):
    response = client.post(
        "/ui/patients",
        data={
            "first_name": "Anna",
            "last_name": "Smith",
            "birthdate": "1990-05-12",
            "email": "anna.smith@example.com"
        },
        headers={"HX-Request": "true"}
    )
    assert response.status_code == 200
    assert "Patient created successfully!" in response.text
    assert "Location" not in response.headers

    statement = select(PatientDB).where(PatientDB.email == "anna.smith@example.com")
    saved_patient = db_session.scalar(statement)
    assert saved_patient is not None
    assert saved_patient.first_name == "Anna"
    assert saved_patient.last_name == "Smith"

def test_create_patient_from_form_without_email(client):
    response = client.post(
        "/ui/patients",
        data={
            "first_name": "Anna",
            "last_name": "Smith",
            "birthdate": "1990-05-12"
        },
        follow_redirects=False
    )
    assert response.status_code == 303