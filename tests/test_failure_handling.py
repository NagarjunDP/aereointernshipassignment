import app.processor as processor


def test_single_certificate_error_marks_job_completed_with_errors(client, monkeypatch):
    original_generator = processor.generate_certificate_pdf

    def mock_generator(cert, job, output_path):
        if cert.recipient_name == "Broken Recipient":
            raise RuntimeError("Rendering error")
        return original_generator(cert, job, output_path)

    monkeypatch.setattr(processor, "generate_certificate_pdf", mock_generator)

    payload = {
        "course_name": "System Architecture",
        "completion_date": "October 2026",
        "issuer": "Engineering Org",
        "recipients": [
            {"name": "Valid Recipient 1", "email": "valid1@example.com"},
            {"name": "Broken Recipient", "email": "broken@example.com"},
            {"name": "Valid Recipient 2", "email": "valid2@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["job_id"]

    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    data = status_resp.json()

    assert data["total"] == 3
    assert data["successful"] == 2
    assert data["failed"] == 1
    assert data["status"] == "COMPLETED_WITH_ERRORS"
    assert len(data["failures"]) == 1
    assert data["failures"][0]["name"] == "Broken Recipient"
