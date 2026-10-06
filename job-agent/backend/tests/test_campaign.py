from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from app.campaign.orchestrator import (
    CampaignConfig,
    CampaignOrchestrator,
    CampaignResult,
    CampaignStrategy,
    classify_outcome,
    compute_idempotency_key,
)
from app.campaign.report import format_campaign_report


class TestClassifyOutcome:
    def test_submitted_live_is_confirmed(self):
        assert classify_outcome("SUBMITTED_LIVE") == "confirmed"
        assert classify_outcome("SUBMITTED_CONFIRMED") == "confirmed"

    def test_simulated_dry_run(self):
        assert classify_outcome("SIMULATED_SUBMIT_DRY_RUN") == "simulated_dry_run"

    def test_security_blocked_variants(self):
        assert classify_outcome("BLOCKED_HARD_STOP") == "blocked_security"
        assert classify_outcome("BLOCKED_SECURITY_BLOCKED") == "blocked_security"
        assert classify_outcome("APPLICATION_BLOCKED_USER_ACTION") == "blocked_security"

    def test_legal_blocked(self):
        assert classify_outcome("BLOCKED_LEGAL_BLOCKED") == "blocked_legal"

    def test_requires_user_data(self):
        assert classify_outcome("BLOCKED_REQUIRES_USER_DATA") == "requires_user_data"
        assert classify_outcome("AWAITING_USER_CONFIRMATION") == "requires_user_data"
        assert classify_outcome("AWAITING_AUTO_SUBMIT_FLAG") == "requires_user_data"

    def test_skipped_idempotent(self):
        assert classify_outcome("SKIPPED_IDEMPOTENT") == "skipped_idempotent"

    def test_unknown_is_failed(self):
        assert classify_outcome("WEIRD_UNKNOWN_STATE") == "failed"

    def test_rejected_by_eligibility(self):
        assert classify_outcome("REJECTED_BY_ELIGIBILITY") == "rejected"
        assert classify_outcome("DRY_RUN_PREPARED") == "rejected"

    def test_infra_blocked(self):
        assert classify_outcome("SUBMITTED_PLACEHOLDER_REQUIRES_BROWSER") == "infra_blocked"


class TestIdempotencyKey:
    def test_deterministic_same_inputs(self):
        k1 = compute_idempotency_key("app_1", "job_1")
        k2 = compute_idempotency_key("app_1", "job_1")
        assert k1 == k2

    def test_different_apps_different_keys(self):
        k1 = compute_idempotency_key("app_1", "job_1")
        k2 = compute_idempotency_key("app_2", "job_1")
        assert k1 != k2

    def test_different_jobs_different_keys(self):
        k1 = compute_idempotency_key("app_1", "job_1")
        k2 = compute_idempotency_key("app_1", "job_2")
        assert k1 != k2

    def test_channel_affects_key(self):
        k_live = compute_idempotency_key("app_1", "job_1", channel="live_submit")
        k_dry = compute_idempotency_key("app_1", "job_1", channel="dry_run")
        assert k_live != k_dry

    def test_key_length_is_bounded(self):
        k = compute_idempotency_key("app_1", "job_1")
        assert len(k) == 48


class TestDryRunPropagation:
    def test_dry_run_sets_dry_run_env_during_pipeline(self):
        import os
        from unittest.mock import MagicMock
        from app.campaign.orchestrator import CampaignConfig, CampaignOrchestrator

        observed = {"dry_run_in_env": None, "auto_submit_in_env": None}

        def inspecting_runner(profile):
            observed["dry_run_in_env"] = os.environ.get("DRY_RUN")
            observed["auto_submit_in_env"] = os.environ.get("AUTO_SUBMIT_APPROVED")
            sub = MagicMock()
            sub.metadata = {"outcomes": []}
            result = MagicMock()
            result.matched_jobs = []
            result.get = lambda key: sub if key == "submission" else None
            return result

        prev_dry = os.environ.get("DRY_RUN")
        prev_auto = os.environ.get("AUTO_SUBMIT_APPROVED")
        try:
            if "DRY_RUN" in os.environ:
                del os.environ["DRY_RUN"]
            if "AUTO_SUBMIT_APPROVED" in os.environ:
                del os.environ["AUTO_SUBMIT_APPROVED"]
            cfg = CampaignConfig(target_confirmed=1, dry_run=True)
            CampaignOrchestrator(pipeline_runner=inspecting_runner).run(cfg, profile=None)
            assert observed["dry_run_in_env"] == "true", (
                f"Expected DRY_RUN=true during pipeline execution, got {observed['dry_run_in_env']!r}"
            )
            assert observed["auto_submit_in_env"] == "false"
        finally:
            if prev_dry is None:
                os.environ.pop("DRY_RUN", None)
            else:
                os.environ["DRY_RUN"] = prev_dry
            if prev_auto is None:
                os.environ.pop("AUTO_SUBMIT_APPROVED", None)
            else:
                os.environ["AUTO_SUBMIT_APPROVED"] = prev_auto

    def test_env_restored_after_run(self):
        import os
        from unittest.mock import MagicMock
        from app.campaign.orchestrator import CampaignConfig, CampaignOrchestrator

        def nop_runner(profile):
            sub = MagicMock()
            sub.metadata = {"outcomes": []}
            result = MagicMock()
            result.matched_jobs = []
            result.get = lambda key: sub if key == "submission" else None
            return result

        os.environ["DRY_RUN"] = "false"
        try:
            cfg = CampaignConfig(target_confirmed=1, dry_run=True)
            CampaignOrchestrator(pipeline_runner=nop_runner).run(cfg, profile=None)
            assert os.environ.get("DRY_RUN") == "false", "env must be restored after campaign.run()"
        finally:
            os.environ.pop("DRY_RUN", None)


