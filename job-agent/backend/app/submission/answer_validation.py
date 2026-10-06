from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ClaimViolation:
    surface: str
    issue: str
    severity: str = "block"


@dataclass
class ValidationResult:
    valid: bool
    violations: list[ClaimViolation] = field(default_factory=list)

    def block_reasons(self) -> list[str]:
        return [v.issue for v in self.violations if v.severity == "block"]


_FORBIDDEN_CLAIMS = [
    re.compile(r"\b10\+?\s*years?\b", re.I),
    re.compile(r"\b15\+?\s*years?\b", re.I),
    re.compile(r"\b20\+?\s*years?\b", re.I),
    re.compile(r"\bphd\b", re.I),
    re.compile(r"\bprincipal engineer\b", re.I),
    re.compile(r"\bstaff engineer\b", re.I),
    re.compile(r"\bdistinguished engineer\b", re.I),
    re.compile(r"\bchief\s+(ai|technology|technical|engineering)\s+officer\b", re.I),
    re.compile(r"\bus citizen\b", re.I),
    re.compile(r"\bgreen card\b", re.I),
    re.compile(r"\bh-?1b\s*(sponsor|visa|holder)\b", re.I),
    re.compile(r"\bmba\b", re.I),
    re.compile(r"\bphd\s+in\b", re.I),
]

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
_SALARY_LIKE_RE = re.compile(
    r"(\$\s*\d{1,3}(?:,\d{3})+|\$\s*\d{3,}k|\brs\.?\s*\d+\s*lakh|\b₹\s*\d+)",
    re.IGNORECASE,
)


class AnswerValidationEngine:
    def __init__(self, profile) -> None:
        self.profile = profile
        self._profile_degrees = {e.degree.lower() for e in profile.education}
        self._profile_institutions = {e.institution.lower() for e in profile.education}
        self._profile_companies = {e.company.lower() for e in profile.experiences}
        self._profile_companies.add(profile.full_name.lower())

    def validate(self, application, job=None) -> ValidationResult:
        violations: list[ClaimViolation] = []

        self._scan("cover_letter", application.cover_letter_text or "", violations)

        for ans in application.form_answers:
            if ans.answer:
                self._scan(f"form:{ans.field_name}", str(ans.answer), violations)
            if (
                ans.source_tag == "UNKNOWN"
                and ans.answer
                and not ans.requires_user_input
            ):
                violations.append(
                    ClaimViolation(
                        surface="form_answer_tag",
                        issue=f"answer tagged UNKNOWN but non-empty: {ans.field_name}",
                    )
                )

        return ValidationResult(valid=len(violations) == 0, violations=violations)

    def _scan(self, surface: str, text: str, violations: list[ClaimViolation]) -> None:
        if not text:
            return

        for pattern in _FORBIDDEN_CLAIMS:
            if pattern.search(text):
                violations.append(
                    ClaimViolation(
                        surface=surface,
                        issue=f"forbidden claim pattern: {pattern.pattern}",
                    )
                )

        for m in _YEAR_RE.finditer(text):
            try:
                y = int(m.group(1))
            except ValueError:
                continue
            if y < 1990:
                violations.append(
                    ClaimViolation(surface=surface, issue=f"suspicious old year: {y}")
                )
            elif y > 2035:
                violations.append(
                    ClaimViolation(surface=surface, issue=f"suspicious future year: {y}")
                )

        if _SALARY_LIKE_RE.search(text) and surface not in {"job_description", "resume"}:
            violations.append(
                ClaimViolation(
                    surface=surface,
                    issue="unverified salary/compensation claim in generated text",
                )
            )

        lower = text.lower()
        if "phd" in lower and not any("phd" in d for d in self._profile_degrees):
            violations.append(
                ClaimViolation(
                    surface=surface, issue="claims PhD; not in profile.education"
                )
            )
        if "mba" in lower and not any("mba" in d for d in self._profile_degrees):
            violations.append(
                ClaimViolation(
                    surface=surface, issue="claims MBA; not in profile.education"
                )
            )
        if "stanford" in lower and not any(
            "stanford" in inst for inst in self._profile_institutions
        ):
            violations.append(
                ClaimViolation(
                    surface=surface,
                    issue="references Stanford; not in profile.education",
                )
            )
        if (
            "mit" in lower
            and " mit " in f" {lower} "
            and not any("mit" in inst for inst in self._profile_institutions)
        ):
            violations.append(
                ClaimViolation(
                    surface=surface,
                    issue="references MIT; not in profile.education",
                )
            )
