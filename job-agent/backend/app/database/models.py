from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.engine import Base


def _now() -> datetime:
    return datetime.utcnow()


class CompanyRow(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_name: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    careers_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    homepage: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    headquarters: Mapped[str | None] = mapped_column(String(256), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_priority: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_score: Mapped[int] = mapped_column(Integer, default=0)
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    jobs: Mapped[list["JobRow"]] = relationship(back_populates="company")


class JobRow(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_source_source_job_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    source_job_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    company_name: Mapped[str] = mapped_column(String(256), index=True)

    title: Mapped[str] = mapped_column(String(512), index=True)
    location: Mapped[str] = mapped_column(String(256), default="")
    remote: Mapped[str] = mapped_column(String(64), default="unknown")
    employment_type: Mapped[str] = mapped_column(String(64), default="unknown")
    shift: Mapped[str] = mapped_column(String(64), default="unknown")
    hours_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)

    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    salary_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    salary_raw: Mapped[str | None] = mapped_column(String(256), nullable=True)

    description: Mapped[str] = mapped_column(Text, default="")
    requirements: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    responsibilities: Mapped[list[str]] = mapped_column(JSON, default=list)

    application_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    application_method: Mapped[str] = mapped_column(String(64), default="unknown")
    application_email: Mapped[str | None] = mapped_column(String(256), nullable=True)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)

    match_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    priority: Mapped[str] = mapped_column(String(32), default="consider", index=True)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    duplicate_group: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    reason_for_match: Mapped[list[str]] = mapped_column(JSON, default=list)
    missing_requirements: Mapped[list[str]] = mapped_column(JSON, default=list)

    scam_risk: Mapped[str] = mapped_column(String(16), default="none", index=True)
    scam_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)

    rejected: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    rejection_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)

    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    seniority: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    company: Mapped[CompanyRow | None] = relationship(back_populates="jobs")
    applications: Mapped[list["ApplicationRow"]] = relationship(back_populates="job")


class ApplicationRow(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.job_id"), index=True)

    status: Mapped[str] = mapped_column(String(64), default="DISCOVERED", index=True)
    application_method: Mapped[str] = mapped_column(String(64), default="unknown")

    resume_variant: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resume_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cover_letter_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cover_letter_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    form_answers: Mapped[list[dict]] = mapped_column(JSON, default=list)
    pending_user_inputs: Mapped[list[str]] = mapped_column(JSON, default=list)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submission_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    approved_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    followup_due_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    last_followup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status_history: Mapped[list[dict]] = mapped_column(JSON, default=list)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    job: Mapped[JobRow] = relationship(back_populates="applications")


class ContactRow(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(256))
    email: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    role: Mapped[str | None] = mapped_column(String(256), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class MessageRow(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"), nullable=True, index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(32), default="linkedin")
    direction: Mapped[str] = mapped_column(String(16), default="outbound")
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    response_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class EmailRow(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True, index=True)
    to_address: Mapped[str] = mapped_column(String(256))
    from_address: Mapped[str] = mapped_column(String(256))
    subject: Mapped[str] = mapped_column(String(512))
    body: Mapped[str] = mapped_column(Text)
    attachments: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class FollowupRow(Base):
    __tablename__ = "followups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    due_at: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(32), default="application")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    message_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class InterviewRow(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    round_name: Mapped[str] = mapped_column(String(64), default="screen")
    interviewer: Mapped[str | None] = mapped_column(String(256), nullable=True)
    preparation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class SearchRunRow(Base):
    __tablename__ = "search_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    queries: Mapped[list[str]] = mapped_column(JSON, default=list)
    jobs_discovered: Mapped[int] = mapped_column(Integer, default=0)
    jobs_new: Mapped[int] = mapped_column(Integer, default=0)
    jobs_rejected: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_removed: Mapped[int] = mapped_column(Integer, default=0)
    high_priority_count: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list[dict]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLogRow(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    event: Mapped[str] = mapped_column(String(128), index=True)
    actor: Mapped[str] = mapped_column(String(64), default="system")
    subject_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subject_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ErrorRow(Base):
    __tablename__ = "errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    source: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ClientCompanyRow(Base):
    __tablename__ = "client_companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_name: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(256))
    website: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    headquarters: Mapped[str | None] = mapped_column(String(256), nullable=True)
    size_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    funding_signals: Mapped[list[str]] = mapped_column(JSON, default=list)
    technology_signals: Mapped[list[str]] = mapped_column(JSON, default=list)
    ai_usage_signals: Mapped[list[str]] = mapped_column(JSON, default=list)
    hiring_signals: Mapped[list[str]] = mapped_column(JSON, default=list)
    discovery_source: Mapped[str] = mapped_column(String(64))
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class ClientContactRow(Base):
    __tablename__ = "client_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(256), index=True)
    role: Mapped[str | None] = mapped_column(String(256), nullable=True)
    company_canonical: Mapped[str] = mapped_column(String(256), index=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    discovery_source: Mapped[str] = mapped_column(String(64))
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class ClientLeadRow(Base):
    __tablename__ = "client_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    company_canonical: Mapped[str] = mapped_column(String(256), index=True)
    contact_full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    stage: Mapped[str] = mapped_column(String(32), default="DISCOVERED", index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ai_relevance_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    buying_signal_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    opportunity_type: Mapped[str] = mapped_column(String(16), default="CLIENT")
    linked_job_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    stage_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    next_action_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class ClientInteractionRow(Base):
    __tablename__ = "client_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("client_leads.lead_id"), index=True)
    channel: Mapped[str] = mapped_column(String(32), default="email")
    direction: Mapped[str] = mapped_column(String(16), default="outbound")
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    response_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    personalized_signals: Mapped[list[str]] = mapped_column(JSON, default=list)
    draft_only: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


class ClientProposalRow(Base):
    __tablename__ = "client_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("client_leads.lead_id"), index=True)
    scope_summary: Mapped[str] = mapped_column(Text)
    deliverables: Mapped[list[str]] = mapped_column(JSON, default=list)
    harban_services_used: Mapped[list[str]] = mapped_column(JSON, default=list)
    unverified_claims: Mapped[list[str]] = mapped_column(JSON, default=list)
    estimate_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ClientOpportunityRow(Base):
    __tablename__ = "client_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_job_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    company_canonical: Mapped[str] = mapped_column(String(256), index=True)
    description: Mapped[str] = mapped_column(Text)
    classification: Mapped[str] = mapped_column(String(16), default="NEITHER", index=True)
    personal_employment_score: Mapped[float] = mapped_column(Float, default=0.0)
    harban_client_score: Mapped[float] = mapped_column(Float, default=0.0)
    rationale: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


class ClientFollowupRow(Base):
    __tablename__ = "client_followups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(ForeignKey("client_leads.lead_id"), index=True)
    due_at: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(32), default="day-5")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    message_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class SubmissionEvidenceRow(Base):
    __tablename__ = "submission_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(String(32), index=True)
    job_id: Mapped[str] = mapped_column(String(32), index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmation_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    confirmation_application_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    evidence_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), default="SUBMITTED", index=True)
    hard_stop_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


class SubmissionCheckpointRow(Base):
    __tablename__ = "submission_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(String(32), index=True)
    job_id: Mapped[str] = mapped_column(String(32), index=True)
    stage: Mapped[str] = mapped_column(String(48), index=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    blocker_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    fields_filled: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_fields: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
