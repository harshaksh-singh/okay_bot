from __future__ import annotations

import sys
from datetime import date

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from app.agents import AgentContext, JobAgentOrchestrator, OrchestratorResult
from app.analytics import build_daily_report, build_dashboard_snapshot
from app.applications.tracker import ApplicationTracker
from app.config import get_settings
from app.database import init_database
from app.profile import get_profile
from app.schemas.enums import ApplicationStatus, PriorityTier


console = Console()
_tracker = ApplicationTracker()


def _mode_label(settings) -> str:
    bits = []
    if settings.dry_run:
        bits.append("DRY RUN")
    if settings.mock_mode:
        bits.append("MOCK")
    return " / ".join(bits) if bits else "LIVE"


def _print_banner(settings, profile) -> None:
    bar = "=" * 54
    panel = Text()
    panel.append(bar + "\n", style="bold cyan")
    panel.append("AI JOB APPLICATION ASSISTANT\n", style="bold white")
    panel.append(bar + "\n\n", style="bold cyan")
    panel.append(f"Profile:         {profile.full_name}\n")
    panel.append(f"Target:          AI / ML / Software Engineering\n")
    panel.append(f"Locations:       Gurugram / Noida / Delhi NCR / India Remote / Global Remote\n")
    panel.append(f"Employment:      Part-time / Contract / Remote / Full-time\n")
    panel.append(f"Mode:            {_mode_label(settings)}\n")
    panel.append(f"Auto Submit:     {'OFF' if not settings.auto_submit else 'ON'}\n")
    panel.append(f"Auto Email:      {'OFF' if not settings.auto_email else 'ON'}\n")
    panel.append(f"User Approval:   {'ON' if settings.user_approval_required else 'OFF'}\n")
    panel.append(bar, style="bold cyan")
    console.print(Panel.fit(panel, border_style="cyan"))


def _menu() -> int:
    console.print()
    console.print("[bold yellow][1][/bold yellow] Discover Jobs")
    console.print("[bold yellow][2][/bold yellow] Analyze Jobs")
    console.print("[bold yellow][3][/bold yellow] Review Matches")
    console.print("[bold yellow][4][/bold yellow] Prepare Applications")
    console.print("[bold yellow][5][/bold yellow] Review Applications")
    console.print("[bold yellow][6][/bold yellow] Application Tracker")
    console.print("[bold yellow][7][/bold yellow] Recruiter Outreach")
    console.print("[bold yellow][8][/bold yellow] Email Drafts")
    console.print("[bold yellow][9][/bold yellow] Dashboard")
    console.print("[bold yellow][10][/bold yellow] Settings")
    console.print("[bold yellow][11][/bold yellow] Run full pipeline (end-to-end)")
    console.print("[bold yellow][0][/bold yellow] Exit")
    return IntPrompt.ask("Choose", default=11)


def _build_context(profile) -> AgentContext:
    s = get_settings()
    return AgentContext(
        profile=profile,
        discovery_queries=[],
        discovery_locations=[],
        employment_types=[],
        remote_only=False,
        limit_per_source=None,
        dry_run=s.dry_run,
        require_user_approval=s.user_approval_required,
    )


_LAST_RESULT: OrchestratorResult | None = None


def _run_pipeline(profile) -> OrchestratorResult:
    global _LAST_RESULT
    ctx = _build_context(profile)
    orchestrator = JobAgentOrchestrator()
    console.print("[cyan]Running pipeline (compliance -> discovery -> extraction -> matching -> research -> application -> communication -> followup -> quality -> persistence)...[/cyan]")
    result = orchestrator.run(ctx)
    _LAST_RESULT = result
    for ar in result.agent_results:
        prefix = "[green]✓[/green]" if ar.ok else "[red]✗[/red]"
        notes = "; ".join(ar.notes) if ar.notes else "no notes"
        console.print(f"  {prefix} {ar.agent:14s} :: {notes}")
        for err in ar.errors[:3]:
            console.print(f"      [dim red]error: {err}[/dim red]")
    return result


