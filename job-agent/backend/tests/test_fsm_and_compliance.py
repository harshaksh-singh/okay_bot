from __future__ import annotations

from unittest.mock import patch

import pytest

from app.applications.tracker import ApplicationTracker, InvalidStatusTransition
from app.compliance import ComplianceViolation
from app.schemas.application import Application
from app.schemas.enums import ApplicationStatus, is_valid_transition


def _app() -> Application:
    return Application(application_id="app_test", job_id="job_test", status=ApplicationStatus.DISCOVERED)


class TestFSM:
    def test_discovered_to_matched_valid(self):
        tracker = ApplicationTracker()
        app = _app()
        tracker.transition(app, ApplicationStatus.MATCHED)
        assert app.status == ApplicationStatus.MATCHED

    def test_discovered_to_submitted_invalid(self):
        tracker = ApplicationTracker()
        app = _app()
        with pytest.raises(InvalidStatusTransition):
            tracker.transition(app, ApplicationStatus.SUBMITTED)

    def test_submitted_cannot_go_back_to_matched(self):
        tracker = ApplicationTracker()
        app = _app()
        tracker.transition(app, ApplicationStatus.MATCHED)
        tracker.transition(app, ApplicationStatus.APPROVED)
        tracker.transition(app, ApplicationStatus.APPLICATION_PREPARED)
        tracker.transition(app, ApplicationStatus.AWAITING_USER)
        tracker.transition(app, ApplicationStatus.SUBMITTED)
        with pytest.raises(InvalidStatusTransition):
            tracker.transition(app, ApplicationStatus.MATCHED)

    def test_rejected_is_terminal(self):
        tracker = ApplicationTracker()
        app = _app()
        tracker.transition(app, ApplicationStatus.REJECTED)
        with pytest.raises(InvalidStatusTransition):
            tracker.transition(app, ApplicationStatus.MATCHED)
        with pytest.raises(InvalidStatusTransition):
            tracker.transition(app, ApplicationStatus.SUBMITTED)

    def test_status_history_captured(self):
        tracker = ApplicationTracker()
        app = _app()
        tracker.transition(app, ApplicationStatus.MATCHED, note="first move")
        tracker.transition(app, ApplicationStatus.APPROVED, note="user approved")
        assert len(app.status_history) == 2
        assert app.status_history[0][0] == ApplicationStatus.DISCOVERED
        assert app.status_history[1][0] == ApplicationStatus.MATCHED

    def test_approve_sets_approved_fields(self):
        tracker = ApplicationTracker()
        app = _app()
        tracker.transition(app, ApplicationStatus.MATCHED)
        tracker.approve(app)
        assert app.approved_by_user is True
        assert app.approved_at is not None

    def test_submit_sets_timestamp(self):
        tracker = ApplicationTracker()
        app = _app()
        tracker.transition(app, ApplicationStatus.MATCHED)
        tracker.transition(app, ApplicationStatus.APPROVED)
        tracker.transition(app, ApplicationStatus.APPLICATION_PREPARED)
        tracker.transition(app, ApplicationStatus.AWAITING_USER)
        tracker.mark_submitted(app, evidence="screenshot.png")
        assert app.submitted_at is not None
        assert app.submission_evidence == "screenshot.png"

    def test_is_valid_transition_symmetric_identity(self):
        assert is_valid_transition(ApplicationStatus.DISCOVERED, ApplicationStatus.DISCOVERED) is True


