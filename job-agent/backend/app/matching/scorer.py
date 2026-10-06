from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import ScoringThresholds, ScoringWeights, get_settings
from app.profile import Profile
from app.schemas import Job, ScoreBreakdown
from app.schemas.enums import EmploymentType, PriorityTier, RemotePolicy, ShiftType


_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.\-]+")


def _extract_tokens(text: str) -> set[str]:
    return {t.lower() for t in _WORD_RE.findall(text or "")}


_SKILL_SYNONYMS: dict[str, set[str]] = {
    "python": {"python", "py", "pythonic"},
    "pytorch": {"pytorch", "torch"},
    "tensorflow": {"tensorflow", "tf"},
    "javascript": {"javascript", "js", "node", "nodejs"},
    "typescript": {"typescript", "ts"},
    "java": {"java", "jvm"},
    "sql": {"sql", "postgres", "postgresql", "mysql", "sqlite", "mssql"},
    "docker": {"docker", "containers", "containerization"},
    "kubernetes": {"kubernetes", "k8s"},
    "aws": {"aws", "amazon-web-services"},
    "gcp": {"gcp", "google-cloud"},
    "azure": {"azure"},
    "llm": {"llm", "llms", "large-language-model", "gpt", "claude", "gemini", "foundation-model"},
    "rag": {"rag", "retrieval-augmented", "retrieval-augmented-generation"},
    "rlhf": {"rlhf", "reinforcement-learning-from-human-feedback"},
    "sft": {"sft", "supervised-fine-tuning", "fine-tuning"},
    "lora": {"lora", "peft"},
    "huggingface": {"huggingface", "transformers", "hf"},
    "pandas": {"pandas"},
    "numpy": {"numpy"},
    "scikit-learn": {"scikit", "sklearn", "scikit-learn"},
    "fastapi": {"fastapi"},
    "flask": {"flask"},
    "django": {"django"},
    "streamlit": {"streamlit"},
    "git": {"git", "github", "gitlab"},
    "ci/cd": {"ci/cd", "cicd", "ci-cd"},
    "rest apis": {"rest", "api", "apis", "rest-apis", "restful"},
    "ml": {"ml", "machine-learning"},
    "dl": {"deep-learning", "dl"},
    "ai": {"ai", "artificial-intelligence"},
    "evaluation": {"evaluation", "eval", "benchmarking", "benchmark"},
    "data science": {"data-science", "data-scientist"},
    "mlops": {"mlops"},
    "prompt engineering": {"prompt-engineering", "prompting"},
    "diffusion models": {"diffusion", "diffusion-models"},
}


def _canonicalize_skill(skill: str) -> str:
    s = skill.strip().lower().replace("_", "-")
    s = re.sub(r"\s+", "-", s)
    for canonical, variants in _SKILL_SYNONYMS.items():
        if s in variants or s == canonical:
            return canonical
    return s


def _skill_hit(canonical: str, tokens: set[str]) -> bool:
    variants = _SKILL_SYNONYMS.get(canonical, {canonical})
    for v in variants:
        if v in tokens:
            return True
        if v.replace("-", " ") in " ".join(tokens):
            return True
    return False


_SENIORITY_RE = re.compile(
    r"\b(principal|staff|director|vp|vice president|chief|head of|lead|sr\.?|senior|"
    r"10\+?\s*years|8\+?\s*years|7\+?\s*years|6\+?\s*years)\b",
    re.IGNORECASE,
)
_JUNIOR_RE = re.compile(
    r"\b(junior|jr\.?|intern|internship|fresher|0-1 years|0-2 years|entry\s*-?\s*level|graduate)\b",
    re.IGNORECASE,
)
_MIN_YEARS_RE = re.compile(r"(\d+)\+?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)", re.IGNORECASE)


_GURGAON_TERMS = {
    "gurugram", "gurgaon", "cyber hub", "cyber city", "dlf cyber city",
    "udyog vihar", "golf course road", "sohna road",
}
_NOIDA_TERMS = {"noida", "greater noida", "sector 62", "sector 63", "sector 125", "sector 132", "sector 135", "sector 142"}
_NCR_TERMS = {"delhi ncr", "ncr", "delhi", "faridabad", "ghaziabad"}
_INDIA_TERMS = {"india", "bengaluru", "bangalore", "hyderabad", "pune", "chennai", "mumbai", "kolkata"}
_REMOTE_TERMS = {"remote", "anywhere", "work from home", "wfh"}


