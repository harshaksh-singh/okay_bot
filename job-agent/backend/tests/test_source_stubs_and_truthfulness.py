from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import select


class TestExpandedSourceStubs:
    def _registry_with(self, monkeypatch, **flags):
        from app.config import get_settings
        from app.discovery.registry import get_registry, reset_registry_cache
        monkeypatch.setenv("MOCK_MODE", "false")
        for k, v in flags.items():
            monkeypatch.setenv(k.upper(), "true" if v else "false")
        get_settings.cache_clear()
        reset_registry_cache()
        return get_registry()

    def test_glassdoor_stub_registers_when_enabled(self, monkeypatch):
        from app.discovery.sources._common_stub import GlassdoorStub
        reg = self._registry_with(monkeypatch, glassdoor_enabled=True)
        assert any(isinstance(s, GlassdoorStub) for s in reg.all())

    def test_wellfound_stub_registers_when_enabled(self, monkeypatch):
        from app.discovery.sources._common_stub import WellfoundStub
        reg = self._registry_with(monkeypatch, wellfound_enabled=True)
        assert any(isinstance(s, WellfoundStub) for s in reg.all())

    def test_handshake_stub_registers_when_enabled(self, monkeypatch):
        from app.discovery.sources._common_stub import HandshakeStub
        reg = self._registry_with(monkeypatch, handshake_enabled=True)
        assert any(isinstance(s, HandshakeStub) for s in reg.all())

    def test_cutshort_instahyre_hirist_foundit_internshala_register(self, monkeypatch):
        from app.discovery.sources._common_stub import (
            CutshortStub, InstahyreStub, HiristStub, FounditStub, InternshalaStub,
        )
        for cls_name, flag_name in [
            ("cutshort_enabled", "cutshort_enabled"),
            ("instahyre_enabled", "instahyre_enabled"),
            ("hirist_enabled", "hirist_enabled"),
            ("foundit_enabled", "foundit_enabled"),
            ("internshala_enabled", "internshala_enabled"),
        ]:
            reg = self._registry_with(monkeypatch, **{flag_name: True})
            all_sources = reg.all()
            assert any(getattr(s, "phase2_notice", None) and "assisted" in s.phase2_notice.lower() for s in all_sources if hasattr(s, "phase2_notice"))

    def test_outlier_surge_telus_register(self, monkeypatch):
        from app.discovery.sources._common_stub import OutlierStub, SurgeAiStub, TelusDigitalAiStub
        reg = self._registry_with(monkeypatch, outlier_enabled=True, surge_ai_enabled=True, telus_digital_ai_enabled=True)
        all_srcs = reg.all()
        assert any(isinstance(s, OutlierStub) for s in all_srcs)
        assert any(isinstance(s, SurgeAiStub) for s in all_srcs)
        assert any(isinstance(s, TelusDigitalAiStub) for s in all_srcs)

    def test_all_stubs_discover_returns_informative_error(self, monkeypatch):
        from app.discovery.base import SourceContext
        from app.discovery.sources._common_stub import (
            GlassdoorStub, WellfoundStub, CutshortStub, InstahyreStub,
            HiristStub, FounditStub, InternshalaStub, OutlierStub, SurgeAiStub, TelusDigitalAiStub,
        )
        ctx = SourceContext()
        for cls in [GlassdoorStub, WellfoundStub, CutshortStub, InstahyreStub,
                    HiristStub, FounditStub, InternshalaStub, OutlierStub, SurgeAiStub, TelusDigitalAiStub]:
            inst = cls()
            r = inst.discover(ctx)
            assert len(r.errors) == 1
            assert any(k in r.errors[0].lower() for k in ("tos", "logged-in", "assisted", "no public"))


