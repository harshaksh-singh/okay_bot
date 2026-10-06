from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.applications.eligibility import ApplicationEligibilityChecker, ApplicationTier
from app.applications.tracker import ApplicationTracker
from app.config import get_settings
from app.observability import get_logger
from app.schemas import Job
from app.schemas.application import Application
from app.schemas.enums import ApplicationStatus
from app.submission.hard_stops import HardStopReason, detect_hard_stops

log = get_logger("submitter")


@dataclass
class SubmissionOutcome:
    application_id: str
    job_id: str
    outcome: str
    submitted_at: datetime | None = None
    confirmation: bool = False
    confirmation_text: str | None = None
    confirmation_url: str | None = None
    hard_stop_reason: str | None = None
    evidence_path: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "application_id": self.application_id,
            "job_id": self.job_id,
            "outcome": self.outcome,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "confirmation": self.confirmation,
            "confirmation_text": self.confirmation_text,
            "confirmation_url": self.confirmation_url,
            "hard_stop_reason": self.hard_stop_reason,
            "evidence_path": self.evidence_path,
            "notes": list(self.notes),
        }


class ApprovedSubmitter:
    def __init__(
        self,
        evidence_dir: Path | None = None,
        previously_submitted_job_ids: set[str] | None = None,
    ) -> None:
        s = get_settings()
        self.evidence_dir = evidence_dir or (s.data_dir / "submission_evidence")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.eligibility = ApplicationEligibilityChecker(previously_submitted_job_ids=previously_submitted_job_ids)
        self.tracker = ApplicationTracker()

    def _has_prior_live_submission(self, idempotency_key: str) -> bool:
        try:
            from sqlalchemy import select
            from app.database import SessionLocal, init_database
            from app.database.models import SubmissionEvidenceRow
            init_database()
            with SessionLocal() as session:
                row = session.scalars(
                    select(SubmissionEvidenceRow).where(
                        SubmissionEvidenceRow.idempotency_key == idempotency_key,
                        SubmissionEvidenceRow.outcome.in_(["SUBMITTED_LIVE", "SUBMITTED_CONFIRMED"]),
                    )
                ).first()
                return row is not None
        except Exception as e:
            log.warning("submitter.idempotency_check_failed", error=str(e))
            return False

    def submit(self, job: Job, application: Application, page_text: str = "") -> SubmissionOutcome:
        s = get_settings()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        outcome = SubmissionOutcome(application_id=application.application_id, job_id=job.job_id, outcome="PREPARED")

        elig = self.eligibility.evaluate(job, application)
        if elig.tier == ApplicationTier.REJECT:
            outcome.outcome = "REJECTED_BY_ELIGIBILITY"
            outcome.notes.extend(elig.blockers)
            outcome.notes.extend(elig.reasons)
            self._write_evidence(outcome)
            return outcome
        if elig.tier == ApplicationTier.REVIEW_REQUIRED:
            outcome.notes.append(
                "REVIEW_REQUIRED routed to assisted-submit flow (headful browser IS the human review): "
                + "; ".join(elig.reasons)
            )

        from app.submission.hard_stops import HardStopReason
        _user_fillable_stops = {HardStopReason.UNKNOWN_SENSITIVE_QUESTION, HardStopReason.UNVERIFIABLE_FIELD}
        all_stops = detect_hard_stops(page_text=page_text, application=application, job=job)
        pre_submit_stops = [(r, m) for r, m in all_stops if r not in _user_fillable_stops]
        if pre_submit_stops:
            reason, msg = pre_submit_stops[0]
            outcome.outcome = "APPLICATION_BLOCKED_USER_ACTION"
            outcome.hard_stop_reason = reason.value
            outcome.notes.append(msg)
            try:
                self.tracker.transition(application, ApplicationStatus.AWAITING_USER, note=msg)
            except Exception as e:
                outcome.notes.append(f"status transition failed: {e}")
            self._write_evidence(outcome)
            return outcome
        for r, m in all_stops:
            if r in _user_fillable_stops:
                outcome.notes.append(f"user-fillable in browser: {r.value} - {m}")

        try:
            from app.submission.answer_validation import AnswerValidationEngine
            from app.profile import get_profile
            validation = AnswerValidationEngine(get_profile()).validate(application, job)
            if not validation.valid:
                outcome.outcome = "REQUIRES_USER_DATA"
                outcome.notes.append("hallucination guard: answers contain unsupported claims; routed for user review")
                outcome.notes.extend(f"truthfulness: {v.surface}: {v.issue}" for v in validation.violations)
                self._write_evidence(outcome)
                return outcome
        except Exception as e:
            log.warning("submitter.answer_validation_failed", error=str(e))

        if not s.submission_enabled:
            outcome.outcome = "BLOCKED_SUBMISSION_DISABLED"
            outcome.notes.append(
                "SUBMISSION_ENABLED=false; global emergency kill switch is engaged. "
                "Set SUBMISSION_ENABLED=true to permit autonomous live submission."
            )
            self._write_evidence(outcome)
            return outcome

        if not s.dry_run:
            from app.campaign.orchestrator import compute_idempotency_key
            idem_key = compute_idempotency_key(application.application_id, job.job_id, channel="live_submit")
            if self._has_prior_live_submission(idem_key):
                outcome.outcome = "SKIPPED_IDEMPOTENT"
                outcome.notes.append(
                    f"Skipped: prior SUBMITTED_LIVE evidence exists for idempotency_key "
                    f"{idem_key[:16]}... (application={application.application_id}, job={job.job_id})"
                )
                self._write_evidence(outcome)
                return outcome
            outcome.notes.append(f"idempotency_key: {idem_key[:16]}...")

            try:
                from app.discovery.http_client import check_robots_allowed
                if job.application_url and not check_robots_allowed(str(job.application_url)):
                    outcome.outcome = "BLOCKED_ROBOTS_DISALLOWED"
                    outcome.hard_stop_reason = "ROBOTS_DISALLOWED"
                    outcome.notes.append(
                        f"robots.txt disallows automated access to {job.application_url}; "
                        "respecting site policy and skipping autonomous submission"
                    )
                    try:
                        self.tracker.transition(
                            application,
                            ApplicationStatus.AWAITING_USER,
                            note="robots.txt disallowed autonomous access",
                        )
                    except Exception:
                        pass
                    self._write_evidence(outcome)
                    return outcome
            except Exception as e:
                log.warning("submitter.robots_check_failed", error=str(e))

            from app.browser import AssistedApplicationSession, is_browser_available
            if not is_browser_available():
                outcome.outcome = "SUBMITTED_PLACEHOLDER_REQUIRES_BROWSER"
                outcome.notes.append(
                    "Playwright not installed; run: .venv/bin/pip install playwright && "
                    ".venv/bin/playwright install chromium"
                )
                outcome.submitted_at = now
                self._write_evidence(outcome)
                return outcome

            session = AssistedApplicationSession(job=job, application=application)
            live = session.submit_assisted_live()
            outcome.notes.extend(live.notes)
            if live.screenshots:
                outcome.evidence_path = str(live.screenshots[-1])

            def _transition(*targets: ApplicationStatus, note: str | None = None) -> None:
                for target in targets:
                    try:
                        self.tracker.transition(application, target, note=note)
                    except Exception as e:
                        outcome.notes.append(f"status transition to {target.value} failed: {e}")
                        return

            if live.status == "SUBMITTED_LIVE":
                outcome.outcome = "SUBMITTED_LIVE"
                outcome.confirmation = True
                outcome.confirmation_text = live.confirmation_text
                outcome.confirmation_url = live.confirmation_url
                outcome.submitted_at = now
                _transition(ApplicationStatus.APPLICATION_STARTED, ApplicationStatus.SUBMITTED, note="live submit confirmed")
            elif live.status == "SUBMITTED_PENDING_CONFIRMATION":
                outcome.outcome = "SUBMITTED_PENDING_CONFIRMATION"
                outcome.submitted_at = now
                _transition(ApplicationStatus.APPLICATION_STARTED, ApplicationStatus.AWAITING_USER, note="user clicked submit; confirmation not auto-detected")
            elif live.status == "BLOCKED_HARD_STOP":
                outcome.outcome = "APPLICATION_BLOCKED_USER_ACTION"
                outcome.hard_stop_reason = live.hard_stop_reason
                _transition(ApplicationStatus.AWAITING_USER, note=f"live hard-stop: {live.hard_stop_reason}")
            elif live.status == "AWAITING_USER_CONFIRMATION":
                outcome.outcome = "AWAITING_USER_CONFIRMATION"
                _transition(ApplicationStatus.AWAITING_USER, note="user did not click submit before timeout")
            elif live.status == "SUBMISSION_UNCERTAIN":
                outcome.outcome = "SUBMISSION_UNCERTAIN"
                outcome.submitted_at = now
                _transition(ApplicationStatus.APPLICATION_STARTED, ApplicationStatus.AWAITING_USER, note="autonomous submit clicked but confirmation not detected; requires human verification")
            elif live.status == "AUTONOMOUS_CLICK_FAILED":
                outcome.outcome = "AUTONOMOUS_CLICK_FAILED"
                outcome.hard_stop_reason = live.hard_stop_reason or "SUBMIT_BUTTON_NOT_FOUND"
                _transition(ApplicationStatus.AWAITING_USER, note="autonomous click could not find a valid Submit button; manual review required")
            elif live.status.startswith("BLOCKED_"):
                outcome.outcome = "APPLICATION_BLOCKED_USER_ACTION"
                outcome.hard_stop_reason = live.hard_stop_reason or live.status
                _transition(ApplicationStatus.AWAITING_USER, note=f"decision engine blocked in-browser: {live.status}")
            else:
                outcome.outcome = "SUBMITTED_PLACEHOLDER_REQUIRES_BROWSER"
                outcome.notes.append(f"live submit returned unexpected status: {live.status}")

            self._write_evidence(outcome)
            return outcome

        outcome.outcome = "SIMULATED_SUBMIT_DRY_RUN"
        outcome.notes.append("DRY_RUN=true; simulated submission did not reach the external site")
        outcome.submitted_at = now
        outcome.confirmation = True
        outcome.confirmation_text = f"[simulated] application prepared for {job.company}: {job.title}"
        try:
            self.tracker.transition(application, ApplicationStatus.APPLICATION_PREPARED)
        except Exception:
            pass
        self._write_evidence(outcome)
        return outcome

    def _write_evidence(self, outcome: SubmissionOutcome) -> None:
        filename = self.evidence_dir / f"{outcome.application_id}.json"
        outcome.evidence_path = str(filename)
        try:
            filename.write_text(json.dumps(outcome.to_dict(), indent=2))
            log.info("submitter.evidence_written", path=outcome.evidence_path, outcome=outcome.outcome)
        except Exception as e:
            log.warning("submitter.evidence_write_failed", error=str(e))
