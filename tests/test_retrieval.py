import io
import zipfile
import app.processor as processor


def test_retrieving_successful_pdf_returns_200_and_correct_content_type(client):
    payload = {
        "course_name": "API Design",
        "completion_date": "October 2026",
        "issuer": "REST School",
        "recipients": [{"name": "Jane Smith", "email": "jane@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["job_id"]

    certs_resp = client.get(f"/api/v1/jobs/{job_id}/certificates")
    cert_id = certs_resp.json()[0]["id"]

    pdf_resp = client.get(f"/api/v1/certificates/{cert_id}")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in pdf_resp.headers["content-disposition"]
    assert pdf_resp.content.startswith(b"%PDF")


def test_retrieving_failed_certificate_returns_409(client, monkeypatch):
    def mock_generator(cert, job, output_path):
        raise ValueError("Failed rendering")

    monkeypatch.setattr(processor, "generate_certificate_pdf", mock_generator)

    payload = {
        "course_name": "API Design",
        "completion_date": "October 2026",
        "issuer": "REST School",
        "recipients": [{"name": "Broken User", "email": "broken@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["job_id"]

    certs_resp = client.get(f"/api/v1/jobs/{job_id}/certificates")
    cert_id = certs_resp.json()[0]["id"]

    pdf_resp = client.get(f"/api/v1/certificates/{cert_id}")
    assert pdf_resp.status_code == 409


def test_retrieving_nonexistent_certificate_returns_404(client):
    response = client.get("/api/v1/certificates/unknown-id-0000")
    assert response.status_code == 404


def test_downloading_job_zip_returns_all_successful_pdfs(client):
    payload = {
        "course_name": "Archival",
        "completion_date": "October 2026",
        "issuer": "Zip Institute",
        "recipients": [
            {"name": "Person A", "email": "a@example.com"},
            {"name": "Person B", "email": "b@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["job_id"]

    zip_resp = client.get(f"/api/v1/jobs/{job_id}/download")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"

    with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
        namelist = zf.namelist()
        assert len(namelist) == 2
        for filename in namelist:
            file_data = zf.read(filename)
            assert file_data.startswith(b"%PDF")


def test_verifying_valid_code_returns_details_without_email(client):
    payload = {
        "course_name": "Security 101",
        "completion_date": "October 2026",
        "issuer": "Sec Corp",
        "recipients": [{"name": "Verified Student", "email": "student@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    job_id = response.json()["job_id"]

    certs_resp = client.get(f"/api/v1/jobs/{job_id}/certificates")
    valid_code = certs_resp.json()[0]["code"]

    verify_resp = client.get(f"/api/v1/verify/{valid_code}")
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["valid"] is True
    assert v_data["recipient_name"] == "Verified Student"
    assert v_data["course_name"] == "Security 101"
    assert "email" not in v_data


def test_verifying_invalid_code_returns_invalid_status(client):
    verify_resp = client.get("/api/v1/verify/CERT-INVALID999")
    assert verify_resp.status_code == 200
    assert verify_resp.json()["valid"] is False