def _print_job_row(table: Table, j, show_reason: bool = True) -> None:
    priority_display = f"{j.priority.emoji} {j.priority.value}"
    table.add_row(
        priority_display,
        f"{j.match_score:.1f}",
        j.title[:48],
        j.company[:28],
        (j.location or "")[:28],
        j.employment_type.value,
        (j.reason_for_match[0] if j.reason_for_match and show_reason else "")[:40],
    )


def _show_matches(result: OrchestratorResult, limit: int = 30) -> None:
    matching = result.get("matching")
    if not matching or not matching.jobs:
        console.print("[yellow]No matches yet. Run the pipeline first.[/yellow]")
        return
    table = Table(title=f"Top {min(limit, len(matching.jobs))} matches", show_lines=False)
    table.add_column("Priority", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Role")
    table.add_column("Company")
    table.add_column("Location")
    table.add_column("Type")
    table.add_column("Why", style="dim")
    for j in matching.jobs[:limit]:
        _print_job_row(table, j)
    console.print(table)


def _show_rejects(result: OrchestratorResult, limit: int = 20) -> None:
    matching = result.get("matching")
    if not matching:
        return
    if not matching.rejected_jobs:
        console.print("[green]No rejections.[/green]")
        return
    table = Table(title=f"Rejected (first {min(limit, len(matching.rejected_jobs))})")
    table.add_column("Role")
    table.add_column("Company")
    table.add_column("Reasons")
    for j, reasons in matching.rejected_jobs[:limit]:
        table.add_row(j.title[:40], j.company[:28], "; ".join(reasons)[:80])
    console.print(table)


def _show_dashboard(result: OrchestratorResult) -> None:
    if result.halted_by_compliance:
        comp = result.get("compliance")
        viol = comp.metadata.get("hard_violations", []) if comp else []
        halt_panel = Text()
        halt_panel.append("PIPELINE HALTED BY COMPLIANCE\n", style="bold red")
        halt_panel.append("No jobs discovered. No applications prepared. No DB writes.\n\n")
        halt_panel.append("Hard violations:\n", style="bold")
        for v in viol:
            halt_panel.append(f"  • {v}\n", style="red")
        halt_panel.append("\nRemediation: unset the forbidden flag(s) in .env then re-run.")
        console.print(Panel(halt_panel, border_style="red", title="COMPLIANCE HALT"))
        return

    snap = build_dashboard_snapshot(result)
    tbl = Table(title="Today's discovery", show_header=False)
    tbl.add_column("Metric", style="bold")
    tbl.add_column("Value", justify="right")
    for line in snap.summary_lines():
        key, val = line.split(":", 1)
        tbl.add_row(key.strip(), val.strip())
    console.print(tbl)

    funnel = Table(title="Application funnel", show_header=False)
    funnel.add_column("Stage")
    funnel.add_column("Count", justify="right")
    for k, v in snap.pipeline_funnel.items():
        funnel.add_row(k, str(v))
    console.print(funnel)

    tier = Table(title="Priority tiers")
    tier.add_column("Tier"); tier.add_column("Count", justify="right")
    for t in PriorityTier:
        tier.add_row(f"{t.emoji} {t.value}", str(snap.tier_counts.get(t.value, 0)))
    console.print(tier)

    if snap.compliance_violations:
        console.print(Panel.fit("[red]Compliance violations:[/red]\n" + "\n".join(f"  • {v}" for v in snap.compliance_violations), border_style="red"))
    else:
        console.print("[green]Compliance: all safety defaults OK.[/green]")


def _show_harban_dashboard(result: OrchestratorResult) -> None:
    h = result.get("harban")
    if not h:
        console.print("[yellow]No Harban result (HARBAN_ENABLED=false?).[/yellow]")
        return
    counts = h.metadata.get("counts", {})
    tbl = Table(title="HARBAN BUSINESS", show_header=False)
    tbl.add_column("Metric", style="bold magenta")
    tbl.add_column("Value", justify="right")
    for k in ("opportunities_total", "classified_job", "classified_client", "classified_both", "classified_neither", "leads_discovered", "outreach_drafted"):
        tbl.add_row(k.replace("_", " ").title(), str(counts.get(k, 0)))
    console.print(tbl)

    sub = result.get("submission")
    if sub:
        tiers = sub.metadata.get("tier_counts", {})
        st_tbl = Table(title="Approved Application Submission", show_header=False)
        st_tbl.add_column("Tier", style="bold cyan")
        st_tbl.add_column("Count", justify="right")
        for k in ("AUTO_APPLY", "REVIEW_REQUIRED", "REJECT"):
            st_tbl.add_row(k, str(tiers.get(k, 0)))
        st_tbl.add_row("[dim]PRE_APPROVED_APPLICATIONS[/dim]", "[dim]" + ("ON" if sub.metadata.get("pre_approved_mode") else "OFF") + "[/dim]")
        st_tbl.add_row("[dim]AUTO_SUBMIT_APPROVED[/dim]", "[dim]" + ("ON" if sub.metadata.get("auto_submit_approved") else "OFF") + "[/dim]")
        console.print(st_tbl)


def _review_applications(result: OrchestratorResult) -> None:
    app_r = result.get("application")
    if not app_r:
        console.print("[yellow]No applications prepared. Run the pipeline first.[/yellow]")
        return
    apps = app_r.metadata.get("applications", [])
    if not apps:
        console.print("[yellow]No applications ready for review.[/yellow]")
        return
    if not sys.stdin.isatty():
        console.print(f"[yellow]Non-interactive stdin — skipping per-application prompts. "
                      f"{len(apps)} applications prepared and awaiting review.[/yellow]")
        return
    for app in apps[:10]:
        job = next((j for j in result.matched_jobs if j.job_id == app.job_id), None)
        if not job:
            continue
        body = Text()
        body.append(f"{job.priority.emoji} {job.priority.value.upper()}\n\n", style="bold yellow")
        body.append(f"Company:       {job.company}\n")
        body.append(f"Role:          {job.title}\n")
        body.append(f"Location:      {job.location}\n")
        body.append(f"Employment:    {job.employment_type.value}\n")
        body.append(f"Match Score:   {job.match_score:.1f}\n")
        body.append(f"Salary:        {job.pretty_salary()}\n\n")
        body.append("Why matched:\n", style="bold")
        for reason in job.reason_for_match[:5]:
            body.append(f"  {reason}\n")
        if job.missing_requirements:
            body.append("\nPotential concerns:\n", style="bold yellow")
            for g in job.missing_requirements[:3]:
                body.append(f"  ⚠ {g}\n")
        body.append(f"\nResume:         {app.resume_variant}\n")
        body.append(f"Application URL: {job.application_url or '-'}\n")
        body.append(f"Status:         {app.status.value}\n")
        if app.pending_user_inputs:
            body.append(f"USER_INPUT_REQUIRED: {', '.join(app.pending_user_inputs)}\n", style="bold red")
        console.print(Panel(body, title=f"[{app.application_id}]", border_style="cyan"))

        if app.cover_letter_text:
            console.print(Panel(app.cover_letter_text, title="Cover letter draft", border_style="green"))

        if get_settings().user_approval_required:
            console.print(
                "[bold]Approve submission?[/bold] "
                "[green][y]es[/green] / [red][n]o withdraw[/red] / "
                "[yellow][s]kip[/yellow] / [cyan][o]pen in browser[/cyan]"
            )
            answer = Prompt.ask("Approve submission?", choices=["y", "n", "s", "o"], default="s")
            if answer == "y":
                try:
                    _tracker.approve(app, note="user approved via CLI")
                    console.print(f"[green]Approved {app.application_id} (status now {app.status.value})[/green]")
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
            elif answer == "n":
                try:
                    _tracker.mark_withdrawn(app, reason="user declined via CLI")
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
            elif answer == "o":
                from app.browser import AssistedApplicationSession
                sess = AssistedApplicationSession(job=job, application=app)
                sess.open_in_default_browser()
                for note in sess.notes:
                    console.print(f"[cyan]{note}[/cyan]")
            else:
                console.print("[yellow]Skipped.[/yellow]")


def _recruiter_outreach(result: OrchestratorResult) -> None:
    comm = result.get("communication")
    if not comm:
        console.print("[yellow]No recruiter messages. Run the pipeline first.[/yellow]")
        return
    msgs = comm.metadata.get("recruiter_messages", [])
    if not msgs:
        console.print("[yellow]No recruiter messages to show.[/yellow]")
        return
    for m in msgs[:10]:
        console.print(Panel(m["message"], title=f"[{m['channel']}] job {m['job_id']}", border_style="magenta"))


def _email_drafts(result: OrchestratorResult) -> None:
    comm = result.get("communication")
    if not comm:
        console.print("[yellow]No email drafts. Run the pipeline first.[/yellow]")
        return
    emails = comm.metadata.get("emails", [])
    if not emails:
        console.print("[yellow]No email drafts (no jobs with explicit application_email in this batch).[/yellow]")
        return
    for e in emails[:10]:
        body = Text()
        body.append(f"To:      {e.get('to', '')}\n")
        body.append(f"Subject: {e.get('subject', '')}\n\n")
        body.append(e.get("body", ""))
        console.print(Panel(body, title=f"email draft (job {e['job_id']})", border_style="green"))


def _settings_view() -> None:
    s = get_settings()
    tbl = Table(title="Current settings (read from .env / defaults)")
    tbl.add_column("Setting"); tbl.add_column("Value")
    rows = [
        ("APP_ENV", s.app_env),
        ("MOCK_MODE", str(s.mock_mode)),
        ("DRY_RUN", str(s.dry_run)),
        ("AUTO_SUBMIT", str(s.auto_submit)),
        ("AUTO_EMAIL", str(s.auto_email)),
        ("USER_APPROVAL_REQUIRED", str(s.user_approval_required)),
        ("CAPTCHA_BYPASS", str(s.captcha_bypass)),
        ("MFA_BYPASS", str(s.mfa_bypass)),
        ("DATABASE_URL", s.database_url),
        ("LLM_PROVIDER", s.llm_provider),
        ("LINKEDIN_ENABLED", str(s.linkedin_enabled)),
        ("NAUKRI_ENABLED", str(s.naukri_enabled)),
        ("INDEED_ENABLED", str(s.indeed_enabled)),
        ("BROWSER_AUTOMATION_ENABLED", str(s.browser_automation_enabled)),
        ("EMAIL_ENABLED", str(s.email_enabled)),
    ]
    for k, v in rows:
        tbl.add_row(k, v)
    console.print(tbl)
    console.print("[dim]Edit `.env` to change these; defaults are SAFE (dry-run, no auto-submit, no bypasses).[/dim]")


def _get_flag_value(args: list[str], flag: str, default: str) -> str:
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i + 1]
        if a.startswith(f"{flag}="):
            return a.split("=", 1)[1]
    return default


