from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestEnvProductionExample:
    def test_production_env_example_exists_and_safe(self):
        p = REPO_ROOT / ".env.production.example"
        assert p.exists()
        content = p.read_text()
        for pat in (
            "PRE_APPROVED_APPLICATIONS=false",
            "AUTO_SUBMIT_APPROVED=false",
            "AUTO_EMAIL_APPROVED=false",
            "COMPLIANCE_HARD_BLOCK=true",
            "TRUTHFULNESS_HARD_BLOCK=true",
            "CAPTCHA_BYPASS=false",
            "MFA_BYPASS=false",
            "OTP_BYPASS=false",
            "RATE_LIMIT_BYPASS=false",
            "REQUIRES_REAL_CONTACT=true",
            "DISCOVERY_PILOT_MODE=true",
        ):
            assert pat in content, f"missing production invariant: {pat}"


class TestSecretScanner:
    def test_scanner_clean_on_this_repo(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from secret_scan import scan
        hits = scan(REPO_ROOT)
        hits.pop("_meta", None)
        for kind, matches in hits.items():
            assert matches == [], f"found suspected {kind}: {matches[:3]}"

    def test_scanner_catches_planted_secret(self, tmp_path):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from secret_scan import scan
        bad = tmp_path / "prod_config.py"
        bad.write_text('token = "sk-Zbfnvdqpr8kK3mXfLq2eYvQwRtNu9JxVgPkCwDsEhHJ"\n')
        hits = scan(tmp_path)
        hits.pop("_meta", None)
        assert any(matches for kind, matches in hits.items())


class TestGitSecurityCheck:
    def test_gitignore_covers_required_patterns(self):
        gi = (REPO_ROOT / ".gitignore").read_text()
        for pat in [".env", "browser/", "data/*.db"]:
            assert pat in gi


class TestDbBackupRestore:
    def test_backup_restore_check_cycle(self, tmp_path):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from db_backup import backup, check, restore

        source_db = tmp_path / "src.db"
        con = sqlite3.connect(source_db)
        cur = con.cursor()
        cur.execute("CREATE TABLE jobs (job_id TEXT, title TEXT)")
        cur.execute("INSERT INTO jobs VALUES ('j1', 'AI Engineer')")
        con.commit()
        con.close()

        backup_dir = tmp_path / "backups"
        dest = backup(source_db, backup_dir)
        assert dest.exists()
        manifest_path = dest.with_suffix(".manifest.json")
        assert manifest_path.exists()

        target = tmp_path / "restored.db"
        restore(dest, target)
        assert target.exists()
        result = check(target)
        assert result["integrity"] == "ok"
        assert "jobs" in result["row_counts"]

    def test_check_detects_credential_column(self, tmp_path):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from db_backup import check

        db = tmp_path / "bad.db"
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("CREATE TABLE users (id INTEGER, password TEXT)")
        con.commit()
        con.close()
        result = check(db)
        assert "users.password" in result["credential_columns_detected"]


class TestDiscoveryPilotCaps:
    def test_pilot_mode_caps_discovery_limit(self, profile, monkeypatch):
        from app.agents import AgentContext
        from app.agents.discovery_agent import DiscoveryAgent

        monkeypatch.setenv("DISCOVERY_PILOT_MODE", "true")
        monkeypatch.setenv("DISCOVERY_PILOT_MAX_PER_SOURCE", "5")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            ctx = AgentContext(profile=profile, limit_per_source=None)
            r = DiscoveryAgent().run(ctx, [])
            assert len(r.jobs) <= 5
            assert any("pilot_mode" in n.lower() for n in r.notes)
        finally:
            get_settings.cache_clear()


class TestHttpCircuitBreaker:
    def test_circuit_opens_after_threshold_failures(self):
        from app.discovery.http_client import HttpClient
        client = HttpClient(circuit_failure_threshold=3, circuit_cooldown_seconds=60, respect_robots=False, max_retries=0)
        for _ in range(3):
            client._record_failure("flaky.local")
        assert client._circuit_open("flaky.local")

    def test_circuit_status_report(self):
        from app.discovery.http_client import HttpClient
        client = HttpClient(circuit_failure_threshold=2, circuit_cooldown_seconds=60, respect_robots=False, max_retries=0)
        client._record_failure("a.example")
        client._record_failure("a.example")
        client._record_failure("b.example")
        status = client.circuit_status()
        assert status["a.example"]["open"] is True
        assert status["b.example"]["open"] is False


class TestOTPBypassRejected:
    def test_otp_bypass_true_raises_compliance_violation(self, monkeypatch):
        from app.agents.compliance_agent import ComplianceAgent
        from app.agents.base import AgentContext
        from app.compliance import ComplianceViolation
        from app.config import Settings
        from app.profile import get_profile
        from unittest.mock import patch

        with patch("app.agents.compliance_agent.get_settings") as m:
            m.return_value = Settings(otp_bypass=True)
            agent = ComplianceAgent()
            with pytest.raises(ComplianceViolation) as exc:
                agent.run(AgentContext(profile=get_profile()), [])
            assert any("OTP_BYPASS" in v for v in exc.value.violations)


class TestProductionDailyReport:
    def test_production_daily_report_renders_three_sections(self, profile):
        from app.agents import AgentContext, JobAgentOrchestrator
        from app.analytics import build_production_daily_report

        orch = JobAgentOrchestrator()
        result = orch.run(AgentContext(profile=profile))
        rep = build_production_daily_report(result)
        text = rep.render()
        assert "PRODUCTION DAILY REPORT" in text
        assert "CAREER" in text
        assert "HARBAN" in text
        assert "OPPORTUNITY ROUTER" in text
        assert "SYSTEM" in text


class TestResumeValidator:
    def test_validator_runs_against_generated_resumes(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from resume_validator import validate_resume
        gen = REPO_ROOT / "data" / "resumes_generated" / "resume_ai_ml.txt"
        if not gen.exists():
            pytest.skip("no generated resume yet")
        from app.profile import get_profile
        profile = get_profile()
        rep = validate_resume(gen, {str(f.value) for f in profile.to_fact_list()}, {profile.full_name, "Ethara AI"})
        assert rep["status"] == "OK", f"issues: {rep['issues']}"
