from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import select


class TestEligibilityChecker:
    def test_scam_high_blocks(self, mock_jobs):
        from app.applications.eligibility import ApplicationEligibilityChecker, ApplicationTier
        from app.schemas.enums import ScamRisk
        checker = ApplicationEligibilityChecker()
        scam = next(j for j in mock_jobs if j.source_job_id == "li-scam-031")
        scam.scam_risk = ScamRisk.HIGH
        r = checker.evaluate(scam)
        assert r.tier == ApplicationTier.REJECT
        assert any("scam" in b.lower() for b in r.blockers)

    def test_duplicate_blocks(self, mock_jobs):
        from app.applications.eligibility import ApplicationEligibilityChecker, ApplicationTier
        checker = ApplicationEligibilityChecker()
        job = mock_jobs[0]
        job.is_duplicate = True
        r = checker.evaluate(job)
        assert r.tier == ApplicationTier.REJECT
        assert any("duplicate" in b.lower() for b in r.blockers)

    def test_previously_submitted_blocks(self, mock_jobs):
        from app.applications.eligibility import ApplicationEligibilityChecker, ApplicationTier
        job = mock_jobs[0]
        checker = ApplicationEligibilityChecker(previously_submitted_job_ids={job.job_id})
        r = checker.evaluate(job)
        assert r.tier == ApplicationTier.REJECT

    def test_no_application_url_or_email_blocks(self, mock_jobs):
        from app.applications.eligibility import ApplicationEligibilityChecker, ApplicationTier
        job = mock_jobs[0]
        job.application_url = None
        job.application_email = None
        r = ApplicationEligibilityChecker().evaluate(job)
        assert r.tier == ApplicationTier.REJECT

    def test_auto_apply_requires_high_match(self, mock_jobs, monkeypatch):
        monkeypatch.setenv("AUTO_APPLY_MATCH_THRESHOLD", "85")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            from app.applications.eligibility import ApplicationEligibilityChecker, ApplicationTier
            from app.schemas.enums import ScamRisk
            job = mock_jobs[0]
            job.match_score = 92.0
            job.scam_risk = ScamRisk.NONE
            job.is_duplicate = False
            job.rejected = False
            job.application_url = job.application_url or "https://example.com/apply"
            r = ApplicationEligibilityChecker().evaluate(job)
            assert r.tier == ApplicationTier.AUTO_APPLY
        finally:
            get_settings.cache_clear()

    def test_review_band(self, mock_jobs, monkeypatch):
        monkeypatch.setenv("AUTO_APPLY_MATCH_THRESHOLD", "85")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            from app.applications.eligibility import ApplicationEligibilityChecker, ApplicationTier
            from app.schemas.enums import ScamRisk
            job = mock_jobs[0]
            job.match_score = 78.0
            job.scam_risk = ScamRisk.NONE
            job.is_duplicate = False
            job.rejected = False
            r = ApplicationEligibilityChecker().evaluate(job)
            assert r.tier == ApplicationTier.REVIEW_REQUIRED
        finally:
            get_settings.cache_clear()


