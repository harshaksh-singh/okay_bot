from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from app.schemas import Job
from app.schemas.application import Application
from app.submission.hard_stops import HardStopReason


class SubmissionDecision(str, Enum):
    AUTO_SUBMIT = "AUTO_SUBMIT"
    REQUIRES_USER_DATA = "REQUIRES_USER_DATA"
    SECURITY_BLOCKED = "SECURITY_BLOCKED"
    LEGAL_BLOCKED = "LEGAL_BLOCKED"
    FAILED = "FAILED"


class FieldState(str, Enum):
    FIELD_READY = "FIELD_READY"
    FIELD_AUTO_FILLED = "FIELD_AUTO_FILLED"
    FIELD_GENERATED = "FIELD_GENERATED"
    FIELD_NEEDS_USER_DATA = "FIELD_NEEDS_USER_DATA"
    FIELD_SECURITY_BLOCKED = "FIELD_SECURITY_BLOCKED"
    FIELD_LEGAL_BLOCKED = "FIELD_LEGAL_BLOCKED"


@dataclass
class FieldClassification:
    name: str
    state: FieldState
    category: str = ""
    reason: str = ""
    value_filled: str | None = None


@dataclass
class DecisionResult:
    decision: SubmissionDecision
    reasons: list[str] = field(default_factory=list)
    field_states: list[FieldClassification] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def is_submittable(self) -> bool:
        return self.decision == SubmissionDecision.AUTO_SUBMIT


_LEGAL_HARD_STOPS: set[HardStopReason] = {
    HardStopReason.UNKNOWN_LEGAL_QUESTION,
}


_SECURITY_HARD_STOPS: set[HardStopReason] = {
    HardStopReason.CAPTCHA,
    HardStopReason.MFA,
    HardStopReason.OTP,
    HardStopReason.IDENTITY_VERIFICATION,
    HardStopReason.PAYMENT,
    HardStopReason.PLATFORM_BLOCKED,
}


_USER_DATA_HARD_STOPS: set[HardStopReason] = {
    HardStopReason.UNKNOWN_SENSITIVE_QUESTION,
    HardStopReason.UNVERIFIABLE_FIELD,
}


_LEGAL_PAGE_PATTERNS = [
    re.compile(r"\barbitration\s+agreement\b", re.I),
    re.compile(r"waive\s+(my|our|their)?\s*(respective\s+)?rights?\s+to\s+(trial\s+by\s+)?jury", re.I),
    re.compile(r"\bbinding\s+(contract|declaration|agreement)\b", re.I),
    re.compile(r"\bI\s+(certify|affirm|declare)\s+under\s+penalty\s+of\s+perjury\b", re.I),
    re.compile(r"\bclass\s+action\s+waiver\b", re.I),
    re.compile(r"\bagreement\s+to\s+arbitrate\b", re.I),
]


_SENSITIVE_FIELD_PATTERNS = [
    re.compile(r"\b(gender|sex|race|ethnicity|veteran|disability|religion)\b", re.I),
    re.compile(r"\beeo[-_\s]+(self[-\s]*identification|classification)?", re.I),
    re.compile(r"\b(hispanic|latino)\b", re.I),
    re.compile(r"\bprotected\s+(class|category|veteran)\b", re.I),
]


