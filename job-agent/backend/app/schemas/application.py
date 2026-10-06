from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import ApplicationMethod, ApplicationStatus


class FormAnswer(BaseModel):
    field_name: str
    question: str
    answer: str | None = None
    source_tag: str = "UNKNOWN"
    requires_user_input: bool = False
    is_sensitive: bool = False


class ApplicationBase(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    job_id: str
    status: ApplicationStatus = ApplicationStatus.DISCOVERED
    application_method: ApplicationMethod = ApplicationMethod.UNKNOWN

    resume_variant: str | None = None
    resume_path: Path | None = None
    cover_letter_path: Path | None = None
    cover_letter_text: str | None = None

    form_answers: list[FormAnswer] = Field(default_factory=list)
    pending_user_inputs: list[str] = Field(default_factory=list)

    submitted_at: datetime | None = None
    submission_evidence: str | None = None

    notes: str | None = None


class ApplicationCreate(ApplicationBase):
    pass


class Application(ApplicationBase):
    application_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    status_history: list[tuple[ApplicationStatus, datetime, str | None]] = Field(default_factory=list)

    followup_due_at: date | None = None
    last_followup_at: datetime | None = None

    approved_by_user: bool = False
    approved_at: datetime | None = None
