from sqlalchemy import select

from models import AssessmentDB


def test_create_assessment(client):
    # 1. Create a patient using client.post()
    patient_response = client.post(
        "/patients",
        json={
            "first_name": "Anna",
            "last_name": "Smith",
            "birthdate": "1990-05-12"
        }
    )

    # 2. Check that patient creation returned HTTP 201
    assert patient_response.status_code == 201

    # 3. Extract patient_id from the JSON response
    patient_id = patient_response.json()["id"]

    # 4. Create an assessment for that patient
    assessment_response = client.post(
        f"/patients/{patient_id}/assessments",
        json={
            "assessment_date": "2026-10-17",
            "score": 70
        }
    )

    # 5. Verify that assessment creation returned HTTP 201
    assert assessment_response.status_code == 201

    # 6. Verify that the returned score is 70
    assert assessment_response.json()["score"] == 70

def test_database_isolation(client):
    response = client.get("/patients")

    assert response.status_code == 200
    assert response.json() == []

def test_create_assessment_invalid_score(client):
    """Create invalid assessment with score 150, normally is between 0 and 100."""
    patient_response = client.post(
        "/patients",
        json={
            "first_name": "Anna",
            "last_name": "Smith",
            "birthdate": "1990-05-12"
        }
    )

    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    assessment_response = client.post(
        f"/patients/{patient_id}/assessments",
        json={
            "assessment_date": "2026-10-17",
            "score": 150
        }
    )

    assert assessment_response.status_code == 422

    # Verify if uncorrect assessment is not stored in data base
    assessments_response = client.get(
        f"/patients/{patient_id}/assessments"
    )

    assert assessments_response.status_code == 200
    assert assessments_response.json() == []

def test_create_assessment_patient_not_found(client):
    assessment_response = client.post(
        "/patients/999999/assessments",
        json={
                "assessment_date": "2026-10-17",
                "score": 70
        }
    )

    assert assessment_response.json()["detail"] == "Patient of id 999999 not found."

"""Imagine two patients:
- Patient A has an assessment with ID 5.
- Patient B has no assessments.
What should happen when someone requests:
GET /patients/{patient_B_id}/assessments/5
Your endpoint should return 404, even though assessment 5 exists, because it belongs to Patient A."""
def test_assessment_ownership(client):
    first_patient_reponse = client.post(
        "/patients",
        json={
                    "first_name": "Anna",
                    "last_name": "Smith",
                    "birthdate": "1990-05-12"
                }
    )

    assert first_patient_reponse.status_code == 201
    first_patient_id = first_patient_reponse.json()["id"]

    second_patient_reponse = client.post(
        "/patients",
        json={
                    "first_name": "John",
                    "last_name": "Kowalski",
                    "birthdate": "1990-12-12"
                }
    )

    assert second_patient_reponse.status_code == 201
    second_patient_id = second_patient_reponse.json()["id"]

    assert first_patient_id != second_patient_id

    assessment_response = client.post(
        f"/patients/{first_patient_id}/assessments",
        json={
                "assessment_date": "2026-10-17",
                "score": 70
        }
    )

    assert assessment_response.status_code == 201
    assessment_response_id = assessment_response.json()["id"]

    get_first_assessment_response = client.get(
            f"/patients/{first_patient_id}/assessments/{assessment_response_id}",
        )

    assert get_first_assessment_response.status_code == 200

    get_second_assessment_response = client.get(
            f"/patients/{second_patient_id}/assessments/{assessment_response_id}",
        )
    
    assert get_second_assessment_response.status_code == 404

    # to print prints use: uv run pytest -v -s
    print("First patient ID:", first_patient_id)
    print("Assessment ID:", assessment_response_id)
    print("Status:", get_first_assessment_response.status_code)
    print("Response:", get_first_assessment_response.json())

"""Create one patient and three assessments with these dates:
2026-01-10	90
2026-03-15	40
2026-02-20	70
Then retrieve the patient's assessments.
Question: What should the returned order of scores and dates be?
"""

