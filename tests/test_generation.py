from pathlib import Path
from types import SimpleNamespace
from app.generator import generate_certificate_pdf


def test_generating_certificate_pdf_creates_valid_pdf_file(tmp_path: Path):
    cert = SimpleNamespace(recipient_name="John Doe", code="CERT-TEST12")
    job = SimpleNamespace(
        course_name="Machine Learning",
        completion_date="October 2026",
        issuer="AI Academy",
    )
    output_path = tmp_path / "certs" / "test_cert.pdf"

    generated_file = generate_certificate_pdf(cert, job, output_path)
    assert Path(generated_file).exists()

    with open(generated_file, "rb") as f:
        header = f.read(4)
    assert header == b"%PDF"


def test_generating_certificate_pdf_with_long_name_succeeds(tmp_path: Path):
    long_name = "Very Long Recipient Name That Exceeds Normal Certificate Header Width Guidelines"
    cert = SimpleNamespace(recipient_name=long_name, code="CERT-LONG01")
    job = SimpleNamespace(
        course_name="Advanced Architectural Pattern Design for Distributed Systems",
        completion_date="October 2026",
        issuer="Global Engineering Institute",
    )
    output_path = tmp_path / "certs" / "long_cert.pdf"

    generated_file = generate_certificate_pdf(cert, job, output_path)
    assert Path(generated_file).exists()