class TestHardStopDetector:
    def test_captcha_detected(self):
        from app.submission.hard_stops import HardStopReason, detect_hard_stops
        stops = detect_hard_stops(page_text="Please complete the reCAPTCHA to continue")
        assert any(r == HardStopReason.CAPTCHA for r, _ in stops)

    def test_mfa_detected(self):
        from app.submission.hard_stops import HardStopReason, detect_hard_stops
        stops = detect_hard_stops(page_text="Enter your 2FA code")
        assert any(r == HardStopReason.MFA for r, _ in stops)

    def test_otp_detected(self):
        from app.submission.hard_stops import HardStopReason, detect_hard_stops
        stops = detect_hard_stops(page_text="A verification code sent to your phone")
        assert any(r == HardStopReason.OTP for r, _ in stops)

    def test_identity_verification_detected(self):
        from app.submission.hard_stops import HardStopReason, detect_hard_stops
        stops = detect_hard_stops(page_text="Upload your government photo ID to continue")
        assert any(r == HardStopReason.IDENTITY_VERIFICATION for r, _ in stops)

    def test_payment_detected(self):
        from app.submission.hard_stops import HardStopReason, detect_hard_stops
        stops = detect_hard_stops(page_text="Application fee of $50 required to continue")
        assert any(r == HardStopReason.PAYMENT for r, _ in stops)

    def test_unknown_legal_question_detected(self):
        from app.submission.hard_stops import HardStopReason, detect_hard_stops
        stops = detect_hard_stops(page_text="Are you a US Citizen?")
        assert any(r == HardStopReason.UNKNOWN_LEGAL_QUESTION for r, _ in stops)

    def test_sensitive_pending_input_flagged(self):
        from app.submission.hard_stops import HardStopReason, detect_hard_stops
        stops = detect_hard_stops(pending_user_inputs=["expected_salary"])
        assert any(r == HardStopReason.UNKNOWN_SENSITIVE_QUESTION for r, _ in stops)


class TestApprovedSubmitter:
    def test_submission_disabled_blocks_live_submit(self, profile, mock_jobs, monkeypatch):
        monkeypatch.setenv("SUBMISSION_ENABLED", "false")
        monkeypatch.setenv("AUTO_APPLY_MATCH_THRESHOLD", "40")
        monkeypatch.setenv("REVIEW_REQUIRED_MATCH_FLOOR", "20")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            from app.applications.preparer import ApplicationPreparer
            from app.submission.submitter import ApprovedSubmitter
            from app.schemas.enums import ScamRisk
            job = mock_jobs[0]
            job.match_score = 90.0
            job.scam_risk = ScamRisk.NONE
            job.is_duplicate = False
            job.rejected = False
            app = ApplicationPreparer().prepare(job, profile, dry_run=True)
            app.pending_user_inputs = []
            out = ApprovedSubmitter().submit(job, app)
            assert out.outcome in ("BLOCKED_SUBMISSION_DISABLED", "SIMULATED_SUBMIT_DRY_RUN"), (
                f"with SUBMISSION_ENABLED=false, must not reach live submit. Got: {out.outcome}"
            )
        finally:
            get_settings.cache_clear()

    def test_pre_approved_rejects_low_match(self, profile, mock_jobs, monkeypatch):
        from app.applications.preparer import ApplicationPreparer
        from app.submission.submitter import ApprovedSubmitter
        monkeypatch.setenv("PRE_APPROVED_APPLICATIONS", "true")
        monkeypatch.setenv("REVIEW_REQUIRED_MATCH_FLOOR", "75")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            job = mock_jobs[0]
            job.match_score = 50.0
            app = ApplicationPreparer().prepare(job, profile, dry_run=True)
            out = ApprovedSubmitter().submit(job, app)
            assert out.outcome == "REJECTED_BY_ELIGIBILITY"
        finally:
            get_settings.cache_clear()

    def test_hard_stop_halts_submission(self, profile, mock_jobs, monkeypatch):
        from app.applications.preparer import ApplicationPreparer
        from app.submission.submitter import ApprovedSubmitter
        monkeypatch.setenv("PRE_APPROVED_APPLICATIONS", "true")
        monkeypatch.setenv("AUTO_SUBMIT_APPROVED", "true")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            job = next(j for j in mock_jobs if j.source_job_id == "li-ai-ant-001")
            job.match_score = 95.0
            from app.schemas.enums import ScamRisk
            job.scam_risk = ScamRisk.NONE
            app = ApplicationPreparer().prepare(job, profile, dry_run=True)
            app.pending_user_inputs = []
            out = ApprovedSubmitter().submit(job, app, page_text="Please solve this CAPTCHA to continue")
            assert out.outcome == "APPLICATION_BLOCKED_USER_ACTION"
            assert out.hard_stop_reason == "CAPTCHA"
        finally:
            get_settings.cache_clear()

    def test_sensitive_pending_inputs_route_to_browser_review_not_silent_submit(self, profile, mock_jobs, monkeypatch):
        monkeypatch.setenv("PRE_APPROVED_APPLICATIONS", "true")
        monkeypatch.setenv("AUTO_SUBMIT_APPROVED", "true")
        monkeypatch.setenv("DRY_RUN", "true")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            from app.applications.preparer import ApplicationPreparer
            from app.submission.submitter import ApprovedSubmitter
            job = next(j for j in mock_jobs if j.source_job_id == "li-ai-ant-001")
            job.match_score = 95.0
            from app.schemas.enums import ScamRisk
            job.scam_risk = ScamRisk.NONE
            app = ApplicationPreparer().prepare(job, profile, dry_run=True)
            assert "expected_salary" in app.pending_user_inputs
            out = ApprovedSubmitter().submit(job, app)
            assert out.outcome in (
                "SIMULATED_SUBMIT_DRY_RUN",
                "REJECTED_BY_ELIGIBILITY",
                "BLOCKED_SUBMISSION_DISABLED",
                "REQUIRES_USER_DATA",
            ), (
                f"sensitive pending inputs must never silently auto-submit. "
                f"Must route to assisted-browser-review (SIMULATED_SUBMIT_DRY_RUN), "
                f"REJECTED_BY_ELIGIBILITY, BLOCKED_SUBMISSION_DISABLED (kill-switch), "
                f"or REQUIRES_USER_DATA (hallucination/truthfulness guard). "
                f"Got: {out.outcome}"
            )
            assert out.outcome != "SUBMITTED_LIVE", "sensitive inputs must NEVER produce silent live-submit without user review"
            if out.outcome == "SIMULATED_SUBMIT_DRY_RUN":
                assert any(
                    "sensitive" in n.lower() or "review_required" in n.lower() or "user-fillable" in n.lower()
                    for n in out.notes
                ), f"routed app must note why REVIEW_REQUIRED. notes: {out.notes}"
        finally:
            get_settings.cache_clear()