class TestQualityAgentFactChecks:
    def _make_app_with_text(self, text: str):
        from app.schemas.application import Application
        from app.schemas.enums import ApplicationStatus
        return Application(
            application_id="app_quality_test",
            job_id="job_q",
            status=ApplicationStatus.MATCHED,
            cover_letter_text=text,
        )

    def _run_quality_only(self, profile, applications, previous_jobs=None):
        from app.agents.base import AgentContext, AgentResult
        from app.agents.quality_agent import QualityAgent
        prev = []
        app_result = AgentResult(agent="application")
        app_result.metadata["applications"] = applications
        prev.append(app_result)
        if previous_jobs is not None:
            matching = AgentResult(agent="matching", jobs=previous_jobs)
            prev.append(matching)
        ctx = AgentContext(profile=profile)
        return QualityAgent().run(ctx, prev)

    def test_detects_fabricated_phd_claim(self, profile):
        app = self._make_app_with_text(
            "I hold a PhD in Machine Learning from Stanford."
        )
        r = self._run_quality_only(profile, [app])
        issues = r.metadata["quality_issues"]
        assert any("PhD" in i["issue"] for i in issues)
        assert any("Stanford" in i["issue"] for i in issues)

    def test_detects_fabricated_mba(self, profile):
        app = self._make_app_with_text("I have an MBA from Harvard.")
        r = self._run_quality_only(profile, [app])
        issues = r.metadata["quality_issues"]
        assert any("MBA" in i["issue"] for i in issues)

    def test_detects_forbidden_year_claims(self, profile):
        app = self._make_app_with_text(
            "I have been working since 2005 as a Principal Engineer."
        )
        r = self._run_quality_only(profile, [app])
        issues = r.metadata["quality_issues"]
        assert any("principal" in i["issue"].lower() for i in issues)

    def test_detects_suspicious_year_ranges(self, profile):
        app_old = self._make_app_with_text("I have been coding since 1985.")
        r = self._run_quality_only(profile, [app_old])
        issues = r.metadata["quality_issues"]
        assert any("1985" in i["issue"] and "old" in i["issue"] for i in issues)

        app_future = self._make_app_with_text("I plan to retire in 2040.")
        r2 = self._run_quality_only(profile, [app_future])
        issues2 = r2.metadata["quality_issues"]
        assert any("2040" in i["issue"] and "future" in i["issue"] for i in issues2)

    def test_detects_salary_claim_in_cover_letter(self, profile):
        app = self._make_app_with_text(
            "I expect $200,000 per year for this role."
        )
        r = self._run_quality_only(profile, [app])
        issues = r.metadata["quality_issues"]
        assert any("salary" in i["issue"].lower() for i in issues)

    def test_detects_visa_claims(self, profile):
        app = self._make_app_with_text("I am a US Citizen with a green card.")
        r = self._run_quality_only(profile, [app])
        issues = r.metadata["quality_issues"]
        assert any("us citizen" in i["issue"].lower() for i in issues)
        assert any("green card" in i["issue"].lower() for i in issues)

    def test_truthful_cover_letter_produces_no_fact_issues(self, profile):
        app = self._make_app_with_text(
            "Hi, I am Harshaksh Singh currently at Ethara AI working on LLM fine-tuning. "
            "My B.Tech is from Noida Institute of Engineering & Technology. "
            "I am available part-time."
        )
        r = self._run_quality_only(profile, [app])
        issues = r.metadata["quality_issues"]
        bad = [i for i in issues if any(k in i["issue"].lower() for k in ("fabricated", "phd", "mba", "citizen", "salary", "stanford"))]
        assert bad == []


class TestInterviewTracking:
    def test_mark_interview_creates_interview_row(self, profile):
        from sqlalchemy import select
        from app.applications.tracker import ApplicationTracker
        from app.database import SessionLocal, init_database
        from app.database.models import ApplicationRow, InterviewRow, JobRow
        from app.schemas.application import Application
        from app.schemas.enums import ApplicationStatus

        init_database()
        with SessionLocal() as s:
            if not s.scalars(select(JobRow).where(JobRow.job_id == "iv_job_1")).first():
                s.add(JobRow(job_id="iv_job_1", source="mock", company_name="X", title="Y"))
            if not s.scalars(select(ApplicationRow).where(ApplicationRow.application_id == "app_iv_1")).first():
                s.add(ApplicationRow(application_id="app_iv_1", job_id="iv_job_1", status="SUBMITTED"))
            s.commit()
            before = len(s.scalars(select(InterviewRow)).all())

        app = Application(application_id="app_iv_1", job_id="iv_job_1", status=ApplicationStatus.SUBMITTED)
        tracker = ApplicationTracker()
        tracker.mark_interview(app, note="first round", round_name="technical", interviewer="Jane Doe")
        assert app.status == ApplicationStatus.INTERVIEW

        with SessionLocal() as s:
            interviews = s.scalars(select(InterviewRow)).all()
        assert len(interviews) == before + 1
        latest = interviews[-1]
        assert latest.round_name == "technical"
        assert latest.interviewer == "Jane Doe"


class TestInterviewsAPI:
    def test_interviews_endpoint_exists(self):
        from fastapi.testclient import TestClient
        from app.api import create_app
        app = create_app()
        with TestClient(app) as c:
            r = c.get("/interviews")
            assert r.status_code == 200
            assert isinstance(r.json(), list)
