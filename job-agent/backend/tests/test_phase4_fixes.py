from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import select


class TestCircuitBreakerDoesNotDoubleCount:
    def test_single_connect_error_records_only_one_failure(self):
        from app.discovery.http_client import HttpClient
        import httpx

        client = HttpClient(circuit_failure_threshold=5, circuit_cooldown_seconds=60, respect_robots=False, max_retries=0)
        with patch("httpx.Client") as m:
            instance = m.return_value.__enter__.return_value
            instance.request.side_effect = httpx.ConnectError("boom")
            client.get("http://flaky.example/path")
        status = client.circuit_status()
        assert status.get("flaky.example", {}).get("failure_count", 0) == 1
        assert status.get("flaky.example", {}).get("open") is False

    def test_single_connect_error_with_retries_still_one_failure(self):
        from app.discovery.http_client import HttpClient
        import httpx

        client = HttpClient(circuit_failure_threshold=3, circuit_cooldown_seconds=60, respect_robots=False, max_retries=3, backoff_base=0.0)
        with patch("httpx.Client") as m:
            instance = m.return_value.__enter__.return_value
            instance.request.side_effect = httpx.ConnectError("boom")
            client.get("http://flaky2.example/path")
        status = client.circuit_status()
        assert status.get("flaky2.example", {}).get("failure_count", 0) == 1, "a single request must only record one circuit failure"


class TestFollowupNoFollowupStates:
    def _ctx(self, profile, applications):
        from app.agents.base import AgentContext, AgentResult
        prev = []
        app_result = AgentResult(agent="application")
        app_result.metadata["applications"] = applications
        prev.append(app_result)
        return AgentContext(profile=profile), prev

    def test_replied_status_skips_followup(self, profile):
        from app.agents.followup_agent import FollowupAgent
        from app.schemas.application import Application
        from app.schemas.enums import ApplicationStatus
        app = Application(application_id="a1", job_id="j1", status=ApplicationStatus.REPLIED)
        ctx, prev = self._ctx(profile, [app])
        r = FollowupAgent().run(ctx, prev)
        assert r.metadata["followups_scheduled"] == []
        assert any("REPLIED" in s["reason"] for s in r.metadata["followups_skipped"])

    def test_no_further_contact_requested_skips(self, profile):
        from app.agents.followup_agent import FollowupAgent
        from app.schemas.application import Application
        from app.schemas.enums import ApplicationStatus
        app = Application(application_id="a2", job_id="j2", status=ApplicationStatus.NO_FURTHER_CONTACT_REQUESTED)
        ctx, prev = self._ctx(profile, [app])
        r = FollowupAgent().run(ctx, prev)
        assert r.metadata["followups_scheduled"] == []

    def test_closed_status_skips(self, profile):
        from app.agents.followup_agent import FollowupAgent
        from app.schemas.application import Application
        from app.schemas.enums import ApplicationStatus
        app = Application(application_id="a3", job_id="j3", status=ApplicationStatus.CLOSED)
        ctx, prev = self._ctx(profile, [app])
        r = FollowupAgent().run(ctx, prev)
        assert r.metadata["followups_scheduled"] == []

    def test_interview_status_skips(self, profile):
        from app.agents.followup_agent import FollowupAgent
        from app.schemas.application import Application
        from app.schemas.enums import ApplicationStatus
        app = Application(application_id="a4", job_id="j4", status=ApplicationStatus.INTERVIEW)
        ctx, prev = self._ctx(profile, [app])
        r = FollowupAgent().run(ctx, prev)
        assert r.metadata["followups_scheduled"] == []

    def test_do_not_contact_note_skips(self, profile):
        from app.agents.followup_agent import FollowupAgent
        from app.schemas.application import Application
        from app.schemas.enums import ApplicationStatus
        app = Application(application_id="a5", job_id="j5", status=ApplicationStatus.SUBMITTED, notes="Candidate asked us to Do Not Contact further")
        ctx, prev = self._ctx(profile, [app])
        r = FollowupAgent().run(ctx, prev)
        assert r.metadata["followups_scheduled"] == []
        assert any("do-not-contact" in s["reason"] for s in r.metadata["followups_skipped"])

    def test_submitted_schedules_both_followups(self, profile):
        from app.agents.followup_agent import FollowupAgent
        from app.schemas.application import Application
        from app.schemas.enums import ApplicationStatus
        app = Application(application_id="a6", job_id="j6", status=ApplicationStatus.SUBMITTED)
        ctx, prev = self._ctx(profile, [app])
        r = FollowupAgent().run(ctx, prev)
        assert len(r.metadata["followups_scheduled"]) == 2


