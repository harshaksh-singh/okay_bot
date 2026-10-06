from __future__ import annotations

from app.agents import AgentContext, JobAgentOrchestrator


def _default_context(profile):
    return AgentContext(
        profile=profile,
        discovery_queries=[],
        discovery_locations=[],
        employment_types=[],
        remote_only=False,
        limit_per_source=None,
        dry_run=True,
        require_user_approval=True,
    )


def test_orchestrator_runs_all_agents(profile):
    o = JobAgentOrchestrator()
    r = o.run(_default_context(profile))
    agent_names = {ar.agent for ar in r.agent_results}
    expected = {"discovery", "extraction", "matching", "research", "application", "communication", "followup", "compliance", "quality"}
    assert expected.issubset(agent_names)


def test_orchestrator_produces_discovered_jobs(profile):
    o = JobAgentOrchestrator()
    r = o.run(_default_context(profile))
    assert len(r.discovered_jobs) >= 50


def test_orchestrator_dedup_folds_duplicates(profile):
    o = JobAgentOrchestrator()
    r = o.run(_default_context(profile))
    assert len(r.canonical_jobs) < len(r.discovered_jobs)
    assert len(r.canonical_jobs) >= 40


def test_orchestrator_matches_and_scores(profile):
    o = JobAgentOrchestrator()
    r = o.run(_default_context(profile))
    scored = r.matched_jobs
    assert scored, "should have at least some kept matches"
    assert all(0 <= j.match_score <= 100 for j in scored)
    assert scored == sorted(scored, key=lambda j: j.match_score, reverse=True)


def test_orchestrator_rejects_scams_and_unrelated(profile):
    o = JobAgentOrchestrator()
    r = o.run(_default_context(profile))
    rejected_titles = [j.title.lower() for j, _ in r.rejected_jobs]
    assert any("nurse" in t for t in rejected_titles) or any("sales" in t for t in rejected_titles)
    assert any("data entry" in t for t in rejected_titles) or any(any("scam" in reason.lower() for reason in reasons) for _, reasons in r.rejected_jobs)


def test_orchestrator_compliance_passes_in_safe_defaults(profile):
    o = JobAgentOrchestrator()
    r = o.run(_default_context(profile))
    comp = r.get("compliance")
    assert comp is not None
    assert not comp.metadata.get("compliance_violations"), f"unexpected: {comp.metadata}"


def test_orchestrator_prepares_applications(profile):
    o = JobAgentOrchestrator()
    r = o.run(_default_context(profile))
    apps = r.applications
    assert len(apps) > 0
    assert all(a.cover_letter_text for a in apps)
    assert all(a.form_answers for a in apps)
    assert all(a.resume_variant for a in apps)


def test_orchestrator_identifies_pending_user_inputs(profile):
    o = JobAgentOrchestrator()
    r = o.run(_default_context(profile))
    apps = r.applications
    assert all("expected_salary" in a.pending_user_inputs for a in apps)


def test_orchestrator_schedules_followups(profile):
    o = JobAgentOrchestrator()
    r = o.run(_default_context(profile))
    fu = r.get("followup")
    assert fu is not None
    scheduled = fu.metadata.get("followups_scheduled", [])
    assert scheduled


def test_orchestrator_quality_flags_no_forbidden_claims(profile):
    o = JobAgentOrchestrator()
    r = o.run(_default_context(profile))
    q = r.get("quality")
    assert q is not None
    issues = q.metadata.get("quality_issues", [])
    assert all("forbidden" not in i["issue"] for i in issues)
