from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from app.agents import AgentContext, JobAgentOrchestrator, OrchestratorResult
from app.analytics import build_daily_report, build_dashboard_snapshot
from app.config import get_settings
from app.observability import get_logger
from app.profile import get_profile

log = get_logger("scheduler")


def run_scheduled_discovery(label: str = "manual") -> OrchestratorResult:
    s = get_settings()
    profile = get_profile()
    ctx = AgentContext(
        profile=profile,
        discovery_queries=[],
        discovery_locations=[],
        employment_types=[],
        dry_run=s.dry_run,
        require_user_approval=s.user_approval_required,
    )
    orchestrator = JobAgentOrchestrator()
    log.info("scheduler.run_started", label=label)
    result = orchestrator.run(ctx)
    snap = build_dashboard_snapshot(result)
    log.info(
        "scheduler.run_finished",
        label=label,
        discovered=snap.jobs_discovered,
        canonical=snap.jobs_after_dedup,
        rejected=snap.jobs_rejected,
        high_match=snap.high_match,
        apply_now=snap.apply_now,
    )
    _write_daily_report(result)
    return result


def _write_daily_report(result: OrchestratorResult) -> Path:
    s = get_settings()
    reports_dir = s.data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    rep = build_daily_report(result, for_date=date.today())
    out = reports_dir / f"daily_report_{rep.for_date.isoformat()}.md"
    out.write_text("\n".join(rep.lines))
    log.info("scheduler.report_written", path=str(out))
    return out


class JobScheduler:
    def __init__(self) -> None:
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError as e:
            raise RuntimeError("apscheduler not installed; `pip install apscheduler`") from e
        self._BackgroundScheduler = BackgroundScheduler
        self._CronTrigger = CronTrigger
        self._scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
        self._configured = False

    def configure_default_runs(self) -> None:
        if self._configured:
            return
        s = get_settings()
        for label, hhmm in (
            ("morning", s.schedule_morning_ist),
            ("evening", s.schedule_evening_ist),
            ("night", s.schedule_night_ist),
        ):
            try:
                hh, mm = hhmm.split(":")
                trigger = self._CronTrigger(hour=int(hh), minute=int(mm))
                self._scheduler.add_job(
                    run_scheduled_discovery,
                    trigger=trigger,
                    kwargs={"label": label},
                    id=f"discovery_{label}",
                    replace_existing=True,
                )
                log.info("scheduler.job_registered", label=label, time=hhmm)
            except Exception as e:
                log.warning("scheduler.job_registration_failed", label=label, error=str(e))
        self._configured = True

    def start(self) -> None:
        if not self._configured:
            self.configure_default_runs()
        if not self._scheduler.running:
            self._scheduler.start()
            log.info("scheduler.started")

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            log.info("scheduler.stopped")

    def list_jobs(self) -> list[dict]:
        out: list[dict] = []
        for j in self._scheduler.get_jobs():
            next_run = getattr(j, "next_run_time", None)
            out.append({
                "id": j.id,
                "next_run": str(next_run) if next_run else None,
                "trigger": str(j.trigger),
            })
        return out
