from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PY = str(REPO_ROOT / ".venv" / "bin" / "python") if (REPO_ROOT / ".venv").exists() else sys.executable


def _run_script(script_name: str, *args: str) -> tuple[int, str]:
    try:
        out = subprocess.run(
            [PY, str(REPO_ROOT / "scripts" / script_name), *args],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=180,
        )
        return out.returncode, (out.stdout or "") + "\n" + (out.stderr or "")
    except Exception as e:
        return 1, str(e)


class TestVerifySessionsScript:
    def test_verify_sessions_runs(self):
        rc, out = _run_script("verify_sessions.py")
        assert "Session verification" in out
        assert "AUTHENTICATED" in out or "LOGIN_REQUIRED" in out or "NOT_CONFIGURED" in out


class TestConnectGmailScript:
    def test_connect_gmail_prints_oauth_instructions_without_asking_for_password(self):
        rc, out = _run_script("connect_gmail.py")
        assert "OAuth" in out
        assert "NEVER accepts your Gmail password" in out
        for forbidden in ("Enter your password:", "Password:", "What is your Gmail password"):
            assert forbidden not in out

    def test_verify_gmail_prints_status_without_prompting(self):
        rc, out = _run_script("connect_gmail.py", "--verify")
        assert any(marker in out for marker in ("NOT CONFIGURED", "refresh token present in Keychain", "`keyring` is not installed"))
        for forbidden in ("Enter your password:", "Password:"):
            assert forbidden not in out


class TestDiscoveryAuditScript:
    def test_discovery_audit_runs(self):
        rc, out = _run_script("discovery_audit.py")
        assert "Discovery audit" in out
        for bucket in ("DISCOVERED", "QUALIFIED", "REJECTED", "DUPLICATE", "EXPIRED", "SCAM_RISK", "LOW_MATCH", "INVALID_URL"):
            assert bucket in out


class TestPlatformCapabilitiesScript:
    def test_platform_capabilities_runs(self):
        rc, out = _run_script("platform_capabilities.py")
        assert rc == 0
        assert "Platform capability matrix" in out
        for platform in ("linkedin", "naukri", "indeed", "remoteok", "gmail", "harban_business", "company_careers"):
            assert platform in out
        assert "REAL_GREENHOUSE_LEVER_ASHBY" in out
        assert "STUB_USER_ASSISTED" in out
        assert "OAUTH" in out

    def test_platform_capabilities_marks_stubs_honestly(self):
        rc, out = _run_script("platform_capabilities.py")
        assert "linkedin" in out
        for line in out.splitlines():
            if line.startswith("linkedin "):
                assert "STUB" in line or "USER" in line or "ASSISTED" in line, (
                    "LinkedIn discovery must be marked as STUB_USER_ASSISTED, not falsely YES"
                )


class TestPhaseStatusScript:
    @pytest.mark.skip(reason="phase_status.py runs pytest internally; would cause recursion in test context. Run `make phase-status` manually.")
    def test_phase_status_runs(self):
        pass

    def test_phase_status_structure(self):
        text = (REPO_ROOT / "scripts" / "phase_status.py").read_text()
        for section in ("PHASE 5 STATUS", "PHASE 6 STATUS", "REAL-WORLD RESULTS", "SECURITY CONFIRMATION", "FINAL STATUS"):
            assert section in text


class TestNoCredentialPromptsAnywhere:
    def test_no_make_target_prompts_for_password(self):
        makefile = (REPO_ROOT / "Makefile").read_text()
        for forbidden in ("read -s PASSWORD", "echo \"$$PASSWORD\"", "input password"):
            assert forbidden not in makefile

    def test_no_script_contains_input_password(self):
        for py in (REPO_ROOT / "scripts").glob("*.py"):
            text = py.read_text()
            for forbidden in ("input('password", 'input("password', "getpass.getpass", "stdin.readline()"):
                if forbidden in text:
                    assert "getpass" in text and "oauth" in text.lower(), (
                        f"{py.name}: contains '{forbidden}' outside an OAuth context"
                    )


class TestGmailScopeLeastPrivilege:
    def test_connect_gmail_uses_only_gmail_send_scope(self):
        text = (REPO_ROOT / "scripts" / "connect_gmail.py").read_text()
        assert "https://www.googleapis.com/auth/gmail.send" in text, (
            "connect_gmail.py must request gmail.send scope"
        )
        assert "gmail.compose" not in text, (
            "connect_gmail.py must NOT request gmail.compose (excess privilege; "
            "only gmail.send is needed to send drafted .eml files)"
        )
        assert "gmail.modify" not in text, "gmail.modify is broader than needed"
        assert "gmail.readonly" not in text, "gmail.readonly is not needed for send-only"


class TestCheckOauthConfigScript:
    def test_check_oauth_config_runs_and_reports_state(self):
        rc, out = _run_script("check_oauth_config.py")
        assert "Gmail OAuth pre-flight check" in out
        for section in ("[1] .env OAuth config", "[2] Python dependencies", "[3] macOS Keychain token"):
            assert section in out
        assert "NEXT STEP" in out or "ALL CHECKS PASS" in out

    def test_check_oauth_config_never_prints_token_or_secret_values(self):
        rc, out = _run_script("check_oauth_config.py")
        for forbidden in ("refresh_token:", "Bearer ya29.", "sk-", "GOCSPX-"):
            assert forbidden not in out, f"check_oauth_config.py leaked prefix: {forbidden}"


class TestInstallGmailClientScript:
    def test_install_rejects_missing_file(self, tmp_path):
        rc, out = _run_script("install_gmail_client.py", str(tmp_path / "nope.json"))
        assert rc == 1
        assert "file does not exist" in out

    def test_install_rejects_non_installed_app_type(self, tmp_path):
        import json as _json
        bad = tmp_path / "web.json"
        bad.write_text(_json.dumps({"web": {"client_id": "x.apps.googleusercontent.com", "client_secret": "y"}}))
        rc, out = _run_script("install_gmail_client.py", str(bad))
        assert rc == 1
        assert "not an 'installed'" in out or "Desktop app" in out

    def test_install_rejects_malformed_json(self, tmp_path):
        bad = tmp_path / "garbage.json"
        bad.write_text("not valid json {{{")
        rc, out = _run_script("install_gmail_client.py", str(bad))
        assert rc == 1
        assert "not valid JSON" in out


class TestLoginMakeTargetsCoverUserDrivenPlatforms:
    def test_all_user_driven_platforms_have_login_targets(self):
        makefile = (REPO_ROOT / "Makefile").read_text()
        expected_targets = [
            "login-linkedin", "login-naukri", "login-indeed",
            "login-handshake", "login-wellfound", "login-outlier",
            "login-glassdoor", "login-cutshort", "login-instahyre",
            "login-hirist", "login-foundit", "login-internshala",
            "login-surge-ai", "login-telus-digital-ai",
        ]
        for target in expected_targets:
            assert f"\n{target}:" in makefile, f"Makefile missing target: {target}"

    def test_login_targets_dispatch_to_valid_account_platforms(self):
        from app.accounts.enums import AccountPlatform
        valid_values = {p.value for p in AccountPlatform}
        makefile = (REPO_ROOT / "Makefile").read_text()
        import re
        for match in re.finditer(r"\$\(PY\) -m app\.accounts\.cli (\w+)", makefile):
            platform_arg = match.group(1)
            assert platform_arg in valid_values, (
                f"Makefile login target dispatches to '{platform_arg}' which is not "
                f"an AccountPlatform value. Valid values: {sorted(valid_values)}"
            )
