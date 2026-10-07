def test_job_status_reports_correct_progress_and_counts(client):
    payload = {
        "course_name": "DevOps Engineering",
        "completion_date": "October 2026",
        "issuer": "DevOps Institute",
        "recipients": [
            {"name": "User 1", "email": "user1@example.com"},
            {"name": "User 2", "email": "user2@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["job_id"]

    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200

    data = status_resp.json()
    assert data["job_id"] == job_id
    assert data["total"] == 2
    assert data["successful"] == 2
    assert data["failed"] == 0
    assert data["pending"] == 0
    assert data["progress_percent"] == 100.0
    assert data["status"] == "COMPLETED"
