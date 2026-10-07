# Bulk Certificate Generator

A backend API and web application for generating bulk PDF certificates from course and recipient data.
Built using Python, FastAPI, SQLAlchemy 2.0, and ReportLab.
Designed with simple and readable code for technical review.

## Features

- Asynchronous background processing for bulk certificate requests.
- Individual per-recipient validation so valid records succeed even if some entries fail.
- Isolated PDF generation per recipient ensuring one error never halts the batch.
- ReportLab PDF generator using a single predefined landscape A4 template.
- Live job progress tracking and status monitoring endpoints.
- Single PDF downloads, batch ZIP download, and certificate verification by unique code.
- Static single-page dashboard for manual input and CSV upload.

## Tech Stack

- Python 3.14 / 3.10+
- FastAPI
- Uvicorn
- SQLAlchemy 2.0
- Pydantic v2
- ReportLab
- Pytest
- HTTPX

## Setup

1. Clone the repository and navigate to the root directory:
   ```bash
   cd aereo
   ```

2. Create and activate a virtual environment:
   - On macOS/Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - On Windows:
     ```cmd
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

## Run the Application

Start the Uvicorn development server:
```bash
uvicorn app.main:app --reload
```

- Web Dashboard: http://127.0.0.1:8000/
- API Documentation (Swagger UI): http://127.0.0.1:8000/docs

## Run Tests

Run the test suite using pytest:
```bash
pytest
```

## API Overview

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/jobs` | Submit a bulk certificate generation job using JSON payload |
| POST | `/api/v1/jobs/upload` | Submit a bulk certificate generation job via CSV upload |
| GET | `/api/v1/jobs/{job_id}` | Get progress percentage, total/success/failed counts, and failure reasons |
| GET | `/api/v1/jobs/{job_id}/certificates` | List all individual certificates for a job |
| GET | `/api/v1/certificates/{certificate_id}` | Download a single generated PDF certificate |
| GET | `/api/v1/jobs/{job_id}/download` | Download a ZIP file containing all successful PDFs for a job |
| GET | `/api/v1/verify/{code}` | Verify authenticity of a certificate code |

## Submit a Generation Request

### JSON Request Example

Command:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "course_name": "Full-Stack Software Engineering",
    "completion_date": "October 2026",
    "issuer": "Tech Academy",
    "recipients": [
      {"name": "Alice Smith", "email": "alice@example.com"},
      {"name": "Bob Jones", "email": "bob@example.com"},
      {"name": "Invalid Recipient", "email": "invalid-email"}
    ]
  }'
```

Response:
```json
{"job_id":"be42c79c-f378-4369-8e7d-a5338978011b","status":"PENDING","total":3}
```

### CSV Upload Example

Command:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/jobs/upload \
  -F "course_name=Data Science 101" \
  -F "completion_date=October 2026" \
  -F "issuer=University X" \
  -F "file=@recipients.csv"
```

Response:
```json
{"job_id":"e9aaf297-858f-4f82-ba32-bd5340a29d27","status":"PENDING","total":2}
```

## Check Progress

Command:
```bash
curl http://127.0.0.1:8000/api/v1/jobs/be42c79c-f378-4369-8e7d-a5338978011b
```

Response:
```json
{
  "job_id": "be42c79c-f378-4369-8e7d-a5338978011b",
  "status": "COMPLETED_WITH_ERRORS",
  "total": 3,
  "successful": 2,
  "failed": 1,
  "pending": 0,
  "progress_percent": 100.0,
  "failures": [
    {
      "name": "Invalid Recipient",
      "email": "invalid-email",
      "error": "Invalid email address format"
    }
  ]
}
```

## Retrieve Certificates

### List Certificates in Job
```bash
curl http://127.0.0.1:8000/api/v1/jobs/be42c79c-f378-4369-8e7d-a5338978011b/certificates
```

### Download Single PDF
```bash
curl -O -J http://127.0.0.1:8000/api/v1/certificates/9601c632-99f3-4dec-838a-fc67260d7fdd
```

### Download ZIP Archive
```bash
curl -o certificates.zip http://127.0.0.1:8000/api/v1/jobs/be42c79c-f378-4369-8e7d-a5338978011b/download
```

## Verify a Certificate

Command:
```bash
curl http://127.0.0.1:8000/api/v1/verify/CERT-3BF813
```

