from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.data.mock_jobs import build_mock_jobs
from app.llm.mock import MockLLMProvider
from app.profile import get_profile
from app.resumes.generator import ResumeGenerator, render_variant_text


class TestResumeGenerator:
    def test_render_all_variants(self, tmp_path):
        g = ResumeGenerator(output_dir=tmp_path)
        profile = get_profile()
        paths = g.render_all(profile)
        assert len(paths) >= 3
        for name, p in paths.items():
            assert p.exists()
            content = p.read_text()
            assert profile.full_name in content
            assert "EXPERIENCE" in content
            assert "SKILLS" in content
            assert "EDUCATION" in content
            assert "Ethara AI" in content

    def test_ensure_variant_creates_only_once(self, tmp_path):
        g = ResumeGenerator(output_dir=tmp_path)
        profile = get_profile()
        p1 = g.ensure_variant(profile, "ai_ml")
        assert p1 and p1.exists()
        mtime1 = p1.stat().st_mtime
        p2 = g.ensure_variant(profile, "ai_ml")
        assert p2 == p1
        assert p2.stat().st_mtime == mtime1

    def test_ensure_variant_returns_none_for_unknown(self, tmp_path):
        g = ResumeGenerator(output_dir=tmp_path)
        profile = get_profile()
        assert g.ensure_variant(profile, "nonexistent_variant") is None

    def test_render_includes_highlighted_skills(self, tmp_path):
        g = ResumeGenerator(output_dir=tmp_path)
        profile = get_profile()
        ai_ml = next(v for v in profile.resume_variants if v.name == "ai_ml")
        text = render_variant_text(profile, ai_ml)
        assert "Highlighted for this variant" in text
        for skill in ai_ml.highlighted_skills[:3]:
            assert skill in text

    def test_render_includes_projects_and_education(self, tmp_path):
        g = ResumeGenerator(output_dir=tmp_path)
        profile = get_profile()
        ai_ml = next(v for v in profile.resume_variants if v.name == "ai_ml")
        text = render_variant_text(profile, ai_ml)
        assert "PROJECTS" in text
        assert "Resume–JD Matcher" in text or "Resume" in text
        assert "Noida Institute" in text or "NIET" in text
        assert "Hindi" in text


class TestMockLLMProviderCoverage:
    def test_analyze_job_returns_signals(self, mock_jobs):
        p = MockLLMProvider()
        job = next(j for j in mock_jobs if j.source_job_id == "li-ai-ant-001")
        out = p.analyze_job(job)
        assert "keywords" in out
        assert "model" in out
        assert "python" in out["keywords"] or "llm" in out["keywords"]

    def test_score_job_returns_breakdown(self, mock_jobs, profile):
        p = MockLLMProvider()
        job = next(j for j in mock_jobs if j.source_job_id == "li-ai-ant-001")
        out = p.score_job(job, profile)
        assert "score_breakdown" in out
        assert "reasons" in out

    def test_generate_resume_rationale(self, mock_jobs, profile):
        p = MockLLMProvider()
        job = mock_jobs[0]
        text = p.generate_resume_rationale(job, profile, "ai_ml")
        assert "ai_ml" in text
        assert job.company in text

    def test_generate_cover_letter(self, mock_jobs, profile):
        p = MockLLMProvider()
        job = next(j for j in mock_jobs if j.source_job_id == "li-ai-ant-001")
        text = p.generate_cover_letter(job, profile)
        assert profile.full_name in text
        assert job.company in text

    def test_generate_email_includes_profile(self, mock_jobs, profile):
        p = MockLLMProvider()
        job = next(j for j in mock_jobs if j.source_job_id == "indie-ai-051")
        out = p.generate_email(job, profile, recipient="hr@x.co")
        assert out["subject"].startswith("Application")
        assert out["to"] == "hr@x.co"
        assert profile.full_name in out["body"]

    def test_answer_question_variants(self, mock_jobs, profile):
        p = MockLLMProvider()
        job = mock_jobs[0]
        name = p.answer_application_question("Full name", job, profile)
        assert name["answer"] == profile.full_name
        email = p.answer_application_question("Email", job, profile)
        assert email["answer"] == str(profile.email)
        phone = p.answer_application_question("Phone", job, profile)
        assert phone["answer"] == profile.phone
        loc = p.answer_application_question("Current location", job, profile)
        assert loc["answer"] == profile.location
        exp = p.answer_application_question("Years of experience", job, profile)
        assert exp["source"] == "DERIVED_FACT"
        skills = p.answer_application_question("Skills", job, profile)
        assert skills["source"] == "PROFILE_FACT"

    def test_answer_sensitive_question_requires_user_input(self, mock_jobs, profile):
        p = MockLLMProvider()
        job = mock_jobs[0]
        out = p.answer_application_question("What is your expected salary?", job, profile)
        assert out["requires_user_input"] is True
        assert out["source"] == "USER_INPUT_REQUIRED"

    def test_answer_unknown_question_requires_user_input(self, mock_jobs, profile):
        p = MockLLMProvider()
        job = mock_jobs[0]
        out = p.answer_application_question("What color is your car?", job, profile)
        assert out["answer"] is None
        assert out["source"] == "UNKNOWN"
        assert out["requires_user_input"] is True

    def test_detect_scam_delegates(self, mock_jobs):
        p = MockLLMProvider()
        scam = next(j for j in mock_jobs if j.source_job_id == "li-scam-031")
        out = p.detect_scam(scam)
        assert out["risk"] == "high"

    def test_deduplicate_jobs_returns_similarity(self, mock_jobs):
        p = MockLLMProvider()
        walmart = [j for j in mock_jobs if "walmart" in j.company.lower()]
        assert len(walmart) >= 2
        out = p.deduplicate_jobs(walmart[0], walmart[1])
        assert out["similarity"] >= 0.0
        assert "is_duplicate" in out


