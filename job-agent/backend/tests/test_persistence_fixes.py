from __future__ import annotations

from sqlalchemy import select

from app.agents import AgentContext, JobAgentOrchestrator
from app.applications.preparer import ApplicationPreparer
from app.data.mock_jobs import build_mock_jobs
from app.database import SessionLocal, init_database
from app.database.models import (
    ApplicationRow,
    AuditLogRow,
    EmailRow,
    FollowupRow,
    JobRow,
    MessageRow,
    SearchRunRow,
)


def _ctx(profile):
    return AgentContext(
        profile=profile,
        discovery_queries=[],
        discovery_locations=[],
        employment_types=[],
        dry_run=True,
        require_user_approval=True,
    )


def test_pipeline_writes_email_rows(profile):
    init_database()
    orch = JobAgentOrchestrator()
    orch.run(_ctx(profile))
    with SessionLocal() as s:
        emails = s.scalars(select(EmailRow)).all()
    assert len(emails) >= 1, "pipeline must write EmailRow records for jobs with application_email"
    assert any(e.to_address.endswith("indieailabs.co") for e in emails)
    assert any(e.status == "draft" for e in emails)


def test_pipeline_is_idempotent_for_messages_and_followups(profile):
    init_database()
    orch = JobAgentOrchestrator()
    orch.run(_ctx(profile))
    with SessionLocal() as s:
        msgs_before = len(s.scalars(select(MessageRow)).all())
        fus_before = len(s.scalars(select(FollowupRow)).all())
        jobs_before = len(s.scalars(select(JobRow)).all())
        apps_before = len(s.scalars(select(ApplicationRow)).all())

    orch.run(_ctx(profile))
    with SessionLocal() as s:
        msgs_after = len(s.scalars(select(MessageRow)).all())
        fus_after = len(s.scalars(select(FollowupRow)).all())
        jobs_after = len(s.scalars(select(JobRow)).all())
        apps_after = len(s.scalars(select(ApplicationRow)).all())

    assert msgs_after == msgs_before, "MessageRow must be idempotent across pipeline reruns"
    assert fus_after == fus_before, "FollowupRow must be idempotent across pipeline reruns"
    assert jobs_after == jobs_before
    assert apps_after == apps_before


def test_search_runs_sources_is_flat_list(profile):
    init_database()
    orch = JobAgentOrchestrator()
    orch.run(_ctx(profile))
    with SessionLocal() as s:
        runs = s.scalars(select(SearchRunRow)).all()
    assert runs
    for r in runs:
        assert isinstance(r.sources, list)
        for entry in r.sources:
            assert isinstance(entry, str), f"expected flat list of strings, got {type(entry).__name__}"


def test_resume_files_exist_after_prepare(profile):
    preparer = ApplicationPreparer()
    jobs = build_mock_jobs()
    job = next(j for j in jobs if j.source_job_id == "li-ai-ant-001")
    app = preparer.prepare(job, profile, dry_run=True)
    assert app.resume_path is not None
    assert app.resume_path.exists(), f"resume path {app.resume_path} must exist after prepare"
    content = app.resume_path.read_text()
    assert "Harshaksh Singh" in content
    assert "Ethara AI" in content


def test_cli_exit_code_on_compliance_halt(profile, monkeypatch, tmp_path):
    from unittest.mock import patch
    from app.config import Settings
    from app.cli import run_cli

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/halt.db")

    with patch("app.agents.compliance_agent.get_settings") as m:
        m.return_value = Settings(captcha_bypass=True)
        rc = run_cli(["--discover"])
    assert rc == 2, "CLI must return non-zero exit code when pipeline halted by compliance"
