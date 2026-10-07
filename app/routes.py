import csv
import io
import re
import uuid
import zipfile
from pathlib import Path
from typing import List, Set
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.config import OUTPUT_DIR
import app.config as config
from app.database import get_db
from app.models import Job, Certificate, JobStatus, CertStatus
from app.processor import process_job
from app.schemas import (
    JobCreate,
    JobAcceptedResponse,
    JobStatusResponse,
    RecipientFailure,
    CertificateResponse,
    VerifyResponse,
    RecipientInput,
)

router = APIRouter(prefix="/api/v1")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip().lower()))


def generate_cert_code() -> str:
    return f"CERT-{uuid.uuid4().hex[:6].upper()}"


def sanitize_filename(name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", name or "").strip("_")
    return clean if clean else "certificate"


@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED, response_model=JobAcceptedResponse)
def create_job(
    payload: JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if len(payload.recipients) > config.MAX_RECIPIENTS_PER_JOB:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Recipient count exceeds maximum allowed limit of {config.MAX_RECIPIENTS_PER_JOB}",
        )

    job_id = str(uuid.uuid4())
    initial_failure_count = 0
    seen_emails: Set[str] = set()

    job = Job(
        id=job_id,
        course_name=payload.course_name.strip(),
        completion_date=payload.completion_date.strip(),
        issuer=payload.issuer.strip(),
        status=JobStatus.PENDING.value,
        total_count=len(payload.recipients),
        success_count=0,
        failure_count=0,
    )
    db.add(job)

    for r in payload.recipients:
        name = (r.name or "").strip()
        email = (r.email or "").strip().lower()

        if not name:
            cert = Certificate(
                job_id=job_id,
                recipient_name=name,
                recipient_email=email,
                code=generate_cert_code(),
                status=CertStatus.FAILED.value,
                error_message="Recipient name cannot be empty",
            )
            initial_failure_count += 1
        elif len(name) > 255:
            cert = Certificate(
                job_id=job_id,
                recipient_name=name,
                recipient_email=email,
                code=generate_cert_code(),
                status=CertStatus.FAILED.value,
                error_message="Recipient name exceeds maximum allowed length of 255 characters",
            )
            initial_failure_count += 1
        elif not is_valid_email(email):
            cert = Certificate(
                job_id=job_id,
                recipient_name=name,
                recipient_email=email,
                code=generate_cert_code(),
                status=CertStatus.FAILED.value,
                error_message="Invalid email address format",
            )
            initial_failure_count += 1
        elif email in seen_emails:
            cert = Certificate(
                job_id=job_id,
                recipient_name=name,
                recipient_email=email,
                code=generate_cert_code(),
                status=CertStatus.FAILED.value,
                error_message="Duplicate email address in job",
            )
            initial_failure_count += 1
        else:
            seen_emails.add(email)
            cert = Certificate(
                job_id=job_id,
                recipient_name=name,
                recipient_email=email,
                code=generate_cert_code(),
                status=CertStatus.PENDING.value,
            )

        db.add(cert)

    job.failure_count = initial_failure_count
    db.commit()

    background_tasks.add_task(process_job, job_id)

    return JobAcceptedResponse(
        job_id=job_id,
        status=JobStatus.PENDING.value,
        total=job.total_count,
    )


