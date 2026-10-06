from __future__ import annotations

from datetime import datetime, timedelta

from app.submission.throttle import AIMDThrottler, ThrottleState


class TestAIMDThrottler:
    def test_initial_state_uses_base_gap(self):
        t = AIMDThrottler(base_gap_seconds=7.0)
        assert t.current_gap("linkedin") == 7.0

    def test_record_success_decays_gap(self):
        t = AIMDThrottler(base_gap_seconds=7.0, max_gap_seconds=3600.0)
        t._platforms["linkedin"] = ThrottleState(current_gap_seconds=14.0)
        t.record_success("linkedin")
        assert t._platforms["linkedin"].current_gap_seconds == 14.0 * 0.9

    def test_success_cannot_decay_below_base(self):
        t = AIMDThrottler(base_gap_seconds=7.0)
        t._platforms["linkedin"] = ThrottleState(current_gap_seconds=7.0)
        for _ in range(20):
            t.record_success("linkedin")
        assert t._platforms["linkedin"].current_gap_seconds == 7.0

    def test_record_block_doubles_gap(self):
        t = AIMDThrottler(base_gap_seconds=7.0, block_multiplier=2.0, max_gap_seconds=3600.0)
        t.record_block("linkedin", reason="CAPTCHA")
        assert t._platforms["linkedin"].current_gap_seconds == 14.0
        t.record_block("linkedin", reason="CAPTCHA again")
        assert t._platforms["linkedin"].current_gap_seconds == 28.0

    def test_block_cannot_exceed_max_gap(self):
        t = AIMDThrottler(base_gap_seconds=7.0, max_gap_seconds=100.0, block_multiplier=2.0)
        for _ in range(10):
            t.record_block("linkedin")
        assert t._platforms["linkedin"].current_gap_seconds == 100.0

    def test_block_sets_blackout(self):
        t = AIMDThrottler(blackout_hours=24.0)
        before = datetime.utcnow()
        t.record_block("linkedin")
        state = t._platforms["linkedin"]
        assert state.blocked_until is not None
        assert state.blocked_until - before >= timedelta(hours=23, minutes=59)

    def test_is_blocked_true_during_blackout(self):
        t = AIMDThrottler()
        t.record_block("linkedin")
        assert t.is_blocked("linkedin") is True

    def test_is_blocked_resets_after_blackout_expires(self):
        t = AIMDThrottler()
        t.record_block("linkedin")
        state = t._platforms["linkedin"]
        state.blocked_until = datetime.utcnow() - timedelta(seconds=1)
        assert t.is_blocked("linkedin") is False
        assert state.current_gap_seconds == t.base_gap

    def test_platform_isolation(self):
        t = AIMDThrottler()
        t.record_block("linkedin")
        t.record_success("naukri")
        assert t.is_blocked("linkedin")
        assert not t.is_blocked("naukri")

    def test_wait_time_includes_jitter(self):
        t = AIMDThrottler(base_gap_seconds=10.0, jitter_percent=0.2)
        waits = [t.wait_time("linkedin") for _ in range(20)]
        assert all(8.0 <= w <= 12.0 for w in waits), f"Wait times outside jitter range: {waits}"
        assert len(set(waits)) > 1

    def test_status_report(self):
        t = AIMDThrottler()
        t.record_success("naukri")
        t.record_block("linkedin")
        status = t.status()
        assert "naukri" in status
        assert "linkedin" in status
        assert status["linkedin"]["blocked"] is True
        assert status["naukri"]["blocked"] is False
        assert status["linkedin"]["total_blocks_seen"] == 1


class TestIdempotencyColumn:
    def test_submission_evidence_has_idempotency_key_column(self):
        from app.database.models import SubmissionEvidenceRow
        cols = {c.name for c in SubmissionEvidenceRow.__table__.columns}
        assert "idempotency_key" in cols

    def test_idempotency_key_is_unique(self):
        from app.database.models import SubmissionEvidenceRow
        col = SubmissionEvidenceRow.__table__.columns["idempotency_key"]
        assert col.unique is True

    def test_insert_duplicate_key_raises(self):
        import sys
        sys.path.insert(0, "backend")
        from app.database import SessionLocal, init_database
        from app.database.models import SubmissionEvidenceRow

        init_database()
        with SessionLocal() as s:
            r1 = SubmissionEvidenceRow(
                application_id="app_idem_1",
                job_id="job_idem_1",
                outcome="SUBMITTED_LIVE",
                idempotency_key="test_key_unique_12345",
            )
            s.add(r1)
            s.commit()

            r2 = SubmissionEvidenceRow(
                application_id="app_idem_2",
                job_id="job_idem_2",
                outcome="SUBMITTED_LIVE",
                idempotency_key="test_key_unique_12345",
            )
            s.add(r2)
            raised = False
            try:
                s.commit()
            except Exception:
                raised = True
                s.rollback()
            assert raised, "Expected IntegrityError on duplicate idempotency_key"

            s.query(SubmissionEvidenceRow).filter(
                SubmissionEvidenceRow.idempotency_key == "test_key_unique_12345"
            ).delete()
            s.commit()
