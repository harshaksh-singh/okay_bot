from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from app.config import get_settings
from app.harban.enums import OutreachChannel
from app.harban.schema import ClientCompany, ClientContact, ClientInteraction, ClientLead
from app.harban.services import HARBAN_SERVICES, HarbanService, match_services, truthful_service_label
from app.profile import Profile


class OutreachPersonalizationError(ValueError):
    pass


@dataclass
class OutreachDraft:
    channel: OutreachChannel
    subject: str | None
    body: str
    recipient: str | None
    personalized_signals: list[str] = field(default_factory=list)
    services_referenced: list[HarbanService] = field(default_factory=list)
    draft_only: bool = True


_PRIVATE_EMAIL_PATTERN = re.compile(r"^(?:info|contact|hello|hi|hey|team|support|careers)@", re.I)


def _ensure_personalization(signals: list[str]) -> None:
    if not signals:
        raise OutreachPersonalizationError(
            "outreach must include at least one verified company-specific signal (job posting, product, funding, etc.)"
        )


class HarbanOutreachGenerator:
    def __init__(self, profile: Profile) -> None:
        self.profile = profile
        self.settings = get_settings()

    def _service_lines(self, services: list[HarbanService]) -> list[str]:
        return [f"- {truthful_service_label(svc)}: {svc.description}" for svc in services[:3]]

    def generate_email(
        self,
        *,
        company: ClientCompany,
        contact: ClientContact,
        signals: list[str],
        client_need_text: str,
    ) -> OutreachDraft:
        _ensure_personalization(signals)
        services = match_services(client_need_text) or list(HARBAN_SERVICES[:2])
        subject = f"Potential AI/LLM engineering support for {company.display_name}"

        signal_line = "; ".join(signals[:3])
        service_lines = self._service_lines(services)

        body_lines = [
            f"Hi {contact.full_name.split()[0] if contact.full_name else 'there'},",
            "",
            f"I came across {company.display_name} while researching teams working on {signals[0]}.",
            f"I noticed: {signal_line}.",
            "",
            "I run HARBAN AI LABS, focused on AI research, evaluation, and engineering. "
            "Based on what you're building, there may be an opportunity to help with:",
            "",
            *service_lines,
            "",
            "A few notes to be upfront: HARBAN is early-stage, and the services above are offered as "
            "scoped engagements rather than productised offerings. I'd want to understand the problem before "
            "committing to anything specific.",
            "",
            "If this is something you're exploring, I'd be happy to share a short technical approach or "
            "discuss the problem live.",
            "",
            f"Best,",
            f"Harshaksh Singh",
            f"HARBAN AI LABS",
            f"{self.settings.harban_website}",
        ]

        if contact.email and _PRIVATE_EMAIL_PATTERN.match(contact.email):
            recipient = contact.email
        elif contact.email and contact.is_public_contact and contact.email_verified:
            recipient = contact.email
        else:
            recipient = None

        return OutreachDraft(
            channel=OutreachChannel.EMAIL,
            subject=subject,
            body="\n".join(body_lines),
            recipient=recipient,
            personalized_signals=list(signals),
            services_referenced=services,
            draft_only=True,
        )

    def generate_outreach_template(
        self,
        *,
        company: ClientCompany,
        signals: list[str],
        client_need_text: str,
    ) -> str:
        _ensure_personalization(signals)
        services = match_services(client_need_text) or list(HARBAN_SERVICES[:2])
        service_lines = self._service_lines(services)
        signal_line = "; ".join(signals[:3])

        body_lines = [
            "Hi {{recipient_first_name}},",
            "",
            f"I came across {company.display_name} while researching teams working on {signals[0]}.",
            f"I noticed: {signal_line}.",
            "",
            "I run HARBAN AI LABS, focused on AI research, evaluation, and engineering. "
            "Based on what you're building, there may be an opportunity to help with:",
            "",
            *service_lines,
            "",
            "A few notes to be upfront: HARBAN is early-stage, and the services above are offered as "
            "scoped engagements rather than productised offerings. I'd want to understand the problem before "
            "committing to anything specific.",
            "",
            "If this is something you're exploring, I'd be happy to share a short technical approach or "
            "discuss the problem live.",
            "",
            "Best,",
            f"{self.profile.full_name}",
            "HARBAN AI LABS",
            f"{self.settings.harban_website}",
            "",
            "[Template requires a verified public contact before sending — do not fill in {{recipient_first_name}} "
            "without a real name sourced from a public professional profile.]",
        ]
        return "\n".join(body_lines)

    def generate_linkedin_message(
        self,
        *,
        company: ClientCompany,
        contact: ClientContact,
        signals: list[str],
    ) -> OutreachDraft:
        _ensure_personalization(signals)
        first_name = contact.full_name.split()[0] if contact.full_name else "there"
        body = (
            f"Hi {first_name} — I came across {company.display_name} while researching teams "
            f"working on {signals[0]}. I run HARBAN AI LABS, focused on AI research, evaluation, and engineering. "
            f"Your work around {signals[0]} caught my attention. Would be glad to connect and explore whether "
            f"there's any technical area where we could help."
        )
        return OutreachDraft(
            channel=OutreachChannel.LINKEDIN,
            subject=None,
            body=body,
            recipient=str(contact.linkedin_url) if contact.linkedin_url else None,
            personalized_signals=list(signals),
            services_referenced=[],
            draft_only=True,
        )


