from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum

from app.config import get_settings
from app.schemas import Job
from app.schemas.application import Application
from app.schemas.enums import ApplicationStatus, ScamRisk


class ApplicationTier(str, Enum):
    AUTO_APPLY = "AUTO_APPLY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECT = "REJECT"


@dataclass
class EligibilityResult:
    tier: ApplicationTier
    reasons: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def is_auto_apply(self) -> bool:
        return self.tier == ApplicationTier.AUTO_APPLY


class ApplicationEligibilityChecker:
    def __init__(self, previously_submitted_job_ids: set[str] | None = None) -> None:
        self.previously_submitted = previously_submitted_job_ids or set()

    def evaluate(self, job: Job, application: Application | None = None) -> EligibilityResult:
        s = get_settings()
        reasons: list[str] = []
        blockers: list[str] = []
        review_reasons: list[str] = []

        if job.rejected:
            blockers.append("job already hard-rejected")
        if job.scam_risk == ScamRisk.HIGH:
            blockers.append("scam risk HIGH")
        if job.is_duplicate:
            blockers.append("duplicate of another canonical job")
        if job.job_id in self.previously_submitted:
            blockers.append("already submitted previously")
        if not job.application_url and not job.application_email:
            blockers.append("no application URL or email")
        if job.deadline is not None and job.deadline < date.today():
            blockers.append("job deadline passed")
        if job.posted_at is not None:
            age = (datetime.now(timezone.utc).replace(tzinfo=None) - job.posted_at.replace(tzinfo=None)).days
            if age > 60:
                blockers.append(f"job posted {age} days ago (likely expired)")

        if blockers:
            return EligibilityResult(tier=ApplicationTier.REJECT, reasons=["reject reasons"], blockers=blockers)

        if application and application.pending_user_inputs:
            sensitive = {"expected_salary", "notice_period", "earliest_start", "work_authorization", "hours_per_week"}
            flagged = [p for p in application.pending_user_inputs if p in sensitive]
            if flagged:
                review_reasons.append(
                    f"pending sensitive user inputs route to REVIEW_REQUIRED per brief Section 10: "
                    f"{', '.join(flagged)}"
                )

        match_ok = job.match_score >= s.auto_apply_match_threshold
        quality_score = 100 if job.scam_risk == ScamRisk.NONE else (60 if job.scam_risk == ScamRisk.LOW else (30 if job.scam_risk == ScamRisk.MEDIUM else 0))
        quality_ok = quality_score >= s.auto_apply_quality_threshold

        if match_ok and quality_ok and not review_reasons:
            reasons.append(f"match {job.match_score:.1f} >= {s.auto_apply_match_threshold}")
            reasons.append(f"quality {quality_score} >= {s.auto_apply_quality_threshold} (scam_risk={job.scam_risk.value})")
            return EligibilityResult(tier=ApplicationTier.AUTO_APPLY, reasons=reasons)

        if match_ok and quality_ok and review_reasons:
            return EligibilityResult(tier=ApplicationTier.REVIEW_REQUIRED, reasons=review_reasons)

        if job.match_score >= s.review_required_match_floor:
            review_reasons.append(f"match {job.match_score:.1f} in review band")
            if not match_ok:
                review_reasons.append(f"below auto-apply threshold ({s.auto_apply_match_threshold})")
            if not quality_ok:
                review_reasons.append(f"quality {quality_score} < {s.auto_apply_quality_threshold}")
            return EligibilityResult(tier=ApplicationTier.REVIEW_REQUIRED, reasons=review_reasons)

        blockers.append(f"match {job.match_score:.1f} < review floor {s.review_required_match_floor}")
        return EligibilityResult(tier=ApplicationTier.REJECT, blockers=blockers)