class TestComplianceHardBlock:
    def _run_compliance_with(self, **flags):
        from app.agents.compliance_agent import ComplianceAgent
        from app.agents.base import AgentContext
        from app.config import Settings
        from app.profile import get_profile

        with patch("app.agents.compliance_agent.get_settings") as m:
            m.return_value = Settings(**flags)
            agent = ComplianceAgent()
            ctx = AgentContext(profile=get_profile())
            return agent

    def test_captcha_bypass_raises(self):
        from app.agents.compliance_agent import ComplianceAgent
        from app.agents.base import AgentContext
        from app.config import Settings
        from app.profile import get_profile

        with patch("app.agents.compliance_agent.get_settings") as m:
            m.return_value = Settings(captcha_bypass=True)
            agent = ComplianceAgent()
            ctx = AgentContext(profile=get_profile())
            with pytest.raises(ComplianceViolation) as exc_info:
                agent.run(ctx, [])
            assert any("CAPTCHA_BYPASS" in v for v in exc_info.value.violations)

    def test_mfa_bypass_raises(self):
        from app.agents.compliance_agent import ComplianceAgent
        from app.agents.base import AgentContext
        from app.config import Settings
        from app.profile import get_profile

        with patch("app.agents.compliance_agent.get_settings") as m:
            m.return_value = Settings(mfa_bypass=True)
            agent = ComplianceAgent()
            ctx = AgentContext(profile=get_profile())
            with pytest.raises(ComplianceViolation):
                agent.run(ctx, [])

    def test_rate_limit_bypass_raises(self):
        from app.agents.compliance_agent import ComplianceAgent
        from app.agents.base import AgentContext
        from app.config import Settings
        from app.profile import get_profile

        with patch("app.agents.compliance_agent.get_settings") as m:
            m.return_value = Settings(rate_limit_bypass=True)
            agent = ComplianceAgent()
            ctx = AgentContext(profile=get_profile())
            with pytest.raises(ComplianceViolation):
                agent.run(ctx, [])

    def test_auto_submit_without_approval_raises(self):
        from app.agents.compliance_agent import ComplianceAgent
        from app.agents.base import AgentContext
        from app.config import Settings
        from app.profile import get_profile

        with patch("app.agents.compliance_agent.get_settings") as m:
            m.return_value = Settings(auto_submit=True, user_approval_required=False)
            agent = ComplianceAgent()
            ctx = AgentContext(profile=get_profile())
            with pytest.raises(ComplianceViolation):
                agent.run(ctx, [])

    def test_auto_submit_with_approval_is_soft_warning(self):
        from app.agents.compliance_agent import ComplianceAgent
        from app.agents.base import AgentContext
        from app.config import Settings
        from app.profile import get_profile

        with patch("app.agents.compliance_agent.get_settings") as m:
            m.return_value = Settings(auto_submit=True, user_approval_required=True)
            agent = ComplianceAgent()
            ctx = AgentContext(profile=get_profile())
            result = agent.run(ctx, [])
            assert result.metadata["soft_warnings"]
            assert not result.metadata["hard_violations"]

    def test_safe_defaults_pass(self):
        from app.agents.compliance_agent import ComplianceAgent
        from app.agents.base import AgentContext
        from app.config import Settings
        from app.profile import get_profile

        with patch("app.agents.compliance_agent.get_settings") as m:
            m.return_value = Settings()
            agent = ComplianceAgent()
            ctx = AgentContext(profile=get_profile())
            result = agent.run(ctx, [])
            assert result.metadata["safety_defaults_ok"] is True

    def test_pipeline_halts_on_hard_violation(self):
        from app.agents import JobAgentOrchestrator, AgentContext
        from app.config import Settings
        from app.profile import get_profile

        with patch("app.agents.compliance_agent.get_settings") as m:
            m.return_value = Settings(captcha_bypass=True)
            orch = JobAgentOrchestrator()
            ctx = AgentContext(profile=get_profile())
            result = orch.run(ctx)
            assert result.halted_by_compliance is True
            assert result.get("compliance").errors
            discovery = result.get("discovery")
            assert discovery and any("halted" in n.lower() for n in discovery.notes)


class TestWeightNormalization:
    def test_weights_are_normalized_before_scoring(self):
        from app.config import ScoringWeights
        from app.matching import MatchingEngine
        from app.data.mock_jobs import build_mock_jobs
        from app.profile import get_profile

        all_ones = ScoringWeights(
            technical_skills=1.0, experience=1.0, role_relevance=1.0, location=1.0,
            employment_type=1.0, schedule=1.0, company_priority=1.0, salary=1.0,
        )
        engine = MatchingEngine(weights=all_ones)
        job = next(j for j in build_mock_jobs() if j.source_job_id == "li-ai-ant-001")
        breakdown, _, _ = engine.score(job, get_profile())
        assert breakdown.total() <= 101.0

    def test_zero_weights_do_not_divide_by_zero(self):
        from app.config import ScoringWeights
        from app.matching import MatchingEngine
        from app.data.mock_jobs import build_mock_jobs
        from app.profile import get_profile

        zeros = ScoringWeights(
            technical_skills=0.0, experience=0.0, role_relevance=0.0, location=0.0,
            employment_type=0.0, schedule=0.0, company_priority=0.0, salary=0.0,
        )
        engine = MatchingEngine(weights=zeros)
        job = next(j for j in build_mock_jobs() if j.source_job_id == "li-ai-ant-001")
        breakdown, _, _ = engine.score(job, get_profile())
        assert breakdown.total() >= 0
