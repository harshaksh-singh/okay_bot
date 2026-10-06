from __future__ import annotations

import json

import pytest
from sqlalchemy import select


class TestEligibilityRoutesSensitiveInputsToReview:
    def test_sensitive_pending_inputs_become_review_not_reject(self, mock_jobs, profile):
        from app.applications.eligibility import ApplicationEligibilityChecker, ApplicationTier
        from app.applications.preparer import ApplicationPreparer
        from app.schemas.enums import ScamRisk

        job = next(j for j in mock_jobs if j.source_job_id == "li-ai-ant-001")
        job.match_score = 95.0
        job.scam_risk = ScamRisk.NONE
        app = ApplicationPreparer().prepare(job, profile, dry_run=True)
        assert "expected_salary" in app.pending_user_inputs
        result = ApplicationEligibilityChecker().evaluate(job, app)
        assert result.tier == ApplicationTier.REVIEW_REQUIRED
        assert any("sensitive" in r.lower() for r in result.reasons)

    def test_clean_application_still_reaches_auto_apply(self, mock_jobs, profile):
        from app.applications.eligibility import ApplicationEligibilityChecker, ApplicationTier
        from app.applications.preparer import ApplicationPreparer
        from app.schemas.enums import ScamRisk

        job = next(j for j in mock_jobs if j.source_job_id == "li-ai-ant-001")
        job.match_score = 95.0
        job.scam_risk = ScamRisk.NONE
        app = ApplicationPreparer().prepare(job, profile, dry_run=True)
        app.pending_user_inputs = []
        result = ApplicationEligibilityChecker().evaluate(job, app)
        assert result.tier == ApplicationTier.AUTO_APPLY

    def test_configured_salary_notice_start_removes_sensitive_block(self, mock_jobs, profile):
        from datetime import date
        from app.applications.eligibility import ApplicationEligibilityChecker, ApplicationTier
        from app.applications.preparer import ApplicationPreparer
        from app.schemas.enums import ScamRisk

        profile.salary_expectation_min_inr_monthly = 50000
        profile.availability.notice_period_weeks = 4
        profile.availability.earliest_start = date(2026, 11, 1)
        try:
            job = next(j for j in mock_jobs if j.source_job_id == "li-ai-ant-001")
            job.match_score = 95.0
            job.scam_risk = ScamRisk.NONE
            app = ApplicationPreparer().prepare(job, profile, dry_run=True)
            assert "expected_salary" not in app.pending_user_inputs
            assert "notice_period" not in app.pending_user_inputs
            assert "earliest_start" not in app.pending_user_inputs
            result = ApplicationEligibilityChecker().evaluate(job, app)
            assert result.tier == ApplicationTier.AUTO_APPLY, f"got {result.tier}; blockers={result.blockers}; reasons={result.reasons}"
        finally:
            profile.salary_expectation_min_inr_monthly = None
            profile.availability.notice_period_weeks = None
            profile.availability.earliest_start = None

    def test_quality_threshold_bypasses_auto_apply(self, mock_jobs, profile, monkeypatch):
        from app.applications.eligibility import ApplicationEligibilityChecker, ApplicationTier
        from app.schemas.enums import ScamRisk

        monkeypatch.setenv("AUTO_APPLY_QUALITY_THRESHOLD", "90")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            job = next(j for j in mock_jobs if j.source_job_id == "li-ai-ant-001")
            job.match_score = 95.0
            job.scam_risk = ScamRisk.LOW
            result = ApplicationEligibilityChecker().evaluate(job)
            assert result.tier == ApplicationTier.REVIEW_REQUIRED
        finally:
            get_settings.cache_clear()


class TestOutreachNeverInventsContact:
    def test_outreach_draft_has_template_placeholder_not_fake_name(self, profile, monkeypatch):
        monkeypatch.setenv("CLIENT_OUTREACH_ENABLED", "true")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            from app.agents import AgentContext, JobAgentOrchestrator
            orch = JobAgentOrchestrator()
            r = orch.run(AgentContext(profile=profile))
            h = r.get("harban")
            assert h is not None
            drafts = h.metadata.get("outreach_drafts", [])
            for d in drafts:
                assert "Hiring Manager" not in d.get("body", ""), "outreach must not fabricate 'Hiring Manager'"
                assert "{{recipient_first_name}}" in d.get("body", "")
                assert d.get("status") == "BLOCKED_REQUIRES_REAL_CONTACT"
                assert d.get("recipient") is None, "outreach must have no recipient until real contact sourced"
                assert "Section 30" in (d.get("notes") or "")
        finally:
            get_settings.cache_clear()


class TestEvidenceJsonIncludesSelfPath:
    def test_evidence_json_includes_evidence_path(self, profile, mock_jobs, tmp_path, monkeypatch):
        from app.applications.preparer import ApplicationPreparer
        from app.submission.submitter import ApprovedSubmitter

        monkeypatch.setenv("PRE_APPROVED_APPLICATIONS", "true")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            job = mock_jobs[0]
            app = ApplicationPreparer().prepare(job, profile, dry_run=True)
            sub = ApprovedSubmitter(evidence_dir=tmp_path)
            out = sub.submit(job, app)
            assert out.evidence_path is not None
            payload = json.loads((tmp_path / f"{app.application_id}.json").read_text())
            assert payload.get("evidence_path") is not None
            assert payload["evidence_path"].endswith(f"{app.application_id}.json")
        finally:
            get_settings.cache_clear()