class TestLLMFactory:
    def test_default_returns_mock(self):
        from app.llm import get_llm_provider
        get_llm_provider.cache_clear()
        provider = get_llm_provider()
        assert provider.name == "mock"

    def test_openai_falls_back_to_mock_without_key(self, monkeypatch):
        from app.llm import get_llm_provider
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("MOCK_MODE", "false")
        from app.config import get_settings
        get_settings.cache_clear()
        get_llm_provider.cache_clear()
        try:
            provider = get_llm_provider()
            assert provider.name == "mock"
        finally:
            get_settings.cache_clear()
            get_llm_provider.cache_clear()

    def test_anthropic_falls_back_to_mock_without_key(self, monkeypatch):
        from app.llm import get_llm_provider
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("MOCK_MODE", "false")
        from app.config import get_settings
        get_settings.cache_clear()
        get_llm_provider.cache_clear()
        try:
            provider = get_llm_provider()
            assert provider.name == "mock"
        finally:
            get_settings.cache_clear()
            get_llm_provider.cache_clear()

    def test_gemini_falls_back_to_mock_without_key(self, monkeypatch):
        from app.llm import get_llm_provider
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.setenv("MOCK_MODE", "false")
        from app.config import get_settings
        get_settings.cache_clear()
        get_llm_provider.cache_clear()
        try:
            provider = get_llm_provider()
            assert provider.name == "mock"
        finally:
            get_settings.cache_clear()
            get_llm_provider.cache_clear()


class TestDiscoveryRegistry:
    def test_default_registry_only_mock(self, monkeypatch):
        from app.discovery.registry import get_registry, reset_registry_cache
        reset_registry_cache()
        try:
            reg = get_registry()
            names = [s.source_id.value for s in reg.all()]
            assert "mock" in names
            enabled = [s.source_id.value for s in reg.enabled()]
            assert enabled == ["mock"]
        finally:
            reset_registry_cache()

    def test_registry_adds_greenhouse_lever_ashby_when_enabled(self, monkeypatch):
        monkeypatch.setenv("MOCK_MODE", "false")
        monkeypatch.setenv("COMPANY_CAREERS_ENABLED", "true")
        from app.config import get_settings
        from app.discovery.registry import get_registry, reset_registry_cache
        get_settings.cache_clear()
        reset_registry_cache()
        try:
            reg = get_registry()
            all_sources = reg.all()
            assert len(all_sources) > 10, "should include many ATS sources when enabled"
            from app.discovery.sources.greenhouse import GreenhouseBoardSource
            from app.discovery.sources.lever import LeverCompanySource
            from app.discovery.sources.ashby import AshbyOrgSource
            assert any(isinstance(s, GreenhouseBoardSource) for s in all_sources)
            assert any(isinstance(s, LeverCompanySource) for s in all_sources)
            assert any(isinstance(s, AshbyOrgSource) for s in all_sources)
        finally:
            get_settings.cache_clear()
            reset_registry_cache()

    def test_registry_adds_remoteok_when_enabled(self, monkeypatch):
        monkeypatch.setenv("MOCK_MODE", "false")
        monkeypatch.setenv("REMOTEOK_ENABLED", "true")
        from app.config import get_settings
        from app.discovery.registry import get_registry, reset_registry_cache
        from app.discovery.sources.remoteok import RemoteOkSource
        get_settings.cache_clear()
        reset_registry_cache()
        try:
            reg = get_registry()
            assert any(isinstance(s, RemoteOkSource) for s in reg.all())
        finally:
            get_settings.cache_clear()
            reset_registry_cache()

    def test_registry_adds_weworkremotely_when_enabled(self, monkeypatch):
        monkeypatch.setenv("MOCK_MODE", "false")
        monkeypatch.setenv("WEWORKREMOTELY_ENABLED", "true")
        from app.config import get_settings
        from app.discovery.registry import get_registry, reset_registry_cache
        from app.discovery.sources.weworkremotely import WeWorkRemotelySource
        get_settings.cache_clear()
        reset_registry_cache()
        try:
            reg = get_registry()
            assert any(isinstance(s, WeWorkRemotelySource) for s in reg.all())
        finally:
            get_settings.cache_clear()
            reset_registry_cache()

    def test_registry_adds_hackernews_when_enabled(self, monkeypatch):
        monkeypatch.setenv("MOCK_MODE", "false")
        monkeypatch.setenv("HACKERNEWS_ENABLED", "true")
        from app.config import get_settings
        from app.discovery.registry import get_registry, reset_registry_cache
        from app.discovery.sources.hackernews import HackerNewsWhoIsHiringSource
        get_settings.cache_clear()
        reset_registry_cache()
        try:
            reg = get_registry()
            hn_sources = [s for s in reg.all() if isinstance(s, HackerNewsWhoIsHiringSource)]
            assert len(hn_sources) == 1
            assert hn_sources[0].is_enabled() is True
        finally:
            get_settings.cache_clear()
            reset_registry_cache()

    def test_registry_adds_google_search_when_enabled(self, monkeypatch):
        monkeypatch.setenv("MOCK_MODE", "false")
        monkeypatch.setenv("GOOGLE_SEARCH_ENABLED", "true")
        from app.config import get_settings
        from app.discovery.registry import get_registry, reset_registry_cache
        from app.discovery.sources.google_search import GoogleProgrammableSearchSource
        get_settings.cache_clear()
        reset_registry_cache()
        try:
            reg = get_registry()
            assert any(isinstance(s, GoogleProgrammableSearchSource) for s in reg.all())
        finally:
            get_settings.cache_clear()
            reset_registry_cache()

    def test_registry_adds_linkedin_stub_when_enabled(self, monkeypatch):
        monkeypatch.setenv("MOCK_MODE", "false")
        monkeypatch.setenv("LINKEDIN_ENABLED", "true")
        from app.config import get_settings
        from app.discovery.registry import get_registry, reset_registry_cache
        from app.discovery.sources.linkedin import LinkedInSource
        get_settings.cache_clear()
        reset_registry_cache()
        try:
            reg = get_registry()
            assert any(isinstance(s, LinkedInSource) for s in reg.all())
        finally:
            get_settings.cache_clear()
            reset_registry_cache()

    def test_by_type_returns_matching_sources(self):
        from app.discovery.registry import get_registry, reset_registry_cache
        from app.schemas.enums import JobSource
        reset_registry_cache()
        try:
            reg = get_registry()
            mocks = reg.by_type(JobSource.MOCK)
            assert len(mocks) == 1
        finally:
            reset_registry_cache()


