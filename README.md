# Bulk Certificate Generator

![Web Dashboard](docs/screenshot.png)

A backend API and web dashboard for generating bulk PDF certificates from course and recipient data.
Built with Python, FastAPI, SQLAlchemy 2.0, and ReportLab.

## Features

- Accepts a bulk list of recipients and generates PDF certificates in the background.
- Validates each recipient individually — valid entries succeed even if others fail.
- Each certificate is generated in its own try/except so one error never stops the rest.
- Single predefined landscape A4 template drawn in code with ReportLab.
- Live progress tracking via polling endpoint.
- Download certificates individually (PDF), in bulk (ZIP), or verify by unique code.
- Static single-page dashboard for manual entry and CSV upload.

## Tech Stack

- Python 3.10+
- FastAPI
- Uvicorn
- SQLAlchemy 2.0
- Pydantic v2
- ReportLab
- Pytest + HTTPX

## Setup

1. Clone and enter the repository:
   ```bash
   git clone https://github.com/NagarjunDP/aereointernshipassignment.git
   cd aereointernshipassignment
   ```

2. Create and activate a virtual environment:
   - macOS / Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```cmd
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Run the Application

```bash
uvicorn app.main:app --reload
```

- Web dashboard: http://127.0.0.1:8000/
- Swagger API docs: http://127.0.0.1:8000/docs

## Run Tests

```bash
pytest
```

## API Overview

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/jobs` | Submit a bulk job (JSON) |
| POST | `/api/v1/jobs/upload` | Submit a bulk job (CSV upload) |
| GET | `/api/v1/jobs/{job_id}` | Get job progress, counts, and failure reasons |
| GET | `/api/v1/jobs/{job_id}/certificates` | List all certificates in a job |
| GET | `/api/v1/certificates/{certificate_id}` | Download a single PDF |
| GET | `/api/v1/jobs/{job_id}/download` | Download all successful PDFs as a ZIP |
| GET | `/api/v1/verify/{code}` | Verify a certificate code |

## Validation Rules

Each recipient is validated individually before generation starts. Invalid recipients are saved with status `FAILED` and a message; they do not block valid ones.

| Rule | Error message |
| --- | --- |
| Name is blank or whitespace-only | `Recipient name cannot be empty` |
| Name longer than 255 characters | `Recipient name exceeds 255 characters` |
| Email does not match `user@domain.tld` format | `Invalid email address format` |
| Same email appears twice in the same job (case-insensitive) | `Duplicate email in this job` |
| More than 1000 recipients per request (configurable via `MAX_RECIPIENTS_PER_JOB` in `config.py`) | Returns 422 with `Recipient count exceeds maximum allowed limit of 1000` |

Structural problems — empty recipient list, missing `course_name` — return 422 and reject the entire request.

## CSV Format

The CSV upload endpoint expects a file with `name` and `email` columns:

```csv
name,email
Alice Smith,alice@example.com
Bob Jones,bob@example.com
```

Column names are matched case-insensitively and trimmed. `recipient_name` and `recipient_email` are also accepted.

## Submit a Generation Request

### JSON

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

### CSV Upload

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

### List Certificates in a Job

```bash
curl http://127.0.0.1:8000/api/v1/jobs/{job_id}/certificates
```

Response (truncated):
```json
[
  {
    "id": "0bc20e98-3979-4fc4-830c-ba23a260d324",
    "name": "Student 1",
    "email": "student1@example.com",
    "status": "SUCCESS",
    "error": null,
    "code": "CERT-A0E9F6"
  },
  {
    "id": "1146afd0-c949-45c5-81e3-91b9a8c13dab",
    "name": "Student 2",
    "email": "student2@example.com",
    "status": "SUCCESS",
    "error": null,
    "code": "CERT-556A09"
  }
]
```

### Download a Single PDF

```bash
curl -O -J http://127.0.0.1:8000/api/v1/certificates/{certificate_id}
```

