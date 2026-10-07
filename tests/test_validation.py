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
    assert "Duplicate email address" in data["failures"][0]["error"]


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
