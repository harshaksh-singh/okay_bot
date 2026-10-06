from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from app.harban.enums import ClientStage, OpportunityType, OutreachChannel


class ClientCompany(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    canonical_name: str
    display_name: str
    website: HttpUrl | None = None
    industry: str | None = None
    headquarters: str | None = None
    size_category: str | None = None
    funding_signals: list[str] = Field(default_factory=list)
    technology_signals: list[str] = Field(default_factory=list)
    ai_usage_signals: list[str] = Field(default_factory=list)
    hiring_signals: list[str] = Field(default_factory=list)
    discovery_source: str
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    notes: str | None = None


class ClientContact(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    full_name: str
    role: str | None = None
    company_canonical: str
    linkedin_url: HttpUrl | None = None
    email: EmailStr | None = None
    email_verified: bool = False
    is_public_contact: bool = False
    discovery_source: str
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    notes: str | None = None


class ClientLead(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    lead_id: str
    company_canonical: str
    contact_full_name: str | None = None
    stage: ClientStage = ClientStage.DISCOVERED
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    ai_relevance_reasons: list[str] = Field(default_factory=list)
    buying_signal_reasons: list[str] = Field(default_factory=list)
    opportunity_type: OpportunityType = OpportunityType.CLIENT
    linked_job_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    stage_history: list[tuple[ClientStage, datetime, str | None]] = Field(default_factory=list)
    next_action_at: date | None = None


class ClientInteraction(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    lead_id: str
    channel: OutreachChannel
    direction: str = "outbound"
    subject: str | None = None
    body: str
    sent_at: datetime | None = None
    response_at: datetime | None = None
    response_body: str | None = None
    personalized_signals: list[str] = Field(default_factory=list)
    draft_only: bool = True


class ClientProposal(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    lead_id: str
    scope_summary: str
    deliverables: list[str] = Field(default_factory=list)
    harban_services_used: list[str] = Field(default_factory=list)
    unverified_claims: list[str] = Field(default_factory=list)
    estimate_text: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClientOpportunity(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    opportunity_id: str
    source_job_id: str | None = None
    company_canonical: str
    description: str
    classification: OpportunityType
    personal_employment_score: float = 0.0
    harban_client_score: float = 0.0
    rationale: list[str] = Field(default_factory=list)


class ClientFollowup(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    lead_id: str
    due_at: date
    kind: str = "day-5"
    status: str = "pending"
    message_draft: str | None = None