Response:
```json
{
  "valid": true,
  "recipient_name": "Alice Smith",
  "course_name": "Full-Stack Software Engineering",
  "completion_date": "October 2026",
  "issuer": "Tech Academy",
  "code": "CERT-3BF813"
}
```

## Design Decisions

- **FastAPI BackgroundTasks**: Selected over Celery because it runs in-process without requiring external services like Redis or RabbitMQ. This keeps deployment simple for a single-server application. A message queue like Celery would be introduced if job processing needed multi-server distribution or persistent retry queues across server restarts.
- **Per-Recipient Validation**: Rejection of an entire bulk request due to one bad recipient creates poor user experience. Each recipient is validated individually so valid certificates generate immediately, while invalid records are marked as FAILED with descriptive error messages.
- **Disk Storage for PDFs**: Storing PDF files on disk and saving only the relative file path string in the database prevents database bloat and preserves query performance.
- **SQLite Default & PostgreSQL Compatibility**: SQLite is used by default for zero-setup local development. Because SQLAlchemy 2.0 ORM is used exclusively, switching to PostgreSQL requires only updating the `DATABASE_URL` environment variable (for example, `export DATABASE_URL="postgresql://user:pass@localhost:5432/certs"`).
- **Session Isolation & Live Progress**: The background function opens its own database session (`SessionLocal()`) and commits after processing each recipient. This allows polling clients to observe live progress while avoiding session thread-sharing issues.
- **Failure Isolation**: PDF generation for each certificate occurs inside a dedicated `try/except` block. If drawing or file output fails for one entry, it is marked as FAILED, counts update, and processing continues for remaining recipients.
- **Single Code-Defined Template**: Defined in `app/generator.py` with explicit layout constants, double decorative borders, and dynamic text font-size auto-shrinking to handle long recipient or course names without text clipping.

## Known Limitations and Future Improvements

- **In-Process Background Processing**: If the web server process restarts while a job is running, background tasks are interrupted. A persistent task queue like Celery or ARQ would fix this.
- **Single Process Scaling**: Currently bounded by single-server disk and CPU resources. Storing PDFs in cloud storage (such as AWS S3) would enable multi-worker scaling.
- **No Authentication**: API endpoints are unauthenticated. OAuth2 / JWT authentication should be added before production deployment.
- **Retry Endpoint**: Failed certificates currently require re-submitting a new job. A retry endpoint (`POST /api/v1/jobs/{job_id}/retry`) could re-process failed rows.
- **Direct Email Delivery**: Certificates are retrieved via download links. Adding SMTP integration would allow automatic email delivery to recipients upon completion.

## Project Structure

```
.
├── app/
│   ├── __init__.py         # Package initialization
│   ├── config.py           # Configuration values (DATABASE_URL, OUTPUT_DIR, limits)
│   ├── database.py         # SQLAlchemy engine, session maker, and DB dependency
│   ├── generator.py        # ReportLab PDF certificate template drawing logic
│   ├── main.py             # FastAPI application initialization and route mounting
│   ├── models.py           # SQLAlchemy 2.0 models for Job and Certificate
│   ├── processor.py        # Background task processing loop with error isolation
│   ├── routes.py           # API route definitions and endpoint handlers
│   └── schemas.py          # Pydantic v2 validation and serialization schemas
├── static/
│   └── index.html          # Vanilla HTML/JS frontend web application
├── tests/
│   ├── conftest.py         # Test fixtures for isolated DB and output directory
│   ├── test_failure_handling.py # Tests for generation exception handling
│   ├── test_generation.py  # Tests for ReportLab PDF rendering
│   ├── test_jobs.py        # Tests for JSON and CSV job creation endpoints
│   ├── test_retrieval.py   # Tests for PDF download, ZIP download, and verification
│   ├── test_status.py      # Tests for job status and progress polling
│   └── test_validation.py  # Tests for structural and per-recipient validation
├── docs/
│   ├── sample_certificate.pdf # Sample PDF certificate
│   └── screenshot.png      # Screenshot of the web dashboard
├── .env.example            # Sample environment variables configuration
├── .gitignore              # Ignored files configuration
├── pytest.ini              # Pytest configuration
├── README.md               # Project documentation
└── requirements.txt        # Pinned Python package dependencies