class TestFSMAdditionalInvariants:
    def test_offer_cannot_go_back_to_submitted(self):
        from app.applications.tracker import ApplicationTracker, InvalidStatusTransition
        from app.schemas.enums import ApplicationStatus
        from app.schemas.application import Application
        app = Application(application_id="app_x", job_id="j_x", status=ApplicationStatus.DISCOVERED)
        t = ApplicationTracker()
        for s in [
            ApplicationStatus.MATCHED,
            ApplicationStatus.APPROVED,
            ApplicationStatus.APPLICATION_PREPARED,
            ApplicationStatus.AWAITING_USER,
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.OFFER,
        ]:
            t.transition(app, s)
        with pytest.raises(InvalidStatusTransition):
            t.transition(app, ApplicationStatus.SUBMITTED)

    def test_offer_can_only_terminate(self):
        from app.schemas.enums import ApplicationStatus, is_valid_transition
        assert is_valid_transition(ApplicationStatus.OFFER, ApplicationStatus.WITHDRAWN)
        assert is_valid_transition(ApplicationStatus.OFFER, ApplicationStatus.REJECTED)
        assert not is_valid_transition(ApplicationStatus.OFFER, ApplicationStatus.SUBMITTED)
        assert not is_valid_transition(ApplicationStatus.OFFER, ApplicationStatus.INTERVIEW)
        assert not is_valid_transition(ApplicationStatus.OFFER, ApplicationStatus.MATCHED)


class TestCLINonInteractive:
    def test_cli_non_interactive_runs_pipeline(self, profile, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/x.db")
        from app.cli import run_cli
        rc = run_cli(["--non-interactive"])
        assert rc == 0

    def test_cli_dashboard_mode(self, profile, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/x.db")
        from app.cli import run_cli
        rc = run_cli(["--dashboard"])
        assert rc == 0

    def test_cli_daily_report(self, profile, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/x.db")
        from app.cli import run_cli
        rc = run_cli(["--daily-report"])
        assert rc == 0

    def test_cli_weekly_analytics(self, profile, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/x.db")
        from app.cli import run_cli
        rc = run_cli(["--weekly-analytics"])
        assert rc == 0


class TestAnalyticsReports:
    def test_weekly_zero_apps_handles_division(self):
        from app.analytics import build_weekly_analytics
        w = build_weekly_analytics(0, 0, 0, 0)
        assert w.response_rate == 0.0
        assert w.interview_rate == 0.0

    def test_weekly_high_response_rate_recommendation(self):
        from app.analytics import build_weekly_analytics
        w = build_weekly_analytics(10, 3, 1, 0)
        assert "strong" in w.recommendation.lower() or "moderate" in w.recommendation.lower()

    def test_weekly_low_response_rate_recommendation(self):
        from app.analytics import build_weekly_analytics
        w = build_weekly_analytics(100, 1, 0, 0)
        assert "<5" in w.recommendation or "threshold" in w.recommendation.lower() or "cover" in w.recommendation.lower()