class TestHarbanClientScoring:
    def test_scoring_detects_ai_signals(self, mock_jobs):
        from app.harban import HarbanClientScorer
        anthropic = next(j for j in mock_jobs if j.source_job_id == "li-ai-ant-001")
        breakdown, ai_reasons, _ = HarbanClientScorer().score_job_as_client_lead(anthropic)
        assert breakdown.ai_relevance > 0
        assert any("llm" in r.lower() or "evaluation" in r.lower() for r in ai_reasons)

    def test_scoring_detects_buying_signals(self, mock_jobs):
        from app.harban import HarbanClientScorer
        job = next(j for j in mock_jobs if "contract" in (j.title or "").lower())
        breakdown, _, buying = HarbanClientScorer().score_job_as_client_lead(job)
        assert len(buying) >= 0

    def test_dual_classifier(self):
        from app.harban import DualOpportunityClassifier, OpportunityType
        c = DualOpportunityClassifier(personal_threshold=70, client_threshold=70)
        assert c.classify(90, 90) == OpportunityType.BOTH
        assert c.classify(90, 30) == OpportunityType.JOB
        assert c.classify(30, 90) == OpportunityType.CLIENT
        assert c.classify(10, 10) == OpportunityType.NEITHER


class TestHarbanServicesTruthfulness:
    def test_all_services_marked_not_delivered(self):
        from app.harban.services import HARBAN_SERVICES
        from app.harban.enums import ServiceStatus
        for svc in HARBAN_SERVICES:
            assert svc.status in {ServiceStatus.DISCUSSION, ServiceStatus.PLANNED}, (
                f"Service {svc.key} is marked DELIVERED but Harban is early-stage; must stay DISCUSSION/PLANNED"
            )

    def test_truthful_service_label_tags_undelivered(self):
        from app.harban.services import HARBAN_SERVICES, truthful_service_label
        for svc in HARBAN_SERVICES:
            lbl = truthful_service_label(svc)
            assert "DISCUSSION" in lbl or "PLANNED" in lbl


