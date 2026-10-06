from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.agents.orchestrator import OrchestratorResult
from app.analytics.dashboard import build_dashboard_snapshot


@dataclass
class DailyReport:
    for_date: date
    new_jobs: int
    high_match: int
    gurugram: int
    noida: int
    remote: int
    part_time: int
    ai_ml: int
    software: int
    application_ready: int
    important_deadlines: int = 0
    recruiter_responses: int = 0
    lines: list[str] = field(default_factory=list)


@dataclass
class WeeklyAnalytics:
    applications: int
    responses: int
    interviews: int
    offers: int
    response_rate: float
    interview_rate: float
    best_role: str | None
    best_source: str | None
    recommendation: str


def _is_ai_ml(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in ("ai ", "ml ", "machine learning", "llm", "genai", "generative", "rlhf", "ai engineer", "data scientist"))


def _is_software(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in ("software engineer", "backend", "full stack", "python developer", "java developer"))


def build_daily_report(result: OrchestratorResult, for_date: date | None = None) -> DailyReport:
    snap = build_dashboard_snapshot(result)
    matching = result.get("matching")
    ai_ml = sum(1 for j in (matching.jobs if matching else []) if _is_ai_ml(j.title))
    software = sum(1 for j in (matching.jobs if matching else []) if _is_software(j.title))

    rep = DailyReport(
        for_date=for_date or date.today(),
        new_jobs=snap.jobs_discovered,
        high_match=snap.high_match,
        gurugram=snap.gurugram,
        noida=snap.noida,
        remote=snap.remote,
        part_time=snap.part_time,
        ai_ml=ai_ml,
        software=software,
        application_ready=snap.apply_now,
    )
    rep.lines = [
        f"# DAILY JOB REPORT",
        f"Date: {rep.for_date.isoformat()}",
        "",
        f"New jobs: {rep.new_jobs}",
        f"High match: {rep.high_match}",
        f"Gurugram: {rep.gurugram}",
        f"Noida: {rep.noida}",
        f"Remote: {rep.remote}",
        f"Part-time: {rep.part_time}",
        f"AI/ML: {rep.ai_ml}",
        f"Software: {rep.software}",
        f"Application-ready: {rep.application_ready}",
    ]
    return rep


def build_weekly_analytics(applications_count: int, responses: int, interviews: int, offers: int, best_role: str | None = None, best_source: str | None = None) -> WeeklyAnalytics:
    response_rate = (responses / applications_count * 100) if applications_count else 0.0
    interview_rate = (interviews / applications_count * 100) if applications_count else 0.0

    if response_rate < 5:
        rec = "response rate <5% — consider tightening match threshold or improving cover letter specificity"
    elif response_rate < 15:
        rec = "response rate moderate — expand to AI evaluation / contract roles for higher conversion"
    else:
        rec = "response rate strong — maintain current targeting and consider raising application volume"

    return WeeklyAnalytics(
        applications=applications_count,
        responses=responses,
        interviews=interviews,
        offers=offers,
        response_rate=response_rate,
        interview_rate=interview_rate,
        best_role=best_role,
        best_source=best_source,
        recommendation=rec,
    )
