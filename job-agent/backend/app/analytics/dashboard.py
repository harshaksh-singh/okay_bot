from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.orchestrator import OrchestratorResult
from app.schemas import Job
from app.schemas.enums import EmploymentType, PriorityTier


_GURGAON_TERMS = {"gurgaon", "gurugram", "cyber hub", "cyber city", "udyog vihar"}
_NOIDA_TERMS = {"noida", "greater noida"}
_NCR_TERMS = {"delhi ncr", "delhi", "faridabad", "ghaziabad"}


def _in_any(location: str, needles: set[str]) -> bool:
    loc = (location or "").lower()
    return any(n in loc for n in needles)


@dataclass
class DashboardSnapshot:
    jobs_discovered: int = 0
    jobs_after_dedup: int = 0
    duplicates_removed: int = 0
    jobs_rejected: int = 0

    high_match: int = 0
    apply_now: int = 0
    part_time: int = 0
    remote: int = 0
    gurugram: int = 0
    noida: int = 0
    ncr_other: int = 0
    global_remote: int = 0

    tier_counts: dict[str, int] = field(default_factory=dict)
    source_counts: dict[str, int] = field(default_factory=dict)

    top_jobs: list[Job] = field(default_factory=list)
    high_priority_jobs: list[Job] = field(default_factory=list)
    part_time_jobs: list[Job] = field(default_factory=list)
    remote_jobs: list[Job] = field(default_factory=list)

    pipeline_funnel: dict[str, int] = field(default_factory=dict)
    pending_user_review: int = 0

    compliance_violations: list[str] = field(default_factory=list)
    scam_rejected: int = 0

    def summary_lines(self) -> list[str]:
        return [
            f"Jobs discovered: {self.jobs_discovered}",
            f"After dedup: {self.jobs_after_dedup} ({self.duplicates_removed} duplicates folded)",
            f"Rejected (hard rules + scam): {self.jobs_rejected}",
            f"High match (>=85): {self.high_match}",
            f"Apply now (>=75): {self.apply_now}",
            f"Part-time: {self.part_time}",
            f"Remote: {self.remote}",
            f"Gurugram: {self.gurugram}",
            f"Noida: {self.noida}",
            f"NCR other: {self.ncr_other}",
            f"Global remote: {self.global_remote}",
        ]


def build_dashboard_snapshot(result: OrchestratorResult) -> DashboardSnapshot:
    snap = DashboardSnapshot()

    discovery = result.get("discovery")
    extraction = result.get("extraction")
    matching = result.get("matching")
    application = result.get("application")
    compliance = result.get("compliance")

    if discovery:
        snap.jobs_discovered = discovery.metadata.get("jobs_discovered", len(discovery.jobs))
        for j in discovery.jobs:
            snap.source_counts[j.source.value] = snap.source_counts.get(j.source.value, 0) + 1

    if extraction:
        snap.jobs_after_dedup = len(extraction.jobs)
        snap.duplicates_removed = extraction.metadata.get("duplicates_removed", 0)

    if matching:
        kept = matching.jobs
        snap.jobs_rejected = len(matching.rejected_jobs)
        snap.scam_rejected = sum(1 for _, reasons in matching.rejected_jobs if any("scam" in r.lower() for r in reasons))

        for j in kept:
            if j.match_score >= 85:
                snap.high_match += 1
            if j.match_score >= 75:
                snap.apply_now += 1
            if j.employment_type == EmploymentType.PART_TIME:
                snap.part_time += 1
                snap.part_time_jobs.append(j)
            if j.is_remote():
                snap.remote += 1
                snap.remote_jobs.append(j)
            if _in_any(j.location, _GURGAON_TERMS):
                snap.gurugram += 1
            elif _in_any(j.location, _NOIDA_TERMS):
                snap.noida += 1
            elif _in_any(j.location, _NCR_TERMS):
                snap.ncr_other += 1
            if j.remote.value in {"remote_global", "remote_global_unverified"}:
                snap.global_remote += 1
            snap.tier_counts[j.priority.value] = snap.tier_counts.get(j.priority.value, 0) + 1

        snap.top_jobs = kept[:10]
        snap.high_priority_jobs = [j for j in kept if j.priority in {PriorityTier.APPLY_IMMEDIATELY, PriorityTier.HIGH_PRIORITY}]

    if application:
        snap.pending_user_review = application.metadata.get("pending_user_review", 0)

    if compliance:
        snap.compliance_violations = compliance.metadata.get("compliance_violations", [])

    snap.pipeline_funnel = {
        "Discovered": snap.jobs_discovered,
        "Canonical (after dedup)": snap.jobs_after_dedup,
        "Matched (after hard rules)": snap.jobs_after_dedup - snap.jobs_rejected,
        "High priority (>=85)": snap.high_match,
        "Prepared": snap.pending_user_review,
    }
    return snap
