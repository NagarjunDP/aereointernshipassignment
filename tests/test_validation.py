def test_empty_recipients_list_returns_422(client):
    payload = {
        "course_name": "Web Dev",
        "completion_date": "October 2026",
        "issuer": "Academy",
        "recipients": [],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


def test_missing_required_course_field_returns_422(client):
    payload = {
        "course_name": "   ",
        "completion_date": "October 2026",
        "issuer": "Academy",
        "recipients": [{"name": "Alice", "email": "alice@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


def test_invalid_email_marks_only_that_recipient_failed(client):
    payload = {
        "course_name": "Cloud Computing",
        "completion_date": "October 2026",
        "issuer": "Cloud Institute",
        "recipients": [
            {"name": "Valid User", "email": "valid@example.com"},
            {"name": "Bad Email", "email": "not-an-email"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["total"] == 2
    assert data["successful"] == 1
    assert data["failed"] == 1
    assert data["status"] == "COMPLETED_WITH_ERRORS"
    assert data["failures"][0]["name"] == "Bad Email"
    assert "Invalid email address format" in data["failures"][0]["error"]


def test_duplicate_email_in_same_job_marks_duplicate_failed(client):
    payload = {
        "course_name": "Security 101",
        "completion_date": "October 2026",
        "issuer": "Sec Corp",
        "recipients": [
            {"name": "First Entry", "email": "user@example.com"},
            {"name": "Second Entry", "email": "USER@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    data = status_resp.json()
    assert data["total"] == 2
    assert data["successful"] == 1
    assert data["failed"] == 1
    assert "Duplicate email" in data["failures"][0]["error"]


def test_empty_recipient_name_marks_recipient_failed(client):
    payload = {
        "course_name": "DevOps",
        "completion_date": "October 2026",
        "issuer": "Academy",
        "recipients": [
            {"name": "   ", "email": "noname@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["job_id"]

    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    data = status_resp.json()
    assert data["failed"] == 1
    assert "name cannot be empty" in data["failures"][0]["error"]


def test_duplicate_email_in_json_job_marks_second_occurrence_failed(client):
    payload = {
        "course_name": "Security",
        "completion_date": "2026-10-07",
        "issuer": "Academy",
        "recipients": [
            {"name": "First", "email": "dup@example.com"},
            {"name": "Second", "email": "dup@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["job_id"]

    data = client.get(f"/api/v1/jobs/{job_id}").json()
    assert data["total"] == 2
    assert data["successful"] == 1
    assert data["failed"] == 1
    assert "Duplicate email" in data["failures"][0]["error"]
    # The second one (name="Second") should be the one that failed
    assert data["failures"][0]["name"] == "Second"


def test_case_different_duplicate_email_is_rejected(client):
    # "A@Example.com" and "a@example.com" must be treated as the same address
    payload = {
        "course_name": "Security",
        "completion_date": "2026-10-07",
        "issuer": "Academy",
        "recipients": [
            {"name": "First", "email": "A@Example.com"},
            {"name": "Second", "email": "a@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["job_id"]

    data = client.get(f"/api/v1/jobs/{job_id}").json()
    assert data["successful"] == 1
    assert data["failed"] == 1
    assert "Duplicate email" in data["failures"][0]["error"]


def test_duplicate_email_in_csv_upload_marks_second_occurrence_failed(client):
    csv_content = "name,email\nFirst,dup@example.com\nSecond,DUP@EXAMPLE.COM"
    files = {"file": ("r.csv", csv_content.encode(), "text/csv")}
    data = {"course_name": "Test", "completion_date": "2026-10-07", "issuer": "Org"}

    response = client.post("/api/v1/jobs/upload", data=data, files=files)
    job_id = response.json()["job_id"]

    result = client.get(f"/api/v1/jobs/{job_id}").json()
    assert result["successful"] == 1
    assert result["failed"] == 1
    assert "Duplicate email" in result["failures"][0]["error"]


def test_200_recipients_with_three_bad_rows_produces_197_success(client):
    # Mirrors the original 200-recipient manual test exactly
    recipients = [{"name": f"Student {i}", "email": f"student{i}@example.com"} for i in range(1, 201)]
    recipients[10] = {"name": "Bad Email", "email": "not-an-email"}          # invalid email
    recipients[20] = {"name": "   ", "email": "blank@example.com"}           # blank name
    recipients[30] = {"name": "Duplicate", "email": "student1@example.com"}  # duplicate of index 0

    payload = {
        "course_name": "Python Programming",
        "completion_date": "2026-10-07",
        "issuer": "Aereo Academy",
        "recipients": recipients,
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    data = client.get(f"/api/v1/jobs/{job_id}").json()
    assert data["total"] == 200
    assert data["successful"] == 197
    assert data["failed"] == 3
    assert data["status"] == "COMPLETED_WITH_ERRORS"

    failure_names = {f["name"] for f in data["failures"]}
    assert "Bad Email" in failure_names
    assert "Duplicate" in failure_names
    # blank name recipient has name="" after stripping
    assert any(f["email"] == "blank@example.com" for f in data["failures"])