@dataclass
class ScoreResult:
    breakdown: ScoreBreakdown
    reasons: list[str]
    missing: list[str]
    total: float


def apply_scoring_tier(score: float, thresholds: ScoringThresholds | None = None) -> PriorityTier:
    t = thresholds or ScoringThresholds()
    if score >= t.apply_immediately:
        return PriorityTier.APPLY_IMMEDIATELY
    if score >= t.high_priority:
        return PriorityTier.HIGH_PRIORITY
    if score >= t.apply:
        return PriorityTier.APPLY
    if score >= t.consider:
        return PriorityTier.CONSIDER
    if score >= t.low_priority:
        return PriorityTier.LOW_PRIORITY
    return PriorityTier.REJECT


class MatchingEngine:
    def __init__(self, weights: ScoringWeights | None = None, thresholds: ScoringThresholds | None = None) -> None:
        settings = get_settings()
        self.weights = weights or settings.scoring_weights
        self.thresholds = thresholds or settings.scoring_thresholds

    def score(self, job: Job, profile: Profile) -> tuple[ScoreBreakdown, list[str], list[str]]:
        reasons: list[str] = []
        missing: list[str] = []

        job_text = " ".join([
            job.title or "",
            job.description or "",
            " ".join(job.requirements or []),
            " ".join(job.preferred_skills or []),
            " ".join(job.responsibilities or []),
        ])
        job_tokens = _extract_tokens(job_text)

        profile_skills_canonical = {_canonicalize_skill(s) for s in profile.all_skills}

        skills_score, skills_reasons, skills_missing = self._score_skills(job, job_tokens, profile_skills_canonical)
        role_score, role_reasons = self._score_role(job, profile)
        exp_score, exp_reasons, exp_missing = self._score_experience(job, profile)
        loc_score, loc_reasons = self._score_location(job, profile)
        emp_score, emp_reasons = self._score_employment(job, profile)
        shift_score, shift_reasons = self._score_schedule(job, profile)
        company_score, company_reasons = self._score_company(job, profile)
        salary_score, salary_reasons = self._score_salary(job, profile)

        nw = self.weights.normalized()
        breakdown = ScoreBreakdown(
            technical_skills=skills_score * nw["technical_skills"] * 100,
            experience=exp_score * nw["experience"] * 100,
            role_relevance=role_score * nw["role_relevance"] * 100,
            location=loc_score * nw["location"] * 100,
            employment_type=emp_score * nw["employment_type"] * 100,
            schedule=shift_score * nw["schedule"] * 100,
            company_priority=company_score * nw["company_priority"] * 100,
            salary=salary_score * nw["salary"] * 100,
        )

        if role_score < 0.3:
            bias = 0.5 + role_score
            for field_name in ScoreBreakdown.model_fields:
                setattr(breakdown, field_name, round(getattr(breakdown, field_name) * bias, 4))

        reasons.extend(skills_reasons)
        reasons.extend(role_reasons)
        reasons.extend(exp_reasons)
        reasons.extend(loc_reasons)
        reasons.extend(emp_reasons)
        reasons.extend(shift_reasons)
        reasons.extend(company_reasons)
        reasons.extend(salary_reasons)

        missing.extend(skills_missing)
        missing.extend(exp_missing)

        return breakdown, reasons, missing

    def score_total(self, job: Job, profile: Profile) -> ScoreResult:
        breakdown, reasons, missing = self.score(job, profile)
        total = round(breakdown.total(), 2)
        return ScoreResult(breakdown=breakdown, reasons=reasons, missing=missing, total=total)

    def _score_skills(
        self, job: Job, job_tokens: set[str], profile_skills_canonical: set[str]
    ) -> tuple[float, list[str], list[str]]:
        reasons: list[str] = []
        missing: list[str] = []

        required_canonical = {_canonicalize_skill(s) for s in job.requirements} if job.requirements else set()
        preferred_canonical = {_canonicalize_skill(s) for s in job.preferred_skills} if job.preferred_skills else set()

        in_text_canonical: set[str] = set()
        for canonical in _SKILL_SYNONYMS:
            if _skill_hit(canonical, job_tokens):
                in_text_canonical.add(canonical)

        all_job_skills = required_canonical | preferred_canonical | in_text_canonical
        if not all_job_skills:
            return 0.2, [], []

        hits = profile_skills_canonical & all_job_skills
        req_hits = profile_skills_canonical & required_canonical if required_canonical else hits
        req_misses = required_canonical - profile_skills_canonical if required_canonical else set()

        if required_canonical:
            score = len(req_hits) / max(1, len(required_canonical))
            bonus = min(0.15, 0.05 * len(hits - req_hits))
            score = min(1.0, score + bonus)
        else:
            score = len(hits) / max(1, len(all_job_skills))

        for s in sorted(hits)[:6]:
            reasons.append(f"✓ skill match: {s}")
        for s in sorted(req_misses):
            missing.append(f"required skill not in profile: {s}")

        return score, reasons, missing

    def _score_role(self, job: Job, profile: Profile) -> tuple[float, list[str]]:
        title_lower = (job.title or "").lower()
        tier1 = {r.lower() for r in profile.tier1_target_roles}
        tier2 = {r.lower() for r in profile.tier2_target_roles}
        tier3 = {r.lower() for r in profile.tier3_target_roles}

        def _contains_any(terms: set[str]) -> bool:
            for t in terms:
                core = t.replace("-", " ")
                if core in title_lower:
                    return True
            return False

        if _contains_any(tier1):
            return 1.0, ["✓ role is Tier-1 target (AI/ML/LLM)"]
        if _contains_any(tier2):
            return 0.75, ["✓ role is Tier-2 target (SWE/Backend/Data)"]
        if _contains_any(tier3):
            return 0.55, ["✓ role is Tier-3 target (AI eval/training)"]

        if "ai" in title_lower or "ml" in title_lower or "llm" in title_lower or "machine learning" in title_lower:
            return 0.6, ["~ role contains AI/ML keyword"]
        if "software" in title_lower or "engineer" in title_lower or "developer" in title_lower:
            return 0.45, ["~ generic engineering role"]

        return 0.1, ["⚠ role not in target tiers"]

    def _score_experience(self, job: Job, profile: Profile) -> tuple[float, list[str], list[str]]:
        reasons: list[str] = []
        missing: list[str] = []

        text = f"{job.title}\n{job.description}\n{' '.join(job.requirements)}"
        total_months = profile.total_experience_months()

        if _JUNIOR_RE.search(text):
            return 0.95, ["✓ role is junior/entry — strong fit for current experience"], []

        if _SENIORITY_RE.search(text):
            if total_months < 60:
                missing.append("⚠ role is senior/staff/lead but profile has <5y production experience")
                return 0.2, [], missing

        min_years = None
        for m in _MIN_YEARS_RE.finditer(text):
            try:
                y = int(m.group(1))
                if min_years is None or y < min_years:
                    min_years = y
            except ValueError:
                continue
        if min_years is not None:
            have_years = total_months / 12
            if have_years + 0.5 >= min_years:
                reasons.append(f"✓ experience requirement ({min_years}+ yrs) satisfied (~{have_years:.1f} yrs)")
                return 0.9, reasons, missing
            gap = min_years - have_years
            if gap <= 1:
                reasons.append(f"~ experience close to requirement ({have_years:.1f}/{min_years} yrs)")
                return 0.65, reasons, missing
            missing.append(f"experience gap: role asks {min_years}+ yrs, profile has ~{have_years:.1f}")
            return 0.3, [], missing

        return 0.7, ["~ no explicit experience requirement found"], []

    def _score_location(self, job: Job, profile: Profile) -> tuple[float, list[str]]:
        loc = (job.location or "").lower()
        reasons: list[str] = []

        if job.remote in {RemotePolicy.REMOTE_LOCAL, RemotePolicy.REMOTE_COUNTRY}:
            reasons.append("✓ remote (India-eligible)")
            return 1.0, reasons
        if job.remote == RemotePolicy.REMOTE_GLOBAL:
            reasons.append("✓ remote global (verified India-eligible)")
            return 0.95, reasons
        if job.remote == RemotePolicy.REMOTE_GLOBAL_UNVERIFIED:
            reasons.append("~ remote global (India eligibility unverified)")
            return 0.6, reasons

        if any(term in loc for term in _GURGAON_TERMS):
            reasons.append("✓ Gurugram / Cyber Hub area — primary location")
            return 1.0, reasons
        if any(term in loc for term in _NOIDA_TERMS):
            reasons.append("✓ Noida / Greater Noida — secondary location")
            return 0.85, reasons
        if any(term in loc for term in _NCR_TERMS):
            reasons.append("✓ Delhi NCR — secondary location")
            return 0.75, reasons
        if any(term in loc for term in _REMOTE_TERMS):
            reasons.append("~ location mentions remote; policy unclear")
            return 0.7, reasons
        if any(term in loc for term in _INDIA_TERMS):
            reasons.append("~ India (other city) — relocation needed")
            return 0.3, reasons
        if job.remote == RemotePolicy.ONSITE and loc:
            reasons.append("⚠ onsite outside NCR")
            return 0.1, reasons

        return 0.4, ["~ location unclear"]

    def _score_employment(self, job: Job, profile: Profile) -> tuple[float, list[str]]:
        a = profile.availability
        reasons: list[str] = []

        et = job.employment_type
        if et == EmploymentType.PART_TIME and a.open_to_part_time:
            reasons.append("✓ part-time — matches primary availability preference")
            return 1.0, reasons
        if et == EmploymentType.CONTRACT and a.open_to_contract:
            reasons.append("✓ contract — matches availability preference")
            return 0.9, reasons
        if et == EmploymentType.FREELANCE and a.open_to_freelance:
            reasons.append("✓ freelance — matches availability preference")
            return 0.9, reasons
        if et == EmploymentType.TEMPORARY:
            reasons.append("~ temporary — flexible")
            return 0.7, reasons
        if et == EmploymentType.FULL_TIME:
            reasons.append("~ full-time — compatible, lower preference weight")
            return 0.5, reasons
        if et == EmploymentType.INTERNSHIP:
            reasons.append("⚠ internship — generally not applicable")
            return 0.1, reasons
        return 0.5, ["~ employment type unknown"]

    def _score_schedule(self, job: Job, profile: Profile) -> tuple[float, list[str]]:
        reasons: list[str] = []
        shift = job.shift
        if shift == ShiftType.EVENING:
            reasons.append("✓ evening shift — aligns with availability")
            return 1.0, reasons
        if shift == ShiftType.NIGHT:
            reasons.append("✓ night shift — aligns with availability")
            return 1.0, reasons
        if shift == ShiftType.WEEKEND:
            reasons.append("✓ weekend — aligns with availability")
            return 0.95, reasons
        if shift in {ShiftType.FLEXIBLE, ShiftType.ASYNC}:
            reasons.append("✓ flexible / async schedule")
            return 1.0, reasons
        if shift == ShiftType.DAY:
            reasons.append("~ day shift (less preferred given current employment)")
            return 0.4, reasons
        return 0.6, ["~ schedule unknown"]

    def _score_company(self, job: Job, profile: Profile) -> tuple[float, list[str]]:
        canon = job.company.strip().lower()
        for pc in profile.priority_companies:
            if canon == pc.lower() or pc.lower() in canon or canon in pc.lower():
                return 1.0, [f"✓ priority company: {pc}"]
        return 0.5, []

    def _score_salary(self, job: Job, profile: Profile) -> tuple[float, list[str]]:
        s = job.salary
        reasons: list[str] = []

        if s.min_value is None and s.max_value is None and not s.raw:
            return 0.6, ["~ salary not disclosed"]

        value = s.max_value or s.min_value
        unit = (s.unit or "").lower()
        currency = (s.currency or "").upper()

        if value is None:
            return 0.6, ["~ salary partial"]

        if currency == "INR" or "₹" in (s.raw or "") or "inr" in unit:
            if "month" in unit:
                if value >= 50000:
                    return 0.9, ["✓ competitive monthly INR salary"]
                if value >= 30000:
                    return 0.7, ["~ moderate monthly INR salary"]
                return 0.3, ["⚠ low monthly INR salary"]
            if "year" in unit or "annum" in unit:
                if value >= 1200000:
                    return 0.9, ["✓ competitive annual INR salary"]
                if value >= 800000:
                    return 0.7, ["~ moderate annual INR salary"]
                return 0.3, ["⚠ low annual INR salary"]
        if currency == "USD" or "$" in (s.raw or ""):
            if "hour" in unit:
                if value >= 25:
                    return 0.95, ["✓ strong USD hourly rate"]
                if value >= 15:
                    return 0.75, ["~ reasonable USD hourly rate"]
                return 0.4, ["⚠ low USD hourly rate"]

        return 0.65, [f"~ salary present ({job.pretty_salary()})"]