def test_assessment_ordering(client):
    patient_response = client.post(
        "/patients",
        json={
            "first_name": "Anna",
            "last_name": "Smith",
            "birthdate": "1982-12-10"
        }
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    first_assessment_response = client.post(
        f"/patients/{patient_id}/assessments",
        json={
            "assessment_date": "2026-01-10",
            "score": 90
        }
    )
    assert first_assessment_response.status_code == 201

    second_assessment_response = client.post(
        f"/patients/{patient_id}/assessments",
        json={
            "assessment_date": "2026-03-15",
            "score": 40
        }
    )
    assert second_assessment_response.status_code == 201

    third_assessment_response = client.post(
        f"/patients/{patient_id}/assessments",
        json={
            "assessment_date": "2026-02-20",
            "score": 70
        }
    )
    assert third_assessment_response.status_code == 201

    assessments = client.get(
        f"/patients/{patient_id}/assessments"
    )
    assert assessments.status_code == 200

    data = assessments.json()
    assert len(data) == 3

    assert [
        (assessment["assessment_date"], assessment["score"])
        for assessment in data
    ] == [
        ("2026-03-15", 40),
        ("2026-02-20", 70),
        ("2026-01-10", 90),
    ]

def test_cascade_delete(client, db_session):
    """
    This is a good example of when testing only through HTTP endpoints isn't sufficient.
    """
    # 1. Create a patient and two assessments.
    patient_response = client.post(
        "/patients",
        json={
            "first_name": "Anna",
            "last_name": "Smith",
            "birthdate": "1982-12-10"
        }
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    first_assessment = client.post(
        f"/patients/{patient_id}/assessments",
        json={
            "assessment_date": "2026-03-15",
            "score": 40
        }
    )
    assert first_assessment.status_code == 201

    second_assessment = client.post(
        f"/patients/{patient_id}/assessments",
        json={
            "assessment_date": "2026-02-20",
            "score": 70
        }
    )
    assert second_assessment.status_code == 201

    # 2. Delete the patient using DELETE /patients/{patient_id}.
    delete_response = client.delete(
                            f"/patients/{patient_id}"
                        )
    assert delete_response.status_code == 200

    # 3. Verify GET /patients/{patient_id} returns 404.
    patient_deleted = client.get(
        f"/patients/{patient_id}"
    )
    assert patient_deleted.status_code == 404

    # 4. Verify that the associated assessments have also been deleted from PostgreSQL. 
    statement = select(AssessmentDB).where(AssessmentDB.patient_id == patient_id)
    remaining_assessments = db_session.execute(statement).scalars().all()
    assert remaining_assessments == []

def test_patch_patient(client):
    # 1. Create a patient with all four fields.
    patient_response = client.post(
        "/patients",
        json={     
                "first_name": "Anna",
                "last_name": "Smith",
                "birthdate": "1982-12-10",
                "email": "anna@example.com"
            }
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    # 2. PATCH only the last_name.
    patch_response = client.patch(
        f"/patients/{patient_id}",
        json={
            "last_name": "Johnson"
        }
    )
    assert patch_response.status_code == 200

    # 3. Verify changed data.
    expected_patient = {
        "id": patient_id,
        "first_name": "Anna",
        "last_name": "Johnson",
        "birthdate": "1982-12-10",
        "email": "anna@example.com",
    }
    assert patch_response.json() == expected_patient

    # 4. GET the patient again to verify the changes were persisted.
    changed_patient = client.get(
        f"/patients/{patient_id}"
    )
    assert changed_patient.status_code == 200
    assert changed_patient.json() == expected_patient

def test_patch_patient_empty_body(client):
    # 1. Create a patient.
    patient_response = client.post(
        "/patients",
        json={     
                "first_name": "Anna",
                "last_name": "Smith",
                "birthdate": "1982-12-10",
                "email": "anna@example.com"
            }
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    # 2. Send PATCH with an empty JSON object:
    patch_response = client.patch(
        f"/patients/{patient_id}",
        json={}
    )

    # 3. Verify HTTP 400.
    assert patch_response.status_code == 400

    # 4. Verify the error message.
    assert patch_response.json()["detail"] == "At least one field must be provided."

    # 5. Verify the patient's data remains unchanged.
    patient_unchanged = client.get(
        f"/patients/{patient_id}"
    )
    assert patient_unchanged.status_code == 200

    expected_patient = {
        "id": patient_id,
        "first_name": "Anna",
        "last_name": "Smith",
        "birthdate": "1982-12-10",
        "email": "anna@example.com",
    }
    assert patient_unchanged.json() == expected_patient

def test_patch_patient_null_last_name(client):
    # 1. Create a patient.
    patient_response = client.post(
        "/patients",
        json={     
                "first_name": "Anna",
                "last_name": "Smith",
                "birthdate": "1982-12-10",
                "email": "anna@example.com"
            }
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    # 2. PATCH with {"last_name": None}.
    patch_response = client.patch(
        f"/patients/{patient_id}",
        json={
            "last_name": None
        }
    )

    # 3. Verify HTTP 422.
    assert patch_response.status_code == 422

    # 4. Verify the last name remains unchanged.
    patient_unchanged = client.get(
        f"/patients/{patient_id}"
    )
    assert patient_unchanged.status_code == 200

    last_name = patient_unchanged.json()["last_name"]
    assert last_name == "Smith" 

def test_patch_patient_remove_email(client):
    # 1. Create a patient with an email address.
    patient_response = client.post(
        "/patients",
        json={     
                "first_name": "Anna",
                "last_name": "Smith",
                "birthdate": "1982-12-10",
                "email": "anna@example.com"
            }
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    # 2. PATCH the patient using {"email": None}.
    patch_response = client.patch(
        f"/patients/{patient_id}",
        json={
            "email": None
        }
    )

    # 3. Verify HTTP 200.
    assert patch_response.status_code == 200

    # 4. Verify the PATCH response contains email=None.
    assert patch_response.json()["email"] is None

    # 5. GET the patient again.
    patient_changed = client.get(
        f"/patients/{patient_id}"
    )
    assert patient_changed.status_code == 200

    # 6. Verify email is still None and other fields are unchanged.
    expected_patient = {
        "id": patient_id,
        "first_name": "Anna",
        "last_name": "Smith",
        "birthdate": "1982-12-10",
        "email": None,
    }
    assert patient_changed.json() == expected_patient

def test_put_patient(client):
    # 1. Create a patient:
    patient_response = client.post(
        "/patients",
        json={     
                "first_name": "Anna",
                "last_name": "Smith",
                "birthdate": "1982-12-10",
                "email": "anna@example.com"
            }
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    # 2. Send PUT with:
    put_response = client.put(
        f"/patients/{patient_id}",
        json={
           "first_name": "Anna",
            "last_name": "Johnson",
            "birthdate": "1982-12-10",
            "email": "anna.johnson@example.com" 
        }
    )

    # 3. Verify HTTP 200.
    assert put_response.status_code == 200

    # 4. Verify the PUT response contains
    #    the updated patient.
    expected_patient = {
        "id": patient_id,
        "first_name": "Anna",
        "last_name": "Johnson",
        "birthdate": "1982-12-10",
        "email": "anna.johnson@example.com"
    }
    assert put_response.json() == expected_patient

    # 5. GET the patient again.
    patient_changed = client.get(
        f"/patients/{patient_id}"
    )
    assert patient_changed.status_code == 200

    # 6. Verify the complete updated data.
    assert patient_changed.json() == expected_patient

def test_put_patient_missing_required_fields(client):
    # 1. Create a patient.
    patient_response = client.post(
        "/patients",
        json={     
                "first_name": "Anna",
                "last_name": "Smith",
                "birthdate": "1982-12-10",
                "email": "anna@example.com"
            }
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    # 2. Send PUT containing only last_name
    put_response = client.put(
        f"/patients/{patient_id}",
        json={
            "last_name": "Johnson",
        }
    )

    # 3. Verify HTTP 422.
    assert put_response.status_code == 422

    # 4. GET the patient again.
    patient_unchanged = client.get(
        f"/patients/{patient_id}"
    )
    assert patient_unchanged.status_code == 200

    # 5. Verify the original patient data remains unchanged.
    expected_patient={
            "id": patient_id,     
            "first_name": "Anna",
            "last_name": "Smith",
            "birthdate": "1982-12-10",
            "email": "anna@example.com"
        }
    assert patient_unchanged.json() == expected_patient

def test_put_patient_omitted_email(client):
    # 1. Create a patient with an email address.
    patient_response = client.post(
        "/patients",
        json={     
                "first_name": "Anna",
                "last_name": "Smith",
                "birthdate": "1982-12-10",
                "email": "anna@example.com"
            }
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    # 2. Send PUT with all required fields, but omit email.
    put_response = client.put(
        f"/patients/{patient_id}",
        json={
            "first_name": "Anna",
            "last_name": "Johnson",
            "birthdate": "1982-12-10"
        }
    )

    # 3. Verify HTTP 200.
    assert put_response.status_code == 200

    # 4. GET the patient again.
    patient_changed = client.get(
        f"/patients/{patient_id}"
    )
    assert patient_changed.status_code == 200

    # 5. Verify email is None and the other fields have their expected values.
    expected_patient={
            "id": patient_id,     
            "first_name": "Anna",
            "last_name": "Johnson",
            "birthdate": "1982-12-10",
            "email": None
        }
    assert patient_changed.json() == expected_patient

def test_delete_patient_twice(client):
    # 1. Create a patient.
    patient_response = client.post(
        "/patients",
        json={     
                "first_name": "Anna",
                "last_name": "Smith",
                "birthdate": "1982-12-10",
                "email": "anna@example.com"
            }
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    # 2. Delete the patient. Verify HTTP 200.
    delete_response = client.delete(
        f"/patients/{patient_id}"
    )
    assert delete_response.status_code == 200

    # 3. Try deleting the same patient again. Verify HTTP 404.
    delete_again = client.delete(
        f"/patients/{patient_id}"
    )
    assert delete_again.status_code == 404

def test_get_deleted_patient_returns_404(client):
    # 1. Request a patient ID that does not exist.
    patient_response = client.post(
        "/patients",
        json={     
                "first_name": "Anna",
                "last_name": "Smith",
                "birthdate": "1982-12-10",
                "email": "anna@example.com"
            }
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    delete_response = client.delete(
        f"/patients/{patient_id}"
    )
    assert delete_response.status_code == 200

    get_patient = client.get(
        f"/patients/{patient_id}"
    )

    # 2. Verify HTTP 404 and the error message.
    assert get_patient.status_code == 404
    assert get_patient.json()["detail"] == f"Patient of id {patient_id} not found."

def test_create_patient_invalid_email(client):
    # 1. Send POST /patients with:
    patient_response = client.post(
        "/patients",
        json={
                "first_name": "Anna",
                "last_name": "Smith",
                "birthdate": "1982-12-10",
                "email": "not-an-email"
        }
    )
    # 2. Verify HTTP 422.
    assert patient_response.status_code == 422

    # 3. Verify that the validation error concerns the email field.
    assert patient_response.json()["detail"][0]["msg"] == ("value is not a valid email address: " 
                                                     "An email address must have an @-sign.")
    """
    Let's understand this expression.
    - errors is a list of validation-error dictionaries.
    - for error in errors iterates through the list.
    - error["loc"] identifies the location of each error.
    - any() returns True if at least one error matches.
    This approach is more robust because it doesn't depend on the exact wording of Pydantic's error messages.
    """
    errors = patient_response.json()["detail"]
    assert any(
        error["loc"] == ["body", "email"]
        for error in errors
    )

def test_create_patient_multiple_validation_errors(client):
    patient_response = client.post(
        "/patients",
        json={
            "first_name": "Al",
            "last_name": "Smith",
            "birthdate": "1982-12-10",
            "email": "not-an-email"
        }
    )
    # 2. Verify HTTP 422.
    assert patient_response.status_code == 422

    # 3. Extract the validation errors.
    errors = patient_response.json()["detail"]
    assert len(errors) == 2

    # 4. Verify that first_name caused an error.
    assert any(
        error["loc"] == ["body", "first_name"]
        for error in errors
    )
    # 5. Verify that email caused an error.
    assert any(
        error["loc"] == ["body", "email"]
        for error in errors
    )

def test_create_patient_missing_birthdate(client):
    # 1. POST a patient with first_name, last_name and email, but no birthdate.
    patient_response = client.post(
        "/patients",
        json={
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice.smith@example.com"
        }
    )
    # 2. Verify HTTP 422.
    assert patient_response.status_code == 422

    # 3. Verify the validation error concerns the birthdate field.
    errors = patient_response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["type"] == "missing"
    assert errors[0]["loc"] == ["body", "birthdate"]

def test_create_patient_future_birthdate(client):
    # 1. POST a patient whose birthdate is 2035-01-01.
    patient_response = client.post(
        "/patients",
        json={
            "first_name": "Alice",
            "last_name": "Smith",
            "birthdate": "2035-01-01",
            "email": "alice.smith@example.com"
        }
    )
    # 2. Verify HTTP 422.
    assert patient_response.status_code == 422

    # 3. Verify the error concerns birthdate.
    errors = patient_response.json()["detail"]
    assert len(errors) == 1
    assert errors[0]["loc"] == ["body", "birthdate"]

    # 4. Inspect the error type.
    assert errors[0]["type"] == "value_error"

def test_create_patient_invalid_birthdate_format(client):
    # 1. POST a patient with birthdate = "2026-15-40"
    patient_response = client.post(
        "/patients",
        json={
            "first_name": "Alice",
            "last_name": "Smith",
            "birthdate": "2026-15-40",
            "email": "alice.smith@example.com"
        }
    )
    # 2. Verify HTTP 422.
    assert patient_response.status_code == 422

    # 3. Verify exactly one validation error.
    errors = patient_response.json()["detail"]
    assert len(errors) == 1

    # 4. Verify the error concerns birthdate.
    assert errors[0]["loc"] == ["body", "birthdate"]

    # 5. Verify the error type is "date_from_datetime_parsing".
    assert errors[0]["type"] == "date_from_datetime_parsing"