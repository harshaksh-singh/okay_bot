from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.campaign.orchestrator import compute_idempotency_key
from app.campaign.resume import (
    CheckpointStage,
    ResumeAction,
    decide_resume_action,
    load_resume_checkpoints,
)


class TestDecideResumeAction:
    def test_safe_replay_from_form_opened(self):
        s = MagicMock()
        s.scalars.return_value.first.return_value = None
        d = decide_resume_action(CheckpointStage.FORM_OPENED.value, "app1", "job1", s)
        assert d.action == ResumeAction.SAFE_REPLAY

    def test_safe_replay_from_form_filled(self):
        s = MagicMock()
        s.scalars.return_value.first.return_value = None
        d = decide_resume_action(CheckpointStage.FORM_FILLED.value, "app1", "job1", s)
        assert d.action == ResumeAction.SAFE_REPLAY

    def test_safe_replay_from_ready_to_submit(self):
        s = MagicMock()
        s.scalars.return_value.first.return_value = None
        d = decide_resume_action(CheckpointStage.READY_TO_SUBMIT.value, "app1", "job1", s)
        assert d.action == ResumeAction.SAFE_REPLAY

    def test_skip_completed_submitted(self):
        s = MagicMock()
        s.scalars.return_value.first.return_value = None
        d = decide_resume_action(CheckpointStage.SUBMITTED.value, "app1", "job1", s)
        assert d.action == ResumeAction.SKIP_COMPLETED

    def test_skip_completed_confirmed(self):
        s = MagicMock()
        s.scalars.return_value.first.return_value = None
        d = decide_resume_action(CheckpointStage.CONFIRMED.value, "app1", "job1", s)
        assert d.action == ResumeAction.SKIP_COMPLETED

    def test_skip_blocked(self):
        s = MagicMock()
        s.scalars.return_value.first.return_value = None
        d = decide_resume_action(CheckpointStage.BLOCKED.value, "app1", "job1", s)
        assert d.action == ResumeAction.SKIP_BLOCKED

    def test_skip_failed(self):
        s = MagicMock()
        s.scalars.return_value.first.return_value = None
        d = decide_resume_action(CheckpointStage.FAILED.value, "app1", "job1", s)
        assert d.action == ResumeAction.SKIP_FAILED

    def test_submitting_without_evidence_marks_uncertain(self):
        s = MagicMock()
        s.scalars.return_value.first.return_value = None
        d = decide_resume_action(CheckpointStage.SUBMITTING.value, "app1", "job1", s)
        assert d.action == ResumeAction.MARK_UNCERTAIN
        assert "uncertain" in d.reason.lower() or "SUBMISSION_UNCERTAIN" in d.reason

    def test_submitting_with_live_evidence_skips(self):
        import sys
        sys.path.insert(0, "backend")
        from app.database import SessionLocal, init_database
        from app.database.models import SubmissionEvidenceRow
        init_database()
        app_id = f"app_crash_{uuid.uuid4().hex[:8]}"
        job_id = f"job_crash_{uuid.uuid4().hex[:8]}"
        idem = compute_idempotency_key(app_id, job_id, channel="live_submit")
        try:
            with SessionLocal() as s:
                s.add(SubmissionEvidenceRow(
                    application_id=app_id,
                    job_id=job_id,
                    outcome="SUBMITTED_LIVE",
                    idempotency_key=idem,
                ))
                s.commit()
                d = decide_resume_action(CheckpointStage.SUBMITTING.value, app_id, job_id, s)
                assert d.action == ResumeAction.SKIP_ALREADY_SUBMITTED
                assert d.has_live_evidence is True
                assert idem == d.idempotency_key
        finally:
            from sqlalchemy import delete
            with SessionLocal() as s:
                s.execute(delete(SubmissionEvidenceRow).where(SubmissionEvidenceRow.idempotency_key == idem))
                s.commit()

    def test_unknown_stage_marks_uncertain(self):
        s = MagicMock()
        s.scalars.return_value.first.return_value = None
        d = decide_resume_action("WHO_KNOWS", "app1", "job1", s)
        assert d.action == ResumeAction.MARK_UNCERTAIN


