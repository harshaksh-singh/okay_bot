from __future__ import annotations

import pytest

from app.agents import AgentContext, JobAgentOrchestrator
from app.analytics import build_daily_report, build_dashboard_snapshot
from app.applications.tracker import ApplicationTracker
from app.schemas.enums import ApplicationStatus, EmploymentType, PriorityTier


@pytest.fixture(scope="module")
def pipeline(profile):
    ctx = AgentContext(
        profile=profile,
        discovery_queries=[],
        discovery_locations=[],
        employment_types=[],
        dry_run=True,
        require_user_approval=True,
    )
    o = JobAgentOrchestrator()
    return o.run(ctx)


@pytest.mark.acceptance
def test_01_discover_50_mock_jobs(pipeline):
    assert len(pipeline.discovered_jobs) >= 50


@pytest.mark.acceptance
def test_02_deduplicate_them(pipeline):
    assert len(pipeline.canonical_jobs) < len(pipeline.discovered_jobs)


@pytest.mark.acceptance
def test_03_score_them(pipeline):
    assert all(0 <= j.match_score <= 100 for j in pipeline.matched_jobs)


@pytest.mark.acceptance
def test_04_identify_top_10(pipeline):
    top = pipeline.matched_jobs[:10]
    assert len(top) == 10
    assert all(top[i].match_score >= top[i+1].match_score for i in range(len(top)-1))


@pytest.mark.acceptance
def test_05_filter_part_time_jobs(pipeline):
    pt = [j for j in pipeline.matched_jobs if j.employment_type == EmploymentType.PART_TIME]
    assert pt, "should find at least one part-time match"


@pytest.mark.acceptance
def test_06_filter_gurugram_jobs(pipeline):
    gur = [j for j in pipeline.matched_jobs if "gur" in j.location.lower() or "cyber" in j.location.lower()]
    assert gur, "should find Gurugram-area matches"


@pytest.mark.acceptance
def test_07_filter_noida_jobs(pipeline):
    noida = [j for j in pipeline.matched_jobs if "noida" in j.location.lower()]
    assert noida


@pytest.mark.acceptance
def test_08_filter_remote_jobs(pipeline):
    remote = [j for j in pipeline.matched_jobs if j.is_remote()]
    assert remote


@pytest.mark.acceptance
def test_09_generate_tailored_application_materials(pipeline):
    apps = pipeline.applications
    assert apps
    assert all(a.cover_letter_text for a in apps)
    assert all(a.resume_variant for a in apps)


@pytest.mark.acceptance
def test_10_create_application_queue(pipeline):
    assert pipeline.applications
    assert all(a.application_id.startswith("app_") for a in pipeline.applications)


@pytest.mark.acceptance
def test_11_require_user_approval(pipeline):
    apps = pipeline.applications
    assert all(not a.approved_by_user for a in apps)
    assert all(a.status in {ApplicationStatus.MATCHED, ApplicationStatus.REVIEW_REQUIRED} for a in apps)


@pytest.mark.acceptance
def test_12_simulate_application(pipeline, profile):
    apps = pipeline.applications
    assert apps
    tracker = ApplicationTracker()
    sample = apps[0]
    tracker.approve(sample)
    tracker.mark_prepared(sample)
    assert sample.status == ApplicationStatus.APPLICATION_PREPARED


@pytest.mark.acceptance
def test_13_generate_recruiter_email_or_message(pipeline):
    comm = pipeline.get("communication")
    assert comm is not None
    msgs = comm.metadata.get("recruiter_messages", [])
    assert msgs, "should draft at least one recruiter message"


@pytest.mark.acceptance
def test_14_generate_followup(pipeline):
    fu = pipeline.get("followup")
    assert fu is not None
    assert fu.metadata.get("followups_scheduled")


@pytest.mark.acceptance
def test_15_store_everything(pipeline):
    assert pipeline.get("discovery") is not None
    assert pipeline.get("matching") is not None
    assert pipeline.get("application") is not None


@pytest.mark.acceptance
def test_16_display_dashboard(pipeline):
    snap = build_dashboard_snapshot(pipeline)
    assert snap.jobs_discovered >= 50
    assert snap.pipeline_funnel


@pytest.mark.acceptance
def test_17_end_to_end_persists_to_database(pipeline):
    from sqlalchemy import select
    from app.database import SessionLocal, init_database
    from app.database.models import ApplicationRow, FollowupRow, JobRow, MessageRow, SearchRunRow, AuditLogRow
    init_database()
    with SessionLocal() as session:
        jobs = session.scalars(select(JobRow)).all()
        apps = session.scalars(select(ApplicationRow)).all()
        runs = session.scalars(select(SearchRunRow)).all()
        audits = session.scalars(select(AuditLogRow)).all()
        msgs = session.scalars(select(MessageRow)).all()
        fus = session.scalars(select(FollowupRow)).all()
    assert len(jobs) >= 40, "pipeline must persist canonical+rejected jobs to DB"
    assert len(apps) >= 1, "pipeline must persist applications to DB"
    assert len(runs) >= 1, "pipeline must record a search run"
    assert len(audits) >= 1, "pipeline must record an audit log entry"
    assert len(msgs) >= 1, "pipeline must persist recruiter messages"
    assert len(fus) >= 2, "pipeline must schedule follow-ups per application"


@pytest.mark.acceptance
def test_18_failure_recovery(profile):
    class BrokenAgent:
        name = "broken"
        def run(self, ctx, prev):
            raise RuntimeError("boom")
    from app.agents.base import AgentContext
    from app.agents import DiscoveryAgent, JobAgentOrchestrator, MatchingAgent, ExtractionAgent
    o = JobAgentOrchestrator(agents=[DiscoveryAgent(), BrokenAgent(), ExtractionAgent(), MatchingAgent()])
    ctx = AgentContext(profile=profile)
    r = o.run(ctx)
    broken = next(a for a in r.agent_results if a.agent == "broken")
    assert broken.errors
    assert r.get("matching") is not None


@pytest.mark.acceptance
def test_19_duplicate_prevention(pipeline):
    group_ids = [j.duplicate_group for j in pipeline.canonical_jobs]
    assert len(group_ids) == len(set(group_ids))


@pytest.mark.acceptance
def test_20_scam_detection(pipeline):
    rejects = pipeline.rejected_jobs
    assert any(any("scam" in r.lower() for r in reasons) for _, reasons in rejects)


@pytest.mark.acceptance
def test_21_captcha_otp_stop_behavior():
    from app.agents.compliance_agent import ComplianceAgent
    from app.agents.base import AgentContext
    from unittest.mock import patch
    from app.compliance import ComplianceViolation
    from app.config import Settings

    with patch("app.agents.compliance_agent.get_settings") as m:
        m.return_value = Settings(captcha_bypass=True)
        agent = ComplianceAgent()
        from app.profile import get_profile
        ctx = AgentContext(profile=get_profile())
        with pytest.raises(ComplianceViolation):
            agent.run(ctx, [])


@pytest.mark.acceptance
def test_22_dry_run_mode(pipeline):
    apps = pipeline.applications
    assert all(a.submitted_at is None for a in apps)
    assert all(a.status != ApplicationStatus.SUBMITTED for a in apps)


@pytest.mark.acceptance
def test_23_daily_report_generates(pipeline):
    rep = build_daily_report(pipeline)
    assert rep.new_jobs >= 50
    assert any("DAILY JOB REPORT" in l for l in rep.lines)
