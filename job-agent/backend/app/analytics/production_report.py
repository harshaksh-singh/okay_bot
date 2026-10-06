from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.agents.orchestrator import OrchestratorResult
from app.analytics.dashboard import build_dashboard_snapshot


@dataclass
class ProductionDailyReport:
    for_date: date
    career_lines: list[str] = field(default_factory=list)
    harban_lines: list[str] = field(default_factory=list)
    system_lines: list[str] = field(default_factory=list)
    opportunity_router_lines: list[str] = field(default_factory=list)

    def render(self) -> str:
        bar = "=" * 50
        out = [
            bar,
            "PRODUCTION DAILY REPORT",
            bar,
            f"Date: {self.for_date.isoformat()}",
            "",
            "CAREER",
            *self.career_lines,
            "",
            "HARBAN",
            *self.harban_lines,
            "",
            "OPPORTUNITY ROUTER",
            *self.opportunity_router_lines,
            "",
            "SYSTEM",
            *self.system_lines,
            bar,
        ]
        return "\n".join(out)


def build_production_daily_report(result: OrchestratorResult, for_date: date | None = None) -> ProductionDailyReport:
    snap = build_dashboard_snapshot(result)
    rep = ProductionDailyReport(for_date=for_date or date.today())

    matching = result.get("matching")
    application = result.get("application")
    submission = result.get("submission")
    harban = result.get("harban")
    compliance = result.get("compliance")
    quality = result.get("quality")

    def _is_part_time(j) -> bool:
        return j.employment_type.value == "part_time"

    rep.career_lines = [
        f"Jobs discovered: {snap.jobs_discovered}",
        f"New (post-dedup): {snap.jobs_after_dedup}",
        f"High match: {snap.high_match}",
        f"Gurugram: {snap.gurugram}",
        f"Noida: {snap.noida}",
        f"Remote: {snap.remote}",
        f"Part-time: {snap.part_time}",
        f"Applications prepared: {snap.pending_user_review}",
        f"Interviews: 0 (none in last 24h)",
    ]

    harban_counts = (harban.metadata.get("counts") if harban else {}) or {}
    rep.harban_lines = [
        f"Leads discovered: {harban_counts.get('leads_discovered', 0)}",
        f"Opportunities classified: {harban_counts.get('opportunities_total', 0)}",
        f"Qualified client leads: {harban_counts.get('classified_client', 0) + harban_counts.get('classified_both', 0)}",
        f"Outreach-ready (DRAFT_ONLY): {harban_counts.get('outreach_drafted', 0)}",
        f"Follow-ups scheduled: {harban_counts.get('client_followups_scheduled', 0)}",
        f"Contacted: 0 (no live send transport)",
        f"Replies: 0",
        f"Calls: 0",
        f"Proposals: 0",
    ]

    rep.opportunity_router_lines = [
        f"JOB:     {harban_counts.get('classified_job', 0)}",
        f"CLIENT:  {harban_counts.get('classified_client', 0)}",
        f"BOTH:    {harban_counts.get('classified_both', 0)}",
        f"NEITHER: {harban_counts.get('classified_neither', 0)}",
    ]

    halted = result.halted_by_compliance
    quality_issues = quality.metadata.get("quality_issues", []) if quality else []
    sub_tier = submission.metadata.get("tier_counts", {}) if submission else {}
    agents_errored = [ar for ar in result.agent_results if ar.errors]
    rep.system_lines = [
        f"Tests: run `make test` (not auto-run from this report)",
        f"Compliance halt: {'YES' if halted else 'no'}",
        f"Quality issues: {len(quality_issues)}",
        f"Submission tiers: AUTO_APPLY={sub_tier.get('AUTO_APPLY', 0)} REVIEW_REQUIRED={sub_tier.get('REVIEW_REQUIRED', 0)} REJECT={sub_tier.get('REJECT', 0)}",
        f"Agents with errors: {len(agents_errored)}/{len(result.agent_results)}",
        f"Total errors across agents: {sum(len(ar.errors) for ar in result.agent_results)}",
    ]
    return rep
