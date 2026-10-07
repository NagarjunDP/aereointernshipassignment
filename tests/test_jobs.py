import app.config as config


def test_creating_job_from_json_returns_accepted(client):
    payload = {
        "course_name": "Full-Stack Web Development",
        "completion_date": "October 2026",
        "issuer": "Tech Academy",
        "recipients": [
            {"name": "Alice Smith", "email": "alice@example.com"},
            {"name": "Bob Jones", "email": "bob@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["total"] == 2


def test_creating_job_from_valid_csv_upload_returns_accepted(client):
    csv_content = "name,email\nCharlie Brown,charlie@example.com\nDiana Prince,diana@example.com"
    files = {"file": ("recipients.csv", csv_content.encode("utf-8"), "text/csv")}
    data = {
        "course_name": "Data Science",
        "completion_date": "October 2026",
        "issuer": "University X",
    }
    response = client.post("/api/v1/jobs/upload", data=data, files=files)
    assert response.status_code == 202
    assert response.json()["total"] == 2


def test_csv_upload_with_missing_course_field_returns_422(client):
    csv_content = "name,email\nCharlie,charlie@example.com"
    files = {"file": ("recipients.csv", csv_content.encode("utf-8"), "text/csv")}
    data = {"course_name": "", "completion_date": "October 2026", "issuer": "University X"}
    response = client.post("/api/v1/jobs/upload", data=data, files=files)
    assert response.status_code == 422


def test_csv_upload_with_empty_file_returns_422(client):
    files = {"file": ("empty.csv", b"", "text/csv")}
    data = {"course_name": "Web Dev", "completion_date": "October 2026", "issuer": "Academy"}
    response = client.post("/api/v1/jobs/upload", data=data, files=files)
    assert response.status_code == 422


def test_exceeding_recipient_limit_returns_422(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_RECIPIENTS_PER_JOB", 2)
    payload = {
        "course_name": "Web Dev",
        "completion_date": "October 2026",
        "issuer": "Academy",
        "recipients": [
            {"name": "User 1", "email": "u1@example.com"},
            {"name": "User 2", "email": "u2@example.com"},
            {"name": "User 3", "email": "u3@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    assert "exceeds maximum allowed limit" in response.json()["detail"]
