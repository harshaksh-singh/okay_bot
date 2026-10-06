from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.campaign.orchestrator import compute_idempotency_key


class CheckpointStage(str, Enum):
    FORM_OPENED = "FORM_OPENED"
    FORM_FILLED = "FORM_FILLED"
    READY_TO_SUBMIT = "READY_TO_SUBMIT"
    SUBMITTING = "SUBMITTING"
    SUBMISSION_UNCERTAIN = "SUBMISSION_UNCERTAIN"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class ResumeAction(str, Enum):
    SAFE_REPLAY = "SAFE_REPLAY"
    SKIP_ALREADY_SUBMITTED = "SKIP_ALREADY_SUBMITTED"
    SKIP_COMPLETED = "SKIP_COMPLETED"
    SKIP_BLOCKED = "SKIP_BLOCKED"
    SKIP_FAILED = "SKIP_FAILED"
    MARK_UNCERTAIN = "MARK_UNCERTAIN"


_TERMINAL_STAGES = {
    CheckpointStage.SUBMITTED,
    CheckpointStage.CONFIRMED,
}

_SAFE_REPLAY_STAGES = {
    CheckpointStage.FORM_OPENED,
    CheckpointStage.FORM_FILLED,
    CheckpointStage.READY_TO_SUBMIT,
}

_UNCERTAIN_STAGES = {
    CheckpointStage.SUBMITTING,
    CheckpointStage.SUBMISSION_UNCERTAIN,
}


@dataclass
class ResumeDecision:
    application_id: str
    job_id: str
    stage: str
    action: ResumeAction
    reason: str
    idempotency_key: str
    has_live_evidence: bool = False


@dataclass
class ResumeReport:
    checkpoints_found: int = 0
    safe_replay: int = 0
    skipped_already_submitted: int = 0
    skipped_completed: int = 0
    skipped_blocked: int = 0
    skipped_failed: int = 0
    marked_uncertain: int = 0
    decisions: list[ResumeDecision] = field(default_factory=list)


def _query_live_evidence_exists(session, idempotency_key: str) -> bool:
    try:
        from sqlalchemy import select
        from app.database.models import SubmissionEvidenceRow
        row = session.scalars(
            select(SubmissionEvidenceRow).where(
                SubmissionEvidenceRow.idempotency_key == idempotency_key,
                SubmissionEvidenceRow.outcome.in_(["SUBMITTED_LIVE", "SUBMITTED_CONFIRMED"]),
            )
        ).first()
        return row is not None
    except Exception:
        return False


def decide_resume_action(
    stage_str: str,
    application_id: str,
    job_id: str,
    session,
) -> ResumeDecision:
    is_unknown_stage = False
    try:
        stage = CheckpointStage(stage_str)
    except ValueError:
        stage = None
        is_unknown_stage = True
    idem_key = compute_idempotency_key(application_id, job_id, channel="live_submit")
    has_evidence = _query_live_evidence_exists(session, idem_key)
    stage_label = stage.value if stage is not None else stage_str

    if has_evidence:
        return ResumeDecision(
            application_id=application_id,
            job_id=job_id,
            stage=stage_label,
            action=ResumeAction.SKIP_ALREADY_SUBMITTED,
            reason=f"Live evidence with idempotency_key {idem_key[:16]}... already exists",
            idempotency_key=idem_key,
            has_live_evidence=True,
        )
    if is_unknown_stage:
        return ResumeDecision(
            application_id=application_id,
            job_id=job_id,
            stage=stage_label,
            action=ResumeAction.MARK_UNCERTAIN,
            reason=f"Unknown stage {stage_str!r}; marking uncertain",
            idempotency_key=idem_key,
        )
    if stage in _TERMINAL_STAGES:
        return ResumeDecision(
            application_id=application_id,
            job_id=job_id,
            stage=stage.value,
            action=ResumeAction.SKIP_COMPLETED,
            reason=f"Stage {stage.value} is terminal",
            idempotency_key=idem_key,
        )
    if stage == CheckpointStage.BLOCKED:
        return ResumeDecision(
            application_id=application_id,
            job_id=job_id,
            stage=stage.value,
            action=ResumeAction.SKIP_BLOCKED,
            reason="Checkpoint marked BLOCKED",
            idempotency_key=idem_key,
        )
    if stage == CheckpointStage.FAILED:
        return ResumeDecision(
            application_id=application_id,
            job_id=job_id,
            stage=stage.value,
            action=ResumeAction.SKIP_FAILED,
            reason="Checkpoint marked FAILED",
            idempotency_key=idem_key,
        )
    if stage in _UNCERTAIN_STAGES:
        return ResumeDecision(
            application_id=application_id,
            job_id=job_id,
            stage=stage.value,
            action=ResumeAction.MARK_UNCERTAIN,
            reason=f"Stage {stage.value} crashed between submit and confirmation; no live evidence found. Mark SUBMISSION_UNCERTAIN; needs human verification.",
            idempotency_key=idem_key,
        )
    if stage in _SAFE_REPLAY_STAGES:
        return ResumeDecision(
            application_id=application_id,
            job_id=job_id,
            stage=stage.value,
            action=ResumeAction.SAFE_REPLAY,
            reason=f"Stage {stage.value} is pre-submit; safe to replay",
            idempotency_key=idem_key,
        )
    return ResumeDecision(
        application_id=application_id,
        job_id=job_id,
        stage=stage.value,
        action=ResumeAction.MARK_UNCERTAIN,
        reason=f"Unknown stage {stage_str!r}; marking uncertain",
        idempotency_key=idem_key,
    )


def load_resume_checkpoints(session_factory=None) -> ResumeReport:
    report = ResumeReport()
    try:
        if session_factory is None:
            from app.database import SessionLocal, init_database
            init_database()
            session_factory = SessionLocal
        with session_factory() as session:
            from sqlalchemy import select
            from app.database.models import SubmissionCheckpointRow
            rows = session.scalars(
                select(SubmissionCheckpointRow).where(
                    SubmissionCheckpointRow.stage.notin_([
                        CheckpointStage.SUBMITTED.value,
                        CheckpointStage.CONFIRMED.value,
                    ])
                )
            ).all()
            report.checkpoints_found = len(rows)
            for row in rows:
                decision = decide_resume_action(
                    row.stage,
                    row.application_id,
                    row.job_id,
                    session,
                )
                report.decisions.append(decision)
                if decision.action == ResumeAction.SAFE_REPLAY:
                    report.safe_replay += 1
                elif decision.action == ResumeAction.SKIP_ALREADY_SUBMITTED:
                    report.skipped_already_submitted += 1
                elif decision.action == ResumeAction.SKIP_COMPLETED:
                    report.skipped_completed += 1
                elif decision.action == ResumeAction.SKIP_BLOCKED:
                    report.skipped_blocked += 1
                elif decision.action == ResumeAction.SKIP_FAILED:
                    report.skipped_failed += 1
                elif decision.action == ResumeAction.MARK_UNCERTAIN:
                    report.marked_uncertain += 1
                    try:
                        row.stage = CheckpointStage.SUBMISSION_UNCERTAIN.value
                        row.blocker_reason = decision.reason[:256]
                        row.updated_at = datetime.utcnow()
                    except Exception:
                        pass
            session.commit()
    except Exception as e:
        import logging
        logging.getLogger("campaign.resume").warning(f"resume_load_failed: {e!r}")
    return report
