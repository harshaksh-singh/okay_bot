from __future__ import annotations

from app.campaign.orchestrator import CampaignResult


def format_campaign_report(result: CampaignResult) -> str:
    cfg = result.config
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("PORTOLAN APPLICATION CAMPAIGN")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Strategy:        {cfg.strategy.value}")
    lines.append(f"Mode:            {'DRY-RUN' if cfg.dry_run else 'LIVE'}")
    lines.append(f"Target:          {cfg.target_confirmed} {'simulated' if cfg.dry_run else 'confirmed'} submissions")
    lines.append(f"Min match score: {cfg.min_match_score:.0f}")
    lines.append(f"Freshness:       <= {cfg.freshness_days} days")
    lines.append("")
    lines.append(f"Started:         {result.started_at.isoformat()}")
    if result.finished_at:
        duration = (result.finished_at - result.started_at).total_seconds()
        lines.append(f"Finished:        {result.finished_at.isoformat()} ({duration:.1f}s)")
    lines.append("")

    lines.append("Pipeline:")
    lines.append(f"  Discovered:    {result.jobs_discovered}")
    lines.append(f"  Eligible:      {result.jobs_eligible}")
    lines.append(f"  Attempted:     {result.attempted}")
    lines.append("")

    lines.append("Outcomes:")
    lines.append(f"  SUBMITTED (live):              {result.confirmed}")
    lines.append(f"  Simulated (dry-run):           {result.simulated_dry_run}")
    lines.append(f"  Blocked (security/CAPTCHA):    {result.blocked_security}")
    lines.append(f"  Blocked (legal/arbitration):   {result.blocked_legal}")
    lines.append(f"  Requires user data:            {result.requires_user_data}")
    lines.append(f"  Infra blocked (browser/env):   {result.infra_blocked}")
    lines.append(f"  Rejected (eligibility):        {result.rejected}")
    lines.append(f"  Skipped (idempotent):          {result.skipped_idempotent}")
    lines.append(f"  Failed:                        {result.failed}")
    lines.append("")

    target_reached = result.is_target_reached()
    status = "TARGET REACHED" if target_reached else "TARGET NOT REACHED"
    lines.append(f"Status: {status}")

    if result.errors:
        lines.append("")
        lines.append("Errors:")
        for e in result.errors[:5]:
            lines.append(f"  - {e[:200]}")

    lines.append("=" * 60)
    return "\n".join(lines)