class TestCampaignOrchestrator:
    def _fake_pipeline(self, outcomes: list[dict]):
        def _runner(profile):
            sub = MagicMock()
            sub.metadata = {"outcomes": outcomes}
            result = MagicMock()
            result.matched_jobs = [MagicMock() for _ in range(len(outcomes))]
            result.get = lambda key: sub if key == "submission" else None
            return result
        return _runner

    def test_campaign_counts_confirmed(self):
        outcomes = [
            {"outcome": "SUBMITTED_LIVE", "application_id": "a1", "job_id": "j1"},
            {"outcome": "SUBMITTED_LIVE", "application_id": "a2", "job_id": "j2"},
            {"outcome": "APPLICATION_BLOCKED_USER_ACTION", "application_id": "a3", "job_id": "j3"},
        ]
        orch = CampaignOrchestrator(pipeline_runner=self._fake_pipeline(outcomes))
        cfg = CampaignConfig(target_confirmed=10, dry_run=False)
        result = orch.run(cfg, profile=None)
        assert result.attempted == 3
        assert result.confirmed == 2
        assert result.blocked_security == 1
        assert result.is_target_reached() is False

    def test_dry_run_counts_simulated(self):
        outcomes = [
            {"outcome": "SIMULATED_SUBMIT_DRY_RUN", "application_id": f"a{i}", "job_id": f"j{i}"}
            for i in range(10)
        ]
        orch = CampaignOrchestrator(pipeline_runner=self._fake_pipeline(outcomes))
        cfg = CampaignConfig(target_confirmed=10, dry_run=True)
        result = orch.run(cfg, profile=None)
        assert result.simulated_dry_run == 10
        assert result.confirmed == 0
        assert result.is_target_reached() is True

    def test_blockers_do_not_stop_campaign(self):
        outcomes = [
            {"outcome": "SUBMITTED_LIVE", "application_id": "a1", "job_id": "j1"},
            {"outcome": "APPLICATION_BLOCKED_USER_ACTION", "application_id": "a2", "job_id": "j2"},
            {"outcome": "BLOCKED_LEGAL_BLOCKED", "application_id": "a3", "job_id": "j3"},
            {"outcome": "BLOCKED_REQUIRES_USER_DATA", "application_id": "a4", "job_id": "j4"},
            {"outcome": "SUBMITTED_LIVE", "application_id": "a5", "job_id": "j5"},
            {"outcome": "SUBMITTED_LIVE", "application_id": "a6", "job_id": "j6"},
        ]
        orch = CampaignOrchestrator(pipeline_runner=self._fake_pipeline(outcomes))
        cfg = CampaignConfig(target_confirmed=3, dry_run=False)
        result = orch.run(cfg, profile=None)
        assert result.attempted == 6
        assert result.confirmed == 3
        assert result.blocked_security == 1
        assert result.blocked_legal == 1
        assert result.requires_user_data == 1
        assert result.is_target_reached() is True

    def test_pipeline_fatal_error_captured(self):
        def broken_runner(profile):
            raise RuntimeError("boom")
        orch = CampaignOrchestrator(pipeline_runner=broken_runner)
        cfg = CampaignConfig(target_confirmed=10)
        result = orch.run(cfg, profile=None)
        assert any("pipeline_fatal" in e for e in result.errors)
        assert result.is_target_reached() is False

    def test_report_renders_without_crash(self):
        outcomes = [
            {"outcome": "SIMULATED_SUBMIT_DRY_RUN", "application_id": "a1", "job_id": "j1"},
        ]
        orch = CampaignOrchestrator(pipeline_runner=self._fake_pipeline(outcomes))
        cfg = CampaignConfig(target_confirmed=1, dry_run=True, strategy=CampaignStrategy.TOP_LATEST)
        result = orch.run(cfg, profile=None)
        report = format_campaign_report(result)
        assert "PORTOLAN APPLICATION CAMPAIGN" in report
        assert "TARGET REACHED" in report
        assert "DRY-RUN" in report