@dataclass
class OutreachLimitState:
    prospects_today: int = 0
    emails_today: int = 0
    linkedin_today: int = 0
    initial_sent_to: set[str] = field(default_factory=set)
    followup_sent_to: set[str] = field(default_factory=set)


class OutreachLimiter:
    def __init__(self, state: OutreachLimitState | None = None) -> None:
        self.state = state or OutreachLimitState()
        self.settings = get_settings()

    def can_send_email(self, contact_key: str, kind: str = "initial") -> tuple[bool, str | None]:
        if self.state.emails_today >= self.settings.outreach_max_emails_per_day:
            return False, "daily email limit reached"
        if kind == "initial" and contact_key in self.state.initial_sent_to:
            if self.settings.outreach_max_initial_per_contact <= 1:
                return False, "already sent initial email to this contact"
        if kind == "followup" and contact_key in self.state.followup_sent_to:
            if self.settings.outreach_max_followups_per_contact <= 1:
                return False, "already sent follow-up to this contact"
        return True, None

    def can_send_linkedin(self, contact_key: str) -> tuple[bool, str | None]:
        if self.state.linkedin_today >= self.settings.outreach_max_linkedin_per_day:
            return False, "daily LinkedIn message limit reached"
        if contact_key in self.state.initial_sent_to:
            return False, "already sent to this contact"
        return True, None

    def record_email(self, contact_key: str, kind: str = "initial") -> None:
        self.state.emails_today += 1
        if kind == "initial":
            self.state.initial_sent_to.add(contact_key)
        else:
            self.state.followup_sent_to.add(contact_key)

    def record_linkedin(self, contact_key: str) -> None:
        self.state.linkedin_today += 1
        self.state.initial_sent_to.add(contact_key)

    def can_add_prospect(self) -> tuple[bool, str | None]:
        if self.state.prospects_today >= self.settings.outreach_max_prospects_per_day:
            return False, "daily prospect limit reached"
        return True, None

    def record_prospect(self) -> None:
        self.state.prospects_today += 1


def schedule_followup_dates(contacted_on: date | None = None) -> list[tuple[str, date]]:
    s = get_settings()
    base = contacted_on or date.today()
    return [
        ("day-5", base + timedelta(days=s.outreach_followup_day_1)),
        ("day-12", base + timedelta(days=s.outreach_followup_day_2)),
    ]