class SubmissionDecisionEngine:
    def __init__(self, *, allow_sensitive_from_config: bool = True) -> None:
        self._allow_sensitive_from_config = allow_sensitive_from_config

    def evaluate(
        self,
        *,
        application: Application,
        job: Job,
        page_text: str = "",
        detected_hard_stops: list[tuple[HardStopReason, str]] | None = None,
        filled_fields: list[str] | None = None,
        detected_field_labels: list[str] | None = None,
        has_captcha_widget: bool = False,
    ) -> DecisionResult:
        reasons: list[str] = []
        blockers: list[str] = []
        states: list[FieldClassification] = []

        if has_captcha_widget:
            blockers.append("CAPTCHA / reCAPTCHA widget detected on page")
            states.append(FieldClassification(
                name="_page_captcha",
                state=FieldState.FIELD_SECURITY_BLOCKED,
                category="SECURITY",
                reason="CAPTCHA widget present; architecture must never bypass",
            ))

        stops = detected_hard_stops or []
        for reason, msg in stops:
            if reason in _SECURITY_HARD_STOPS:
                blockers.append(f"security: {reason.value} - {msg}")
                states.append(FieldClassification(
                    name=f"_stop_{reason.value}",
                    state=FieldState.FIELD_SECURITY_BLOCKED,
                    category="SECURITY",
                    reason=msg,
                ))
            elif reason in _LEGAL_HARD_STOPS:
                blockers.append(f"legal: {reason.value} - {msg}")
                states.append(FieldClassification(
                    name=f"_stop_{reason.value}",
                    state=FieldState.FIELD_LEGAL_BLOCKED,
                    category="LEGAL",
                    reason=msg,
                ))
            elif reason in _USER_DATA_HARD_STOPS:
                blockers.append(f"user_data: {reason.value} - {msg}")
                states.append(FieldClassification(
                    name=f"_stop_{reason.value}",
                    state=FieldState.FIELD_NEEDS_USER_DATA,
                    category="USER_DATA",
                    reason=msg,
                ))

        for pat in _LEGAL_PAGE_PATTERNS:
            m = pat.search(page_text or "")
            if m:
                blockers.append(f"legal: page contains legal-agreement text: {m.group(0)!r}")
                states.append(FieldClassification(
                    name="_page_legal_agreement",
                    state=FieldState.FIELD_LEGAL_BLOCKED,
                    category="LEGAL",
                    reason=f"Legal declaration/agreement pattern on page: {m.group(0)!r}. "
                           f"Cannot be pre-consented via config per transaction.",
                ))
                break

        labels = detected_field_labels or []
        pending_sensitive_in_form: list[str] = []
        for label in labels:
            for pat in _SENSITIVE_FIELD_PATTERNS:
                if pat.search(label):
                    pending_sensitive_in_form.append(label)
                    break
        for label in pending_sensitive_in_form:
            states.append(FieldClassification(
                name=label,
                state=FieldState.FIELD_NEEDS_USER_DATA,
                category="SENSITIVE_PERSONAL",
                reason="EEO / sensitive personal field; requires explicit user configuration per field, "
                       "not implicit auto-fill",
            ))
            blockers.append(f"user_data: sensitive field in form: {label!r}")

        pending = list(application.pending_user_inputs or [])
        for p in pending:
            lower = p.lower()
            if lower in {"linkedin", "github", "portfolio"}:
                continue
            if lower in {"notice_period", "earliest_start", "expected_salary"}:
                states.append(FieldClassification(
                    name=p,
                    state=FieldState.FIELD_NEEDS_USER_DATA,
                    category="PROFILE_PREFERENCE",
                    reason=f"Pending user input {p!r} - not in profile; configure USER_* .env override to auto-fill",
                ))
                blockers.append(f"user_data: pending profile preference {p!r}")
            else:
                states.append(FieldClassification(
                    name=p,
                    state=FieldState.FIELD_NEEDS_USER_DATA,
                    category="UNKNOWN",
                    reason=f"Unresolved pending_user_input: {p!r}",
                ))
                blockers.append(f"user_data: unresolved input {p!r}")

        for name in (filled_fields or []):
            states.append(FieldClassification(
                name=name,
                state=FieldState.FIELD_AUTO_FILLED,
                category="PROFILE_FACT",
                reason="Auto-filled from verified profile data",
            ))

        if any(s.state == FieldState.FIELD_SECURITY_BLOCKED for s in states):
            decision = SubmissionDecision.SECURITY_BLOCKED
            reasons.append("At least one field or page element is SECURITY_BLOCKED; "
                          "architecture must never bypass security controls")
        elif any(s.state == FieldState.FIELD_LEGAL_BLOCKED for s in states):
            decision = SubmissionDecision.LEGAL_BLOCKED
            reasons.append("At least one field or page element is LEGAL_BLOCKED; "
                          "legal consent cannot be pre-configured per transaction")
        elif any(s.state == FieldState.FIELD_NEEDS_USER_DATA for s in states):
            decision = SubmissionDecision.REQUIRES_USER_DATA
            reasons.append("At least one field needs verified user data not available in profile/config")
        elif states and all(
            s.state in {FieldState.FIELD_AUTO_FILLED, FieldState.FIELD_GENERATED, FieldState.FIELD_READY}
            for s in states
        ):
            decision = SubmissionDecision.AUTO_SUBMIT
            reasons.append(f"All {len(states)} fields are auto-filled, generated, or ready; "
                          "no legal/security/user-data blockers detected")
        else:
            decision = SubmissionDecision.FAILED
            reasons.append("No fields classified; engine has insufficient input to decide")

        return DecisionResult(
            decision=decision,
            reasons=reasons,
            field_states=states,
            blockers=blockers,
        )