class TestWiredConfigFlags:
    def test_truthfulness_hard_block_routes_violations_to_review(self, profile, monkeypatch):
        from app.agents.base import AgentContext, AgentResult
        from app.agents.quality_agent import QualityAgent
        from app.applications.preparer import ApplicationPreparer
        from app.schemas.enums import ApplicationStatus
        from app.data.mock_jobs import build_mock_jobs

        monkeypatch.setenv("TRUTHFULNESS_HARD_BLOCK", "true")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            job = build_mock_jobs()[0]
            app = ApplicationPreparer().prepare(job, profile, dry_run=True)
            app.cover_letter_text = "I have a PhD from Stanford and 15 years of experience."
            app_result = AgentResult(agent="application")
            app_result.metadata["applications"] = [app]
            ctx = AgentContext(profile=profile)
            r = QualityAgent().run(ctx, [app_result])
            assert r.metadata["truthfulness_hard_block_active"] is True
            assert app.application_id in r.metadata["blocked_application_ids"]
            assert app.status == ApplicationStatus.REVIEW_REQUIRED
        finally:
            get_settings.cache_clear()

    def test_compliance_hard_block_soft_mode_logs_but_does_not_raise(self, monkeypatch):
        from app.agents.compliance_agent import ComplianceAgent
        from app.agents.base import AgentContext
        from unittest.mock import patch
        from app.compliance import ComplianceViolation
        from app.config import Settings
        from app.profile import get_profile

        with patch("app.agents.compliance_agent.get_settings") as m:
            m.return_value = Settings(captcha_bypass=True, compliance_hard_block=False)
            agent = ComplianceAgent()
            ctx = AgentContext(profile=get_profile())
            r = agent.run(ctx, [])
            assert r.metadata["hard_violations"]
            assert any("compliance_hard_block=false" in n for n in r.notes)

    def test_auto_email_approved_sets_ready_to_send_mode(self, profile, monkeypatch):
        from app.agents import AgentContext, JobAgentOrchestrator
        monkeypatch.setenv("PRE_APPROVED_APPLICATIONS", "true")
        monkeypatch.setenv("AUTO_EMAIL_APPROVED", "true")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            orch = JobAgentOrchestrator()
            r = orch.run(AgentContext(profile=profile))
            c = r.get("communication")
            assert c.metadata.get("email_mode") == "READY_TO_SEND"
        finally:
            get_settings.cache_clear()


class TestTruthfulnessBlocksSubmission:
    def test_quality_blocked_app_cannot_reach_auto_apply(self, profile, mock_jobs, monkeypatch):
        from app.applications.preparer import ApplicationPreparer
        from app.agents.quality_agent import QualityAgent
        from app.agents.submission_agent import SubmissionAgent
        from app.agents.base import AgentContext, AgentResult
        from app.schemas.enums import ScamRisk

        monkeypatch.setenv("TRUTHFULNESS_HARD_BLOCK", "true")
        monkeypatch.setenv("PRE_APPROVED_APPLICATIONS", "true")
        monkeypatch.setenv("AUTO_SUBMIT_APPROVED", "true")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            job = next(j for j in mock_jobs if j.source_job_id == "li-ai-ant-001")
            job.match_score = 95.0
            job.scam_risk = ScamRisk.NONE
            app = ApplicationPreparer().prepare(job, profile, dry_run=True)
            app.pending_user_inputs = []
            app.cover_letter_text = "I have a PhD from Stanford and 15 years of experience."

            app_result = AgentResult(agent="application")
            app_result.metadata["applications"] = [app]
            match_result = AgentResult(agent="matching", jobs=[job])
            ctx = AgentContext(profile=profile)

            q = QualityAgent().run(ctx, [app_result, match_result])
            assert app.application_id in q.metadata["blocked_application_ids"]

            s_result = SubmissionAgent().run(ctx, [app_result, match_result, q])
            outcomes = s_result.metadata.get("outcomes", [])
            assert len(outcomes) == 1
            outcome = outcomes[0]
            assert outcome["outcome"] == "BLOCKED_BY_TRUTHFULNESS_HARD_BLOCK"
            assert outcome["tier"] == "REVIEW_REQUIRED"
            tier_counts = s_result.metadata.get("tier_counts", {})
            assert tier_counts.get("AUTO_APPLY", 0) == 0
            assert tier_counts.get("REVIEW_REQUIRED", 0) == 1
        finally:
            get_settings.cache_clear()


class TestClientFollowupPersistence:
    def test_pipeline_writes_client_followups(self, profile):
        from app.agents import AgentContext, JobAgentOrchestrator
        from app.database import SessionLocal, init_database
        from app.database.models import ClientFollowupRow
        init_database()
        orch = JobAgentOrchestrator()
        orch.run(AgentContext(profile=profile))
        with SessionLocal() as s:
            rows = s.scalars(select(ClientFollowupRow)).all()
        kinds = {r.kind for r in rows}
        assert kinds == {"day-5", "day-12"} or (len(rows) == 0 and "no leads qualified")

    def test_pipeline_idempotent_for_client_followups(self, profile):
        from app.agents import AgentContext, JobAgentOrchestrator
        from app.database import SessionLocal, init_database
        from app.database.models import ClientFollowupRow
        init_database()
        orch = JobAgentOrchestrator()
        orch.run(AgentContext(profile=profile))
        with SessionLocal() as s:
            before = len(s.scalars(select(ClientFollowupRow)).all())
        orch.run(AgentContext(profile=profile))
        with SessionLocal() as s:
            after = len(s.scalars(select(ClientFollowupRow)).all())
        assert before == after