@router.post("/jobs/upload", status_code=status.HTTP_202_ACCEPTED, response_model=JobAcceptedResponse)
async def upload_job_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    course_name: str = Form(...),
    completion_date: str = Form(...),
    issuer: str = Form(...),
    db: Session = Depends(get_db),
):
    if not course_name or not course_name.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="course_name cannot be empty")
    if not completion_date or not completion_date.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="completion_date cannot be empty")
    if not issuer or not issuer.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="issuer cannot be empty")

    try:
        content = await file.read()
        text = content.decode("utf-8-sig")
    except Exception:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid CSV file encoding")

    if not text.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Uploaded CSV file is empty")

    reader = csv.DictReader(io.StringIO(text))
    recipients: List[RecipientInput] = []

    if reader.fieldnames:
        for row in reader:
            if not row:
                continue
            normalized = {str(k).strip().lower(): str(v).strip() for k, v in row.items() if k is not None}
            name = normalized.get("name") or normalized.get("recipient_name") or ""
            email = normalized.get("email") or normalized.get("recipient_email") or ""
            if name or email:
                recipients.append(RecipientInput(name=name, email=email))

    if not recipients:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CSV file must contain at least one valid recipient row",
        )

    job_payload = JobCreate(
        course_name=course_name.strip(),
        completion_date=completion_date.strip(),
        issuer=issuer.strip(),
        recipients=recipients,
    )

    return create_job(job_payload, background_tasks, db)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    pending_count = job.total_count - (job.success_count + job.failure_count)
    if pending_count < 0:
        pending_count = 0

    progress_percent = (
        round(((job.success_count + job.failure_count) / job.total_count) * 100.0, 2)
        if job.total_count > 0
        else 0.0
    )

    failed_certs = (
        db.query(Certificate)
        .filter(Certificate.job_id == job_id, Certificate.status == CertStatus.FAILED.value)
        .all()
    )

    failures = [
        RecipientFailure(
            name=c.recipient_name,
            email=c.recipient_email,
            error=c.error_message or "Unknown error",
        )
        for c in failed_certs
    ]

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        total=job.total_count,
        successful=job.success_count,
        failed=job.failure_count,
        pending=pending_count,
        progress_percent=progress_percent,
        failures=failures,
    )


@router.get("/jobs/{job_id}/certificates", response_model=List[CertificateResponse])
def list_job_certificates(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    certs = db.query(Certificate).filter(Certificate.job_id == job_id).all()
    return [
        CertificateResponse(
            id=c.id,
            name=c.recipient_name,
            email=c.recipient_email,
            status=c.status,
            error=c.error_message,
            code=c.code,
        )
        for c in certs
    ]


@router.get("/certificates/{certificate_id}")
def download_certificate_pdf(certificate_id: str, db: Session = Depends(get_db)):
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    if cert.status != CertStatus.SUCCESS.value or not cert.file_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Certificate has not been generated or failed",
        )

    file_path = Path(cert.file_path)
    if not file_path.is_absolute():
        file_path = (OUTPUT_DIR / file_path).resolve()
    else:
        file_path = file_path.resolve()

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate PDF file not found on disk")

    safe_name = sanitize_filename(cert.recipient_name)
    download_filename = f"{safe_name}-certificate.pdf"

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=download_filename,
    )


@router.get("/jobs/{job_id}/download")
def download_job_zip(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    successful_certs = (
        db.query(Certificate)
        .filter(Certificate.job_id == job_id, Certificate.status == CertStatus.SUCCESS.value)
        .all()
    )

    if not successful_certs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No successful certificates available to download",
        )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for c in successful_certs:
            if c.file_path:
                p = Path(c.file_path)
                if not p.is_absolute():
                    p = (OUTPUT_DIR / p).resolve()
                else:
                    p = p.resolve()

                if p.exists():
                    safe_name = sanitize_filename(c.recipient_name)
                    filename_in_zip = f"{safe_name}_{c.code}.pdf"
                    zf.write(p, arcname=filename_in_zip)

    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="certificates-{job_id}.zip"'},
    )


@router.get("/verify/{code}", response_model=VerifyResponse)
def verify_certificate_code(code: str, db: Session = Depends(get_db)):
    cert = db.query(Certificate).filter(Certificate.code == code).first()
    if not cert or cert.status != CertStatus.SUCCESS.value:
        return VerifyResponse(valid=False, code=code)

    job = db.query(Job).filter(Job.id == cert.job_id).first()
    return VerifyResponse(
        valid=True,
        recipient_name=cert.recipient_name,
        course_name=job.course_name if job else None,
        completion_date=job.completion_date if job else None,
        issuer=job.issuer if job else None,
        code=cert.code,
    )
