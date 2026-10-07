from datetime import datetime, timezone
from app.config import OUTPUT_DIR
from app.database import SessionLocal
from app.generator import generate_certificate_pdf
from app.models import Job, Certificate, JobStatus, CertStatus


def process_job(job_id: str) -> None:
    """Process certificates for a job using an isolated database session."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = JobStatus.PROCESSING.value
        db.commit()

        certificates = db.query(Certificate).filter(Certificate.job_id == job_id).all()

        for cert in certificates:
            if cert.status == CertStatus.FAILED.value:
                continue

            # Path safety: filename derived solely from server UUID cert.id
            output_path = (OUTPUT_DIR / job_id / f"{cert.id}.pdf").resolve()
            try:
                generate_certificate_pdf(cert, job, output_path)
                cert.status = CertStatus.SUCCESS.value
                cert.file_path = str(output_path)
                job.success_count += 1
            except Exception as e:
                cert.status = CertStatus.FAILED.value
                cert.error_message = str(e) or "Failed to generate certificate PDF"
                job.failure_count += 1

            db.commit()

        if job.success_count == 0:
            job.status = JobStatus.FAILED.value
        elif job.failure_count == 0:
            job.status = JobStatus.COMPLETED.value
        else:
            job.status = JobStatus.COMPLETED_WITH_ERRORS.value

        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED.value
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