### Download All as ZIP

```bash
curl -o certificates.zip http://127.0.0.1:8000/api/v1/jobs/{job_id}/download
```

## Verify a Certificate

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

- **Background processing with FastAPI BackgroundTasks, not Celery**: BackgroundTasks runs in-process with no external dependencies (no Redis, no worker processes). This keeps the project simple to run locally. I would switch to Celery or ARQ with Redis if the application needed persistent task queues, distributed workers, or guaranteed completion across server restarts.

- **Per-recipient validation instead of rejecting the whole request**: When someone submits 500 recipients and one has a typo in the email, rejecting all 500 is a poor experience. Each recipient is validated independently so valid ones proceed. Only structural problems (empty list, missing course name) reject the entire request with 422.

- **PDFs on disk, path in the database**: Storing binary files in a relational database bloats storage and slows queries. PDFs are saved to `./generated/<job_id>/<certificate_id>.pdf` and the database stores the absolute file path. File names come from server-generated UUIDs, never from user input.

- **SQLite by default, PostgreSQL by changing one variable**: SQLite needs zero setup for development and testing. Since all database access goes through SQLAlchemy ORM, switching to PostgreSQL requires only setting `DATABASE_URL`:
  ```bash
  export DATABASE_URL="postgresql://user:pass@localhost:5432/certs"
  ```

- **One commit per certificate for live progress**: The background processor commits after each certificate so clients polling the status endpoint see counts update in real time instead of waiting for the entire batch.

- **Failure isolation**: Each certificate is generated inside its own `try/except`. If ReportLab fails for one recipient, that certificate is marked FAILED with the error message, the job's failure counter increments, and the loop continues. If the entire processing function crashes unexpectedly, a top-level `except` marks the job as FAILED so it does not stay stuck in PROCESSING.

- **Single code-defined template**: The certificate layout is defined once in `generator.py` with explicit constants for margins, colours, fonts, and y-positions. Long names auto-shrink to fit without clipping.

- **Duplicate email detection**: Emails are lowercased and stripped before comparison. The first occurrence in a job is accepted; later duplicates are marked FAILED with a clear message.

## Known Limitations and Future Improvements

- **Jobs lost on restart**: Background tasks run in the server process. If it restarts mid-job, those tasks are lost. A persistent task queue (Celery, ARQ) would fix this.
- **Single process**: Processing is single-threaded. For large batches, a worker pool or distributed task queue would help.
- **No authentication**: All endpoints are open. JWT or OAuth2 should be added before production use.
- **No retry endpoint**: Failed certificates require re-submitting the whole job. A `POST /api/v1/jobs/{job_id}/retry` endpoint could re-process only the failed rows.
- **No email delivery**: Certificates are downloaded manually. SMTP integration could deliver them directly to recipients.

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── config.py           - DATABASE_URL, OUTPUT_DIR, MAX_RECIPIENTS_PER_JOB
│   ├── database.py         - SQLAlchemy engine, session factory, get_db dependency
│   ├── generator.py        - ReportLab PDF template and drawing logic
│   ├── main.py             - FastAPI app, table creation, static file mount
│   ├── models.py           - Job and Certificate SQLAlchemy models, status enums
│   ├── processor.py        - Background task loop with per-certificate error isolation
│   ├── routes.py           - All API endpoints and recipient validation
│   └── schemas.py          - Pydantic request/response schemas
├── static/
│   └── index.html          - Vanilla HTML/JS dashboard
├── tests/
│   ├── conftest.py         - Isolated temp DB and output dir fixtures
│   ├── test_failure_handling.py
│   ├── test_generation.py
│   ├── test_jobs.py
│   ├── test_retrieval.py
│   ├── test_status.py
│   └── test_validation.py
├── docs/
│   ├── sample_certificate.pdf
│   └── screenshot.png
├── .env.example
├── .gitignore
├── pytest.ini
├── README.md
└── requirements.txt
```
