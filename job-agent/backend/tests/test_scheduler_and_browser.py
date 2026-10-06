from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.browser import AssistedApplicationSession, is_browser_available
from app.schemas.application import Application
from app.schemas.enums import ApplicationStatus


def test_browser_available_returns_bool():
    assert isinstance(is_browser_available(), bool)


def test_assisted_session_no_url_fails_gracefully(mock_jobs):
    job = mock_jobs[0]
    job.application_url = None
    app = Application(application_id="app_x", job_id=job.job_id, status=ApplicationStatus.APPLICATION_PREPARED)
    sess = AssistedApplicationSession(job=job, application=app)
    assert sess.open_in_default_browser() is False
    assert any("no application URL" in n for n in sess.notes)


def test_assisted_session_handles_webbrowser_failure(mock_jobs, monkeypatch):
    import webbrowser
    monkeypatch.setattr(webbrowser, "open", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no display")))
    job = mock_jobs[0]
    app = Application(application_id="app_x", job_id=job.job_id, status=ApplicationStatus.APPLICATION_PREPARED)
    sess = AssistedApplicationSession(job=job, application=app)
    assert sess.open_in_default_browser() is False
    assert any("failed to open" in n for n in sess.notes)


def test_scheduler_can_be_instantiated():
    from app.scheduler import JobScheduler
    sched = JobScheduler()
    sched.configure_default_runs()
    jobs = sched.list_jobs()
    assert len(jobs) == 3
    assert {j["id"] for j in jobs} == {"discovery_morning", "discovery_evening", "discovery_night"}


def test_scheduler_run_scheduled_discovery_executes(profile):
    from app.scheduler import run_scheduled_discovery
    result = run_scheduled_discovery(label="test")
    assert len(result.discovered_jobs) >= 50
    assert result.get("compliance") is not None


class TestLiveSubmitHelpers:
    def test_is_confirmation_url_detects_standard_patterns(self):
        from app.browser.assisted import _is_confirmation_url
        assert _is_confirmation_url("https://example.com/applications/thanks")
        assert _is_confirmation_url("https://jobs.lever.co/co/apply?LeverAppId=abc123")
        assert _is_confirmation_url("https://boards.greenhouse.io/thank-you")
        assert _is_confirmation_url("https://example.com/success")
        assert not _is_confirmation_url("https://example.com/apply")
        assert not _is_confirmation_url("")

    def test_is_confirmation_text_detects_success_phrases(self):
        from app.browser.assisted import _is_confirmation_text
        ok, matched = _is_confirmation_text("Thank you for applying to our company!")
        assert ok and matched is not None
        ok, _ = _is_confirmation_text("Your application has been submitted successfully.")
        assert ok
        ok, _ = _is_confirmation_text("We've received your application.")
        assert ok
        ok, _ = _is_confirmation_text("Please fill out the form below.")
        assert not ok
        ok, _ = _is_confirmation_text("")
        assert not ok


class TestSubmitAssistedLive:
    def test_missing_playwright_returns_error_and_short_circuits(self, mock_jobs, monkeypatch):
        import app.browser.assisted as mod
        monkeypatch.setattr(mod, "is_browser_available", lambda: False)
        job = mock_jobs[0]
        app = Application(application_id="app_test_pw", job_id=job.job_id, status=ApplicationStatus.APPLICATION_PREPARED)
        sess = AssistedApplicationSession(job=job, application=app)
        result = sess.submit_assisted_live()
        assert result.status == "ERROR"
        assert any("playwright" in n.lower() for n in result.notes)
        assert result.screenshots == []
        assert result.fields_prefilled == []

    def test_submit_result_dataclass_defaults(self):
        from app.browser.assisted import AssistedSubmitResult
        r = AssistedSubmitResult()
        assert r.status == "ERROR"
        assert r.confirmation is False
        assert r.confirmation_text is None
        assert r.hard_stop_reason is None
        assert r.fields_prefilled == []
        assert r.screenshots == []
        assert r.notes == []

    def test_submit_result_captures_confirmation_fields(self):
        from app.browser.assisted import AssistedSubmitResult
        from pathlib import Path
        r = AssistedSubmitResult(
            status="SUBMITTED_LIVE",
            confirmation=True,
            confirmation_text="Thank you for applying",
            confirmation_url="https://example.com/thanks",
            final_url="https://example.com/thanks",
            fields_prefilled=["email", "phone"],
            screenshots=[Path("/tmp/a.png")],
            notes=["submitted"],
        )
        assert r.status == "SUBMITTED_LIVE"
        assert r.confirmation
        assert r.fields_prefilled == ["email", "phone"]
        assert len(r.screenshots) == 1
