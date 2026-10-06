from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.profile import Profile
from app.schemas import Job
from app.schemas.enums import EmploymentType, ScamRisk


_UNRELATED_ROLE_TERMS = {
    "nurse", "nursing", "ward boy", "driver", "chauffeur", "chef", "cook",
    "medical representative", "accountant", "field sales", "door-to-door",
    "insurance agent", "real estate agent", "telecaller",
    "security guard", "receptionist", "warehouse", "forklift",
    "electrician", "plumber", "carpenter", "mason",
}

_SENIOR_RE = re.compile(
    r"\b(vp|vice president|director|chief|cto|cio|ceo|head of|principal engineer|staff engineer|"
    r"engineering manager|senior director|group manager|12\+?\s*years|15\+?\s*years|20\+?\s*years)\b",
    re.IGNORECASE,
)
_MIN_YEARS_RE = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)", re.IGNORECASE)


@dataclass
class HardRejectionResult:
    reject: bool
    reasons: list[str] = field(default_factory=list)


def _title_has_unrelated(title: str) -> bool:
    t = title.lower()
    for term in _UNRELATED_ROLE_TERMS:
        if term in t:
            return True
    return False


def _hard_pass_terms_hit(text: str, hard_pass_terms: list[str]) -> list[str]:
    hits = []
    lower = text.lower()
    for term in hard_pass_terms:
        if term.lower() in lower:
            hits.append(term)
    return hits


def apply_hard_rules(
    job: Job,
    profile: Profile,
    *,
    scam_risk: ScamRisk | None = None,
    is_duplicate_of_applied: bool = False,
    senior_experience_floor_months: int = 60,
) -> HardRejectionResult:
    reasons: list[str] = []

    text = " ".join([job.title or "", job.description or "", " ".join(job.requirements or [])])

    if _title_has_unrelated(job.title) and not any(k in job.title.lower() for k in ("ai", "ml", "data", "software", "engineer", "developer", "python")):
        reasons.append(f"unrelated role: title mentions '{job.title}'")

    hard_pass = _hard_pass_terms_hit(f"{job.title} {job.description}", profile.hard_pass_terms)
    for term in hard_pass:
        reasons.append(f"hard-pass term matched: '{term}'")

    if _SENIOR_RE.search(job.title) or _SENIOR_RE.search(job.description):
        if profile.total_experience_months() < senior_experience_floor_months:
            reasons.append("senior/exec role but profile has <5y production experience")

    for m in _MIN_YEARS_RE.finditer(text):
        try:
            min_years = int(m.group(1))
        except ValueError:
            continue
        if min_years >= 10 and profile.total_experience_months() < 60:
            reasons.append(f"requires {min_years}+ years, profile has ~{profile.total_experience_months() // 12}y")
            break

    if scam_risk == ScamRisk.HIGH:
        reasons.append("scam risk: HIGH")

    if is_duplicate_of_applied:
        reasons.append("duplicate of a job already applied to")

    if not job.company.strip():
        reasons.append("no identifiable company")

    if job.employment_type == EmploymentType.INTERNSHIP:
        reasons.append("internship — not applicable")

    if profile.excluded_companies:
        company_lower = job.company.lower()
        for excluded in profile.excluded_companies:
            if excluded.lower() in company_lower:
                reasons.append(f"excluded company: {excluded}")
                break

    return HardRejectionResult(reject=bool(reasons), reasons=reasons)
