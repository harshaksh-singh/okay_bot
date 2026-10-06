from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.schemas.enums import (
    ApplicationMethod,
    EmploymentType,
    JobSource,
    PriorityTier,
    RemotePolicy,
    ScamRisk,
    ShiftType,
)


_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^a-z0-9 ]+")


def _normalize_text(s: str) -> str:
    s = (s or "").lower().strip()
    s = _PUNCT_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s)
    return s.strip()


def canonical_job_key(company: str, title: str, location: str, source_job_id: str | None = None) -> str:
    base = "|".join([_normalize_text(company), _normalize_text(title), _normalize_text(location), (source_job_id or "").strip().lower()])
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


class ScoreBreakdown(BaseModel):
    technical_skills: float = 0.0
    experience: float = 0.0
    role_relevance: float = 0.0
    location: float = 0.0
    employment_type: float = 0.0
    schedule: float = 0.0
    company_priority: float = 0.0
    salary: float = 0.0

    def total(self) -> float:
        return (
            self.technical_skills
            + self.experience
            + self.role_relevance
            + self.location
            + self.employment_type
            + self.schedule
            + self.company_priority
            + self.salary
        )

    def as_dict(self) -> dict[str, float]:
        return self.model_dump()


class SalaryRange(BaseModel):
    min_value: float | None = None
    max_value: float | None = None
    currency: str | None = None
    unit: str | None = None
    raw: str | None = None


class JobBase(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="ignore")

    source: JobSource
    source_job_id: str | None = None

    company: str
    company_url: HttpUrl | None = None
    title: str
    location: str = ""
    remote: RemotePolicy = RemotePolicy.UNKNOWN

    employment_type: EmploymentType = EmploymentType.UNKNOWN
    shift: ShiftType = ShiftType.UNKNOWN
    hours_per_week: int | None = Field(default=None, ge=0, le=168)

    salary: SalaryRange = Field(default_factory=SalaryRange)

    description: str = ""
    requirements: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)

    application_url: HttpUrl | None = None
    application_method: ApplicationMethod = ApplicationMethod.UNKNOWN
    application_email: str | None = None

    posted_at: datetime | None = None
    deadline: date | None = None

    seniority: str | None = None

    @field_validator("company", "title")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("field must be non-empty")
        return v.strip()


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    description: str | None = None
    requirements: list[str] | None = None
    preferred_skills: list[str] | None = None
    application_url: HttpUrl | None = None
    deadline: date | None = None


class Job(JobBase):
    job_id: str
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

    match_score: float = Field(default=0.0, ge=0.0, le=100.0)
    priority: PriorityTier = PriorityTier.CONSIDER
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)

    duplicate_group: str | None = None
    is_duplicate: bool = False

    reason_for_match: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)

    scam_risk: ScamRisk = ScamRisk.NONE
    scam_reasons: list[str] = Field(default_factory=list)

    rejected: bool = False
    rejection_reasons: list[str] = Field(default_factory=list)

    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _derive_duplicate_group(self) -> Job:
        if not self.duplicate_group:
            self.duplicate_group = canonical_job_key(
                self.company, self.title, self.location, self.source_job_id
            )
        return self

    @classmethod
    def from_create(cls, create: JobCreate, job_id: str | None = None) -> Job:
        data: dict[str, Any] = create.model_dump()
        jid = job_id or canonical_job_key(
            create.company, create.title, create.location, create.source_job_id
        )
        return cls(job_id=jid, **data)

    def pretty_salary(self) -> str:
        s = self.salary
        if s.raw:
            return s.raw
        if s.min_value is None and s.max_value is None:
            return "Not disclosed"
        if s.min_value is not None and s.max_value is not None:
            return f"{s.currency or ''}{int(s.min_value):,} - {s.currency or ''}{int(s.max_value):,} / {s.unit or 'period'}".strip()
        v = s.min_value if s.min_value is not None else s.max_value
        return f"{s.currency or ''}{int(v):,} / {s.unit or 'period'}".strip()

    def is_remote(self) -> bool:
        return self.remote in {
            RemotePolicy.REMOTE_LOCAL,
            RemotePolicy.REMOTE_COUNTRY,
            RemotePolicy.REMOTE_GLOBAL,
            RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
        }

    def is_flexible(self) -> bool:
        return self.employment_type in {
            EmploymentType.PART_TIME,
            EmploymentType.CONTRACT,
            EmploymentType.FREELANCE,
            EmploymentType.TEMPORARY,
        } or self.shift in {
            ShiftType.EVENING,
            ShiftType.NIGHT,
            ShiftType.WEEKEND,
            ShiftType.FLEXIBLE,
            ShiftType.ASYNC,
        }
