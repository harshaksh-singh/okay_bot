from __future__ import annotations

import pytest


class TestStubsWiredIntoPipeline:
    def test_indeed_stub_runs_in_discovery_when_enabled(self, monkeypatch):
        from app.agents.base import AgentContext
        from app.agents.discovery_agent import DiscoveryAgent
        from app.config import get_settings
        from app.discovery.registry import reset_registry_cache
        from app.profile import get_profile

        monkeypatch.setenv("MOCK_MODE", "false")
        monkeypatch.setenv("INDEED_ENABLED", "true")
        get_settings.cache_clear()
        reset_registry_cache()
        try:
            agent = DiscoveryAgent()
            ctx = AgentContext(profile=get_profile())
            result = agent.run(ctx, [])
            assert any("indeed" in err.lower() and ("tos" in err.lower() or "assisted" in err.lower()) for err in result.errors)
            assert "indeed" in result.metadata["sources_run"]
        finally:
            get_settings.cache_clear()
            reset_registry_cache()

    def test_linkedin_stub_runs_in_discovery_when_enabled(self, monkeypatch):
        from app.agents.base import AgentContext
        from app.agents.discovery_agent import DiscoveryAgent
        from app.config import get_settings
        from app.discovery.registry import reset_registry_cache
        from app.profile import get_profile

        monkeypatch.setenv("MOCK_MODE", "false")
        monkeypatch.setenv("LINKEDIN_ENABLED", "true")
        get_settings.cache_clear()
        reset_registry_cache()
        try:
            agent = DiscoveryAgent()
            result = agent.run(AgentContext(profile=get_profile()), [])
            assert "linkedin" in result.metadata["sources_run"]
            assert any(
                "linkedin" in err.lower() and (
                    "logs in" in err.lower()
                    or "logged" in err.lower()
                    or "sign in" in err.lower()
                    or "session not configured" in err.lower()
                    or "not implemented" in err.lower()
                )
                for err in result.errors
            )
        finally:
            get_settings.cache_clear()
            reset_registry_cache()

    def test_wellfound_stub_runs_when_enabled(self, monkeypatch):
        from app.agents.base import AgentContext
        from app.agents.discovery_agent import DiscoveryAgent
        from app.config import get_settings
        from app.discovery.registry import reset_registry_cache
        from app.profile import get_profile

        monkeypatch.setenv("MOCK_MODE", "false")
        monkeypatch.setenv("WELLFOUND_ENABLED", "true")
        get_settings.cache_clear()
        reset_registry_cache()
        try:
            agent = DiscoveryAgent()
            result = agent.run(AgentContext(profile=get_profile()), [])
            assert any("wellfound" in err.lower() for err in result.errors)
        finally:
            get_settings.cache_clear()
            reset_registry_cache()

    def test_stub_disabled_by_default_is_skipped(self, monkeypatch):
        from app.agents.base import AgentContext
        from app.agents.discovery_agent import DiscoveryAgent
        from app.config import get_settings
        from app.discovery.registry import reset_registry_cache
        from app.profile import get_profile

        monkeypatch.delenv("GLASSDOOR_ENABLED", raising=False)
        get_settings.cache_clear()
        reset_registry_cache()
        try:
            result = DiscoveryAgent().run(AgentContext(profile=get_profile()), [])
            assert not any("glassdoor" in s.lower() for s in result.metadata["sources_run"])
        finally:
            get_settings.cache_clear()
            reset_registry_cache()


class TestFormMapperFactTagCoverage:
    def _answers(self, profile, mock_jobs):
        from app.applications.form_mapper import FormFieldMapper
        job = mock_jobs[0]
        return FormFieldMapper().map(job, profile)

    def test_emits_job_fact_tag(self, profile, mock_jobs):
        tags = {a.source_tag for a in self._answers(profile, mock_jobs)}
        assert "JOB_FACT" in tags

    def test_emits_profile_fact_tag(self, profile, mock_jobs):
        tags = {a.source_tag for a in self._answers(profile, mock_jobs)}
        assert "PROFILE_FACT" in tags

    def test_emits_derived_fact_tag(self, profile, mock_jobs):
        tags = {a.source_tag for a in self._answers(profile, mock_jobs)}
        assert "DERIVED_FACT" in tags

    def test_emits_user_input_required_tag(self, profile, mock_jobs):
        tags = {a.source_tag for a in self._answers(profile, mock_jobs)}
        assert "USER_INPUT_REQUIRED" in tags

    def test_emits_user_provided_fact_when_availability_set(self, profile, mock_jobs):
        from datetime import date
        from app.applications.form_mapper import FormFieldMapper
        profile.availability.notice_period_weeks = 4
        profile.availability.earliest_start = date(2026, 11, 1)
        answers = FormFieldMapper().map(mock_jobs[0], profile)
        tags = {a.source_tag for a in answers}
        assert "USER_PROVIDED_FACT" in tags
        profile.availability.notice_period_weeks = None
        profile.availability.earliest_start = None

    def test_job_role_canonical_field_present(self, profile, mock_jobs):
        answers = self._answers(profile, mock_jobs)
        role_answer = next((a for a in answers if a.field_name == "job_role_canonical"), None)
        assert role_answer is not None
        assert role_answer.source_tag == "JOB_FACT"
        assert role_answer.answer == mock_jobs[0].title

    def test_all_four_tiers_of_fact_sources_represented(self, profile, mock_jobs):
        from datetime import date
        from app.applications.form_mapper import FormFieldMapper
        profile.availability.notice_period_weeks = 4
        profile.availability.earliest_start = date(2026, 11, 1)
        answers = FormFieldMapper().map(mock_jobs[0], profile)
        tags = {a.source_tag for a in answers}
        required = {"PROFILE_FACT", "JOB_FACT", "USER_PROVIDED_FACT", "DERIVED_FACT", "USER_INPUT_REQUIRED"}
        assert required.issubset(tags), f"missing tiers: {required - tags}"
        profile.availability.notice_period_weeks = None
        profile.availability.earliest_start = None
