from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.applications.eligibility import ApplicationEligibilityChecker, ApplicationTier
from app.config import get_settings
from app.observability import get_logger
from app.submission.submitter import ApprovedSubmitter

log = get_logger("agent.submission")


class SubmissionAgent(BaseAgent):
    name = "submission"

    def run(self, context: AgentContext, previous: list[AgentResult]) -> AgentResult:
        r = self._start()
        s = get_settings()

        applications = []
        blocked_by_truthfulness: set[str] = set()
        for p in previous:
            if p.agent == "application":
                applications = p.metadata.get("applications", [])
            if p.agent == "quality":
                blocked_by_truthfulness = set(p.metadata.get("blocked_application_ids", []))

        matched_jobs = []
        for p in previous:
            if p.agent == "matching":
                matched_jobs = p.jobs
                break
        job_by_id = {j.job_id: j for j in matched_jobs}

        previously_submitted: set[str] = set()
        try:
            from sqlalchemy import select
            from app.database import SessionLocal, init_database
            from app.database.models import SubmissionEvidenceRow
            init_database()
            with SessionLocal() as session:
                rows = session.scalars(select(SubmissionEvidenceRow).where(SubmissionEvidenceRow.outcome.in_(["SUBMITTED_LIVE", "SUBMITTED_CONFIRMED"]))).all()
                previously_submitted = {r.job_id for r in rows}
        except Exception as e:
            log.warning("submission.read_prior_failed", error=str(e))

        submitter = ApprovedSubmitter(previously_submitted_job_ids=previously_submitted)
        checker = ApplicationEligibilityChecker(previously_submitted_job_ids=previously_submitted)

        outcomes: list[dict] = []
        tier_counts: dict[str, int] = {"AUTO_APPLY": 0, "REVIEW_REQUIRED": 0, "REJECT": 0}

        from app.applications.eligibility import ApplicationTier
        from app.submission.submitter import SubmissionOutcome
        from app.submission.throttle import AIMDThrottler
        throttler = getattr(context, "throttler", None) or AIMDThrottler()
        for app in applications:
            job = job_by_id.get(app.job_id)
            if not job:
                continue

            if app.application_id in blocked_by_truthfulness:
                tier = ApplicationTier.REVIEW_REQUIRED
                outcome = SubmissionOutcome(
                    application_id=app.application_id,
                    job_id=app.job_id,
                    outcome="BLOCKED_BY_TRUTHFULNESS_HARD_BLOCK",
                    notes=["QualityAgent flagged this application; truthfulness_hard_block=true; routed to REVIEW_REQUIRED instead of auto-apply"],
                )
                submitter._write_evidence(outcome)
            else:
                tier = checker.evaluate(job, app).tier
                platform = str(getattr(job.source, "value", job.source))
                if not s.dry_run and tier == ApplicationTier.AUTO_APPLY:
                    throttler.wait_before_submit(platform)
                outcome = submitter.submit(job, app)
                if outcome.outcome in {"SUBMITTED_LIVE", "SUBMITTED_CONFIRMED"}:
                    throttler.record_success(platform)
                elif outcome.outcome == "APPLICATION_BLOCKED_USER_ACTION" and (outcome.hard_stop_reason or "").upper() in {"CAPTCHA", "SECURITY_CONTROL_PRESENT", "PLATFORM_BLOCKED"}:
                    throttler.record_block(platform, reason=outcome.hard_stop_reason or "")

            tier_counts[tier.value] += 1
            outcomes.append({
                "application_id": outcome.application_id,
                "job_id": outcome.job_id,
                "tier": tier.value,
                "outcome": outcome.outcome,
                "hard_stop_reason": outcome.hard_stop_reason,
                "evidence_path": outcome.evidence_path,
                "notes": outcome.notes,
            })

        try:
            from app.database import SessionLocal, init_database
            from app.database.models import SubmissionEvidenceRow
            from datetime import datetime, timezone
            init_database()
            with SessionLocal() as session:
                for o in outcomes:
                    session.add(SubmissionEvidenceRow(
                        application_id=o["application_id"],
                        job_id=o["job_id"],
                        submitted_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        confirmation=o["outcome"] in {"SIMULATED_SUBMIT_DRY_RUN", "SUBMITTED_PLACEHOLDER_REQUIRES_BROWSER"},
                        confirmation_text="; ".join(o.get("notes", [])),
                        evidence_path=o.get("evidence_path"),
                        outcome=o["outcome"],
                        hard_stop_reason=o.get("hard_stop_reason"),
                    ))
                session.commit()
        except Exception as e:
            r.errors.append(f"submission.persist_failed: {e!r}")

        r.metadata["outcomes"] = outcomes
        r.metadata["tier_counts"] = tier_counts
        r.metadata["pre_approved_mode"] = s.pre_approved_applications
        r.metadata["auto_submit_approved"] = s.auto_submit_approved
        r.notes.append(
            f"submission: {tier_counts.get('AUTO_APPLY', 0)} AUTO_APPLY, "
            f"{tier_counts.get('REVIEW_REQUIRED', 0)} REVIEW_REQUIRED, "
            f"{tier_counts.get('REJECT', 0)} REJECT; pre_approved={s.pre_approved_applications}"
        )
        r.mark_done()
        return r