class TestCrashRestartIdempotency:
    def test_crash_after_submit_prevents_duplicate(self):
        import sys
        sys.path.insert(0, "backend")
        from sqlalchemy import delete, select
        from app.database import SessionLocal, init_database
        from app.database.models import SubmissionCheckpointRow, SubmissionEvidenceRow
        init_database()

        app_id = f"app_crash_{uuid.uuid4().hex[:8]}"
        job_id = f"job_crash_{uuid.uuid4().hex[:8]}"
        idem = compute_idempotency_key(app_id, job_id, channel="live_submit")

        try:
            with SessionLocal() as s:
                s.add(SubmissionEvidenceRow(
                    application_id=app_id,
                    job_id=job_id,
                    outcome="SUBMITTED_LIVE",
                    idempotency_key=idem,
                ))
                s.add(SubmissionCheckpointRow(
                    application_id=app_id,
                    job_id=job_id,
                    stage=CheckpointStage.SUBMITTING.value,
                    url="https://mock-ats.local/apply",
                    decision="AUTO_SUBMIT",
                    retry_count=0,
                ))
                s.commit()

            report = load_resume_checkpoints()

            crash_decisions = [d for d in report.decisions if d.application_id == app_id]
            assert len(crash_decisions) == 1, (
                f"Expected exactly 1 decision for our crashed app, got {len(crash_decisions)}"
            )
            assert crash_decisions[0].action == ResumeAction.SKIP_ALREADY_SUBMITTED
            assert crash_decisions[0].has_live_evidence is True

            with SessionLocal() as s:
                rows = s.scalars(
                    select(SubmissionEvidenceRow).where(
                        SubmissionEvidenceRow.idempotency_key == idem,
                        SubmissionEvidenceRow.outcome.in_(["SUBMITTED_LIVE", "SUBMITTED_CONFIRMED"]),
                    )
                ).all()
                assert len(rows) == 1, (
                    f"Expected exactly 1 SUBMITTED_LIVE row after crash+restart, got {len(rows)}. "
                    f"This proves the idempotency guard prevented duplicate submission."
                )
        finally:
            with SessionLocal() as s:
                s.execute(delete(SubmissionEvidenceRow).where(SubmissionEvidenceRow.idempotency_key == idem))
                s.execute(delete(SubmissionCheckpointRow).where(SubmissionCheckpointRow.application_id == app_id))
                s.commit()

    def test_crash_during_submit_without_evidence_marks_uncertain(self):
        import sys
        sys.path.insert(0, "backend")
        from sqlalchemy import delete, select
        from app.database import SessionLocal, init_database
        from app.database.models import SubmissionCheckpointRow
        init_database()

        app_id = f"app_unc_{uuid.uuid4().hex[:8]}"
        job_id = f"job_unc_{uuid.uuid4().hex[:8]}"

        try:
            with SessionLocal() as s:
                s.add(SubmissionCheckpointRow(
                    application_id=app_id,
                    job_id=job_id,
                    stage=CheckpointStage.SUBMITTING.value,
                    url="https://mock-ats.local/apply",
                    decision="AUTO_SUBMIT",
                    retry_count=0,
                ))
                s.commit()

            report = load_resume_checkpoints()

            unc_decisions = [d for d in report.decisions if d.application_id == app_id]
            assert len(unc_decisions) == 1
            assert unc_decisions[0].action == ResumeAction.MARK_UNCERTAIN
            assert unc_decisions[0].has_live_evidence is False

            with SessionLocal() as s:
                row = s.scalars(select(SubmissionCheckpointRow).where(SubmissionCheckpointRow.application_id == app_id)).first()
                assert row.stage == CheckpointStage.SUBMISSION_UNCERTAIN.value
        finally:
            with SessionLocal() as s:
                s.execute(delete(SubmissionCheckpointRow).where(SubmissionCheckpointRow.application_id == app_id))
                s.commit()