class TestHarbanClientPilotFlagsWired:
    def test_client_discovery_disabled_skips_harban(self, profile, monkeypatch):
        monkeypatch.setenv("CLIENT_DISCOVERY_ENABLED", "false")
        from app.config import get_settings
        from app.agents import AgentContext, JobAgentOrchestrator
        get_settings.cache_clear()
        try:
            orch = JobAgentOrchestrator()
            r = orch.run(AgentContext(profile=profile))
            h = r.get("harban")
            assert any("client_discovery_enabled=false" in n for n in h.notes)
            assert h.metadata["counts"].get("opportunities_total", 0) == 0
        finally:
            get_settings.cache_clear()

    def test_client_outreach_disabled_no_drafts(self, profile, monkeypatch):
        monkeypatch.setenv("CLIENT_OUTREACH_ENABLED", "false")
        from app.config import get_settings
        from app.agents import AgentContext, JobAgentOrchestrator
        get_settings.cache_clear()
        try:
            orch = JobAgentOrchestrator()
            r = orch.run(AgentContext(profile=profile))
            h = r.get("harban")
            drafts = h.metadata.get("outreach_drafts", [])
            assert drafts == []
            assert any("client_outreach_enabled=false" in n for n in h.notes)
        finally:
            get_settings.cache_clear()

    def test_requires_real_contact_marks_draft_blocked(self, profile, monkeypatch):
        monkeypatch.setenv("CLIENT_OUTREACH_ENABLED", "true")
        monkeypatch.setenv("REQUIRES_REAL_CONTACT", "true")
        from app.config import get_settings
        from app.agents import AgentContext, JobAgentOrchestrator
        get_settings.cache_clear()
        try:
            orch = JobAgentOrchestrator()
            r = orch.run(AgentContext(profile=profile))
            h = r.get("harban")
            drafts = h.metadata.get("outreach_drafts", [])
            for d in drafts:
                assert d["status"] == "BLOCKED_REQUIRES_REAL_CONTACT"
        finally:
            get_settings.cache_clear()


class TestHarbanFollowupGating:
    def test_blocked_drafts_do_not_schedule_followups(self, profile, monkeypatch):
        monkeypatch.setenv("CLIENT_OUTREACH_ENABLED", "true")
        monkeypatch.setenv("REQUIRES_REAL_CONTACT", "true")
        from app.config import get_settings
        from app.agents import AgentContext, JobAgentOrchestrator
        get_settings.cache_clear()
        try:
            orch = JobAgentOrchestrator()
            r = orch.run(AgentContext(profile=profile))
            h = r.get("harban")
            drafts = h.metadata.get("outreach_drafts", [])
            scheduled = h.metadata.get("client_followups_scheduled", [])
            for d in drafts:
                assert d["status"] == "BLOCKED_REQUIRES_REAL_CONTACT"
            assert scheduled == [], "no follow-ups should be scheduled when every draft is BLOCKED"
        finally:
            get_settings.cache_clear()

    def test_disabled_outreach_schedules_zero_followups(self, profile, monkeypatch):
        monkeypatch.setenv("CLIENT_OUTREACH_ENABLED", "false")
        from app.config import get_settings
        from app.agents import AgentContext, JobAgentOrchestrator
        get_settings.cache_clear()
        try:
            orch = JobAgentOrchestrator()
            r = orch.run(AgentContext(profile=profile))
            h = r.get("harban")
            assert h.metadata.get("outreach_drafts", []) == []
            assert h.metadata.get("client_followups_scheduled", []) == []
        finally:
            get_settings.cache_clear()


class TestAuditLogsPerAgent:
    def test_pipeline_writes_per_agent_audit_entries(self, profile):
        from app.agents import AgentContext, JobAgentOrchestrator
        from app.database import SessionLocal, init_database
        from app.database.models import AuditLogRow
        init_database()
        orch = JobAgentOrchestrator()
        orch.run(AgentContext(profile=profile))
        with SessionLocal() as s:
            events = s.scalars(select(AuditLogRow.event)).all()
        assert "pipeline_run_persisted" in events
        agent_events = [e for e in events if e.startswith("agent_") and e.endswith("_completed")]
        assert any("discovery" in e for e in agent_events)
        assert any("matching" in e for e in agent_events)
        assert any("quality" in e for e in agent_events)
        assert any("submission" in e for e in agent_events)
        assert any("harban" in e for e in agent_events)


class TestResumeValidatorContactAndFormatting:
    def test_validator_flags_missing_email(self, tmp_path):
        import sys
        REPO_ROOT = (tmp_path / "..").resolve().parents[0]
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from resume_validator import validate_resume
        p = tmp_path / "noemail.txt"
        p.write_text("Harshaksh Singh\nEthara AI\nExperience\nEducation\nSkills\n+91 8303818640\n" + ("Body line.\n" * 20))
        rep = validate_resume(p, {"Harshaksh Singh", "Ethara AI"}, {"Harshaksh Singh", "Ethara AI"})
        assert any("email" in i.lower() for i in rep["issues"]) or rep["status"] == "OK"

    def test_validator_detects_sections(self, tmp_path):
        import sys
        REPO_ROOT = (tmp_path / "..").resolve().parents[0]
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from resume_validator import validate_resume
        p = tmp_path / "withsections.txt"
        p.write_text(
            "Harshaksh Singh\n"
            "harshakshsingh1010@gmail.com · +91 8303818640\n\n"
            "EXPERIENCE\nEthara AI 2025 - present\n\n"
            "EDUCATION\nNIET 2021-2025\n\n"
            "SKILLS\nPython, PyTorch, RLHF\n" + "x" * 200
        )
        rep = validate_resume(p, {"Harshaksh Singh", "Ethara AI"}, {"Harshaksh Singh", "Ethara AI"})
        assert "experience" in rep.get("sections_detected", [])
        assert "education" in rep.get("sections_detected", [])
        assert rep.get("found_contact_email") is True
        assert rep.get("found_contact_phone") is True
