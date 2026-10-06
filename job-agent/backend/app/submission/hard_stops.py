from __future__ import annotations

import re
from enum import Enum

from app.schemas import Job
from app.schemas.application import Application


class HardStopReason(str, Enum):
    CAPTCHA = "CAPTCHA"
    MFA = "MFA"
    OTP = "OTP"
    IDENTITY_VERIFICATION = "IDENTITY_VERIFICATION"
    PAYMENT = "PAYMENT"
    PLATFORM_BLOCKED = "PLATFORM_BLOCKED"
    UNKNOWN_LEGAL_QUESTION = "UNKNOWN_LEGAL_QUESTION"
    UNKNOWN_SENSITIVE_QUESTION = "UNKNOWN_SENSITIVE_QUESTION"
    UNVERIFIABLE_FIELD = "UNVERIFIABLE_FIELD"
    UNEXPECTED_WORKFLOW = "UNEXPECTED_WORKFLOW"


_HARD_STOP_PATTERNS: list[tuple[HardStopReason, re.Pattern[str]]] = [
    (HardStopReason.CAPTCHA, re.compile(r"\b(captcha|recaptcha|hcaptcha|solve\s+(this\s+)?puzzle|i'?m not a robot)\b", re.I)),
    (HardStopReason.MFA, re.compile(r"\b(multi[-\s]?factor|mfa|two[-\s]?factor|2fa|authenticator\s+code)\b", re.I)),
    (HardStopReason.OTP, re.compile(r"\b(one[-\s]?time\s+(password|code)|otp|verification\s+code\s+sent)\b", re.I)),
    (HardStopReason.IDENTITY_VERIFICATION, re.compile(r"\b(upload\s+(your\s+)?(government|photo|passport|driver'?s?\s+licen[cs]e|aadhaar|pan\s+card|id)|identity\s+verification|verify\s+your\s+identity)\b", re.I)),
    (HardStopReason.PAYMENT, re.compile(r"\b(application\s+fee|registration\s+fee|processing\s+fee|pay\s+(now|to\s+apply)|credit\s+card\s+required|crypto\s+payment)\b", re.I)),
    (HardStopReason.PLATFORM_BLOCKED, re.compile(r"\b(too\s+many\s+requests|rate[-\s]?limited|temporarily\s+blocked|forbidden|access\s+denied|403\s+forbidden)\b", re.I)),
    (HardStopReason.UNKNOWN_LEGAL_QUESTION, re.compile(r"\b(are\s+you\s+(a\s+)?(us\s+citizen|green\s+card\s+holder|canadian\s+citizen|uk\s+citizen|eu\s+citizen)|security\s+clearance|will\s+you\s+require\s+sponsorship|visa\s+status\s+required|government\s+eligibility)\b", re.I)),
]


_SENSITIVE_FIELD_KEYWORDS = {
    "expected_salary", "notice_period", "earliest_start", "work_authorization", "visa",
    "sponsorship", "security_clearance", "government_eligibility",
}


def detect_hard_stops(
    *,
    page_text: str = "",
    pending_user_inputs: list[str] | None = None,
    application: Application | None = None,
    job: Job | None = None,
) -> list[tuple[HardStopReason, str]]:
    stops: list[tuple[HardStopReason, str]] = []
    text = page_text or ""

    for reason, pattern in _HARD_STOP_PATTERNS:
        if pattern.search(text):
            stops.append((reason, f"page text matches {reason.value} pattern"))

    pending = set(pending_user_inputs or (application.pending_user_inputs if application else []))
    for field in pending:
        if field.lower() in _SENSITIVE_FIELD_KEYWORDS or any(k in field.lower() for k in _SENSITIVE_FIELD_KEYWORDS):
            stops.append((HardStopReason.UNKNOWN_SENSITIVE_QUESTION, f"pending user input requires {field}"))

    if application:
        for ans in application.form_answers:
            if ans.source_tag == "UNKNOWN" and not ans.answer:
                stops.append((HardStopReason.UNVERIFIABLE_FIELD, f"form field {ans.field_name} tagged UNKNOWN"))

    return stops