def run_cli(args: list[str] | None = None) -> int:
    args = args if args is not None else sys.argv[1:]
    s = get_settings()
    profile = get_profile()
    _print_banner(s, profile)

    if "--autonomous-run" in args:
        from app.campaign import (
            CampaignConfig,
            CampaignOrchestrator,
            CampaignStrategy,
            format_campaign_report,
        )
        target = int(_get_flag_value(args, "--applications", "10"))
        strategy_str = _get_flag_value(args, "--strategy", "top_latest")
        try:
            strategy = CampaignStrategy(strategy_str)
        except ValueError:
            strategy = CampaignStrategy.TOP_LATEST
        dry_run = "--dry-run" in args or s.dry_run
        config = CampaignConfig(
            target_confirmed=target,
            strategy=strategy,
            dry_run=dry_run,
        )
        orch = CampaignOrchestrator()
        result = orch.run(config, profile)
        console.print("\n" + format_campaign_report(result))
        if result.errors and not result.is_target_reached():
            return 1
        return 0

    if "--discover" in args or "--pipeline" in args:
        result = _run_pipeline(profile)
        if result.halted_by_compliance:
            _show_dashboard(result)
            return 2
        _show_matches(result)
        _show_dashboard(result)
        if "--yes" not in args and "--no-review" not in args and get_settings().user_approval_required:
            console.print("\n[cyan]Entering human-in-the-loop approval review (per Section 13 of brief). "
                          "Pass --no-review to skip.[/cyan]\n")
            _review_applications(result)
        return 0
    if "--dashboard" in args:
        result = _LAST_RESULT or _run_pipeline(profile)
        _show_dashboard(result)
        return 2 if result.halted_by_compliance else 0
    if "--daily-report" in args:
        result = _LAST_RESULT or _run_pipeline(profile)
        rep = build_daily_report(result, for_date=date.today())
        console.print("\n".join(rep.lines))
        return 0
    if "--accounts" in args:
        from app.accounts import get_accounts_registry
        reg = get_accounts_registry()
        tbl = Table(title="Configured accounts (identifiers only — NO passwords)")
        tbl.add_column("Platform", style="bold")
        tbl.add_column("Account", style="")
        tbl.add_column("Purposes", style="")
        tbl.add_column("Login mode", style="dim")
        tbl.add_column("Session", style="cyan")
        tbl.add_column("Enabled", justify="center")
        tbl.add_column("Last verified", style="dim")
        for row in reg.summary_rows():
            tbl.add_row(
                row["platform"],
                row["username"],
                row["purposes"],
                row["login_mode"],
                row["session_status"],
                "YES" if row["enabled"] else "no",
                row["last_verified_at"],
            )
        console.print(tbl)
        console.print(
            "\n[dim]To activate a platform:[/dim] set `<PLATFORM>_ENABLED=true` and `<PLATFORM>_EMAIL=you@example.com` "
            "in .env, then run `make login-<platform>` to sign in YOURSELF in the opened browser window.\n"
            "[bold red]Passwords are NEVER requested or stored.[/bold red]"
        )
        return 0
    if "--production-daily" in args:
        from app.analytics import build_production_daily_report
        result = _LAST_RESULT or _run_pipeline(profile)
        rep = build_production_daily_report(result, for_date=date.today())
        console.print(rep.render())
        return 2 if result.halted_by_compliance else 0
    if "--daily-growth" in args:
        result = _LAST_RESULT or _run_pipeline(profile)
        _show_dashboard(result)
        _show_harban_dashboard(result)
        return 2 if result.halted_by_compliance else 0
    if "--apply-approved" in args:
        result = _LAST_RESULT or _run_pipeline(profile)
        sub = result.get("submission")
        if sub:
            console.print(Panel(
                "\n".join([f"{o['tier']}: {o['application_id']} → {o['outcome']}" for o in sub.metadata.get("outcomes", [])]),
                title="Approved submission outcomes",
                border_style="cyan",
            ))
        return 2 if result.halted_by_compliance else 0
    if "--client-discovery" in args:
        result = _LAST_RESULT or _run_pipeline(profile)
        _show_harban_dashboard(result)
        return 2 if result.halted_by_compliance else 0
    if "--client-outreach-dry-run" in args:
        result = _LAST_RESULT or _run_pipeline(profile)
        h = result.get("harban")
        if h:
            drafts = h.metadata.get("outreach_drafts", [])
            console.print(f"[cyan]{len(drafts)} outreach drafts (DRAFT_ONLY):[/cyan]")
            for d in drafts[:5]:
                body = Text()
                body.append(f"Channel:   {d['channel']}\n")
                body.append(f"Subject:   {d.get('subject') or '(none)'}\n")
                body.append(f"Recipient: {d.get('recipient') or '(pending verified public contact)'}\n")
                body.append(f"Signals:   {', '.join(d.get('personalized_signals') or [])}\n\n")
                body.append(d.get("body", ""))
                console.print(Panel(body, title=f"Draft for {d.get('company', 'company')}", border_style="magenta"))
        return 0
    if "--weekly-analytics" in args:
        from app.analytics import build_weekly_analytics
        from app.database import SessionLocal
        from app.database.models import ApplicationRow, MessageRow
        from sqlalchemy import select
        init_database()
        with SessionLocal() as session:
            apps = session.scalars(select(ApplicationRow)).all()
            msgs = session.scalars(select(MessageRow)).all()
        apps_count = len(apps)
        responses = len([m for m in msgs if m.response_at is not None])
        interviews = len([a for a in apps if a.status == "INTERVIEW"])
        offers = len([a for a in apps if a.status == "OFFER"])
        rep = build_weekly_analytics(apps_count, responses, interviews, offers)
        console.print(f"Weekly analytics (applications={rep.applications}):")
        console.print(f"  responses:     {rep.responses} ({rep.response_rate:.1f}%)")
        console.print(f"  interviews:    {rep.interviews} ({rep.interview_rate:.1f}%)")
        console.print(f"  offers:        {rep.offers}")
        console.print(f"  recommendation: {rep.recommendation}")
        return 0
    if "--non-interactive" in args:
        result = _run_pipeline(profile)
        _show_dashboard(result)
        _show_matches(result, limit=10)
        return 0

    while True:
        choice = _menu()
        if choice == 0:
            console.print("[cyan]Goodbye.[/cyan]")
            return 0
        if choice in (1, 2, 11):
            _run_pipeline(profile)
            continue
        if choice == 3:
            if _LAST_RESULT:
                _show_matches(_LAST_RESULT)
                _show_rejects(_LAST_RESULT, limit=10)
            else:
                console.print("[yellow]Run the pipeline first (option 1 or 11).[/yellow]")
            continue
        if choice == 4:
            if _LAST_RESULT:
                _review_applications(_LAST_RESULT)
            else:
                console.print("[yellow]Run the pipeline first.[/yellow]")
            continue
        if choice == 5:
            if _LAST_RESULT:
                _review_applications(_LAST_RESULT)
            else:
                console.print("[yellow]Run the pipeline first.[/yellow]")
            continue
        if choice == 6:
            if _LAST_RESULT:
                app_r = _LAST_RESULT.get("application")
                apps = app_r.metadata.get("applications", []) if app_r else []
                tbl = Table(title="Application tracker")
                tbl.add_column("App ID"); tbl.add_column("Status"); tbl.add_column("Job")
                for app in apps:
                    job = next((j for j in _LAST_RESULT.matched_jobs if j.job_id == app.job_id), None)
                    tbl.add_row(app.application_id, app.status.value, job.title if job else app.job_id)
                console.print(tbl)
            else:
                console.print("[yellow]No applications yet.[/yellow]")
            continue
        if choice == 7:
            if _LAST_RESULT:
                _recruiter_outreach(_LAST_RESULT)
            continue
        if choice == 8:
            if _LAST_RESULT:
                _email_drafts(_LAST_RESULT)
            continue
        if choice == 9:
            if _LAST_RESULT:
                _show_dashboard(_LAST_RESULT)
            else:
                console.print("[yellow]Run the pipeline first.[/yellow]")
            continue
        if choice == 10:
            _settings_view()
            continue
        console.print(f"[red]Unknown choice: {choice}[/red]")
