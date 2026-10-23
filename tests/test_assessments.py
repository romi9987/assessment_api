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