from typing import List, Optional
from pydantic import BaseModel, field_validator


class RecipientInput(BaseModel):
    name: str = ""
    email: str = ""


class JobCreate(BaseModel):
    course_name: str
    completion_date: str
    issuer: str
    recipients: List[RecipientInput]

    @field_validator("course_name", "completion_date", "issuer")
    @classmethod
    def validate_non_empty_string(cls, value: str, info) -> str:
        if not value or not value.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return value.strip()

    @field_validator("recipients")
    @classmethod
    def validate_recipients_not_empty(cls, recipients: List[RecipientInput]) -> List[RecipientInput]:
        if not recipients:
            raise ValueError("recipients list cannot be empty")
        return recipients


class JobAcceptedResponse(BaseModel):
    job_id: str
    status: str
    total: int


class RecipientFailure(BaseModel):
    name: str
    email: str
    error: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    total: int
    successful: int
    failed: int
    pending: int
    progress_percent: float
    failures: List[RecipientFailure]


class CertificateResponse(BaseModel):
    id: str
    name: str
    email: str
    status: str
    error: Optional[str] = None
    code: str


class VerifyResponse(BaseModel):
    valid: bool
    recipient_name: Optional[str] = None
    course_name: Optional[str] = None
    completion_date: Optional[str] = None
    issuer: Optional[str] = None
    code: str