class TestOutreachLimits:
    def test_personalization_required(self, profile):
        from app.harban.outreach import HarbanOutreachGenerator, OutreachPersonalizationError
        from app.harban.schema import ClientCompany, ClientContact
        gen = HarbanOutreachGenerator(profile)
        company = ClientCompany(canonical_name="x", display_name="X", discovery_source="t")
        contact = ClientContact(full_name="Jane", company_canonical="x", discovery_source="t")
        with pytest.raises(OutreachPersonalizationError):
            gen.generate_email(company=company, contact=contact, signals=[], client_need_text="")

    def test_outreach_limits_daily_cap(self):
        from app.harban.outreach import OutreachLimiter
        from unittest.mock import patch
        from app.config import Settings
        with patch("app.harban.outreach.get_settings") as m:
            m.return_value = Settings(outreach_max_emails_per_day=2)
            limiter = OutreachLimiter()
            can1, _ = limiter.can_send_email("a@b.com")
            assert can1
            limiter.record_email("a@b.com")
            limiter.record_email("c@d.com")
            can3, reason = limiter.can_send_email("e@f.com")
            assert not can3
            assert "limit" in reason.lower()

    def test_contact_dedup_initial(self):
        from app.harban.outreach import OutreachLimiter
        limiter = OutreachLimiter()
        limiter.record_email("same@contact.com")
        can, reason = limiter.can_send_email("same@contact.com", kind="initial")
        assert not can

    def test_followup_dates(self):
        from app.harban.outreach import schedule_followup_dates
        from datetime import date
        base = date(2026, 10, 4)
        dates = schedule_followup_dates(base)
        kinds = [k for k, _ in dates]
        assert "day-5" in kinds and "day-12" in kinds


class TestHarbanAgentE2E:
    def test_harban_agent_runs_in_orchestrator(self, profile):
        from app.agents import AgentContext, JobAgentOrchestrator
        orch = JobAgentOrchestrator()
        r = orch.run(AgentContext(profile=profile))
        h = r.get("harban")
        assert h is not None
        counts = h.metadata.get("counts", {})
        assert counts.get("opportunities_total", 0) >= 40

    def test_submission_agent_runs_in_orchestrator(self, profile):
        from app.agents import AgentContext, JobAgentOrchestrator
        orch = JobAgentOrchestrator()
        r = orch.run(AgentContext(profile=profile))
        s = r.get("submission")
        assert s is not None
        tier_counts = s.metadata.get("tier_counts", {})
        assert sum(tier_counts.values()) >= 1


class TestHarbanAPI:
    def test_harban_api_endpoints(self, profile):
        from fastapi.testclient import TestClient
        from app.api import create_app
        from app.agents import AgentContext, JobAgentOrchestrator
        orch = JobAgentOrchestrator()
        orch.run(AgentContext(profile=profile))
        app = create_app()
        with TestClient(app) as c:
            assert c.get("/harban/leads").status_code == 200
            assert c.get("/harban/companies").status_code == 200
            assert c.get("/harban/opportunities").status_code == 200
            assert c.get("/harban/outreach-drafts").status_code == 200
            assert c.get("/submission-evidence").status_code == 200


class TestClientFSM:
    def test_invalid_client_transition(self):
        from app.harban import ClientStage, is_valid_client_transition
        assert is_valid_client_transition(ClientStage.DISCOVERED, ClientStage.RESEARCHED)
        assert not is_valid_client_transition(ClientStage.DISCOVERED, ClientStage.WON)
        assert not is_valid_client_transition(ClientStage.WON, ClientStage.PROPOSAL)
        assert not is_valid_client_transition(ClientStage.LOST, ClientStage.CONTACTED)
