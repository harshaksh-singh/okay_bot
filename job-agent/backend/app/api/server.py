from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from sqlalchemy import desc, func, select

from app.config import get_settings
from app.database import SessionLocal, init_database
from app.database.models import (
    ApplicationRow,
    AuditLogRow,
    ClientCompanyRow,
    ClientInteractionRow,
    ClientLeadRow,
    ClientOpportunityRow,
    CompanyRow,
    EmailRow,
    FollowupRow,
    InterviewRow,
    JobRow,
    MessageRow,
    SearchRunRow,
    SubmissionEvidenceRow,
)


def _row_to_dict(row: Any) -> dict:
    out: dict[str, Any] = {}
    for col in row.__table__.columns:
        v = getattr(row, col.name)
        try:
            if hasattr(v, "isoformat"):
                v = v.isoformat()
            out[col.name] = v
        except Exception:
            out[col.name] = str(v)
    return out


@asynccontextmanager
async def _lifespan(app: FastAPI):
    init_database()
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="job-agent API",
        version="0.1.0",
        description="Read-only API over the job-agent SQLite tracker DB. "
                    "No submission endpoints exist by design — human-in-the-loop runs through the CLI.",
        lifespan=_lifespan,
    )
    init_database()

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "mode": "mock" if s.mock_mode else "live",
            "dry_run": s.dry_run,
            "user_approval_required": s.user_approval_required,
            "auto_submit": s.auto_submit,
        }

    @app.get("/jobs")
    def list_jobs(
        limit: int = 50,
        priority: str | None = None,
        rejected: bool = False,
        is_duplicate: bool | None = None,
    ) -> list[dict]:
        with SessionLocal() as session:
            stmt = select(JobRow).order_by(desc(JobRow.match_score))
            if priority:
                stmt = stmt.where(JobRow.priority == priority)
            if not rejected:
                stmt = stmt.where(JobRow.rejected == False)  # noqa: E712
            if is_duplicate is not None:
                stmt = stmt.where(JobRow.is_duplicate == is_duplicate)
            stmt = stmt.limit(max(1, min(500, limit)))
            rows = session.scalars(stmt).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        with SessionLocal() as session:
            row = session.scalars(select(JobRow).where(JobRow.job_id == job_id)).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"job {job_id} not found")
        return _row_to_dict(row)

    @app.get("/applications")
    def list_applications(status: str | None = None, limit: int = 50) -> list[dict]:
        with SessionLocal() as session:
            stmt = select(ApplicationRow).order_by(desc(ApplicationRow.updated_at))
            if status:
                stmt = stmt.where(ApplicationRow.status == status)
            stmt = stmt.limit(max(1, min(500, limit)))
            rows = session.scalars(stmt).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/applications/{application_id}")
    def get_application(application_id: str) -> dict:
        with SessionLocal() as session:
            row = session.scalars(select(ApplicationRow).where(ApplicationRow.application_id == application_id)).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"application {application_id} not found")
        return _row_to_dict(row)

    @app.get("/companies")
    def list_companies(priority: bool | None = None) -> list[dict]:
        with SessionLocal() as session:
            stmt = select(CompanyRow)
            if priority is not None:
                stmt = stmt.where(CompanyRow.is_priority == priority)
            rows = session.scalars(stmt).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/messages")
    def list_messages(application_id: str | None = None) -> list[dict]:
        with SessionLocal() as session:
            stmt = select(MessageRow).order_by(desc(MessageRow.created_at))
            if application_id:
                app_row = session.scalars(select(ApplicationRow).where(ApplicationRow.application_id == application_id)).first()
                if app_row:
                    stmt = stmt.where(MessageRow.application_id == app_row.id)
            rows = session.scalars(stmt).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/emails")
    def list_emails(application_id: str | None = None) -> list[dict]:
        with SessionLocal() as session:
            stmt = select(EmailRow).order_by(desc(EmailRow.created_at))
            if application_id:
                app_row = session.scalars(select(ApplicationRow).where(ApplicationRow.application_id == application_id)).first()
                if app_row:
                    stmt = stmt.where(EmailRow.application_id == app_row.id)
            rows = session.scalars(stmt).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/followups")
    def list_followups() -> list[dict]:
        with SessionLocal() as session:
            rows = session.scalars(select(FollowupRow).order_by(FollowupRow.due_at)).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/harban/leads")
    def list_client_leads(stage: str | None = None, limit: int = 50) -> list[dict]:
        with SessionLocal() as session:
            stmt = select(ClientLeadRow).order_by(desc(ClientLeadRow.score))
            if stage:
                stmt = stmt.where(ClientLeadRow.stage == stage)
            stmt = stmt.limit(max(1, min(500, limit)))
            rows = session.scalars(stmt).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/harban/companies")
    def list_client_companies() -> list[dict]:
        with SessionLocal() as session:
            rows = session.scalars(select(ClientCompanyRow)).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/harban/opportunities")
    def list_client_opportunities(classification: str | None = None) -> list[dict]:
        with SessionLocal() as session:
            stmt = select(ClientOpportunityRow).order_by(desc(ClientOpportunityRow.harban_client_score))
            if classification:
                stmt = stmt.where(ClientOpportunityRow.classification == classification)
            rows = session.scalars(stmt).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/harban/outreach-drafts")
    def list_outreach_drafts(lead_id: str | None = None) -> list[dict]:
        with SessionLocal() as session:
            stmt = select(ClientInteractionRow).order_by(desc(ClientInteractionRow.created_at))
            if lead_id:
                stmt = stmt.where(ClientInteractionRow.lead_id == lead_id)
            rows = session.scalars(stmt).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/submission-evidence")
    def list_submission_evidence(outcome: str | None = None) -> list[dict]:
        with SessionLocal() as session:
            stmt = select(SubmissionEvidenceRow).order_by(desc(SubmissionEvidenceRow.submitted_at))
            if outcome:
                stmt = stmt.where(SubmissionEvidenceRow.outcome == outcome)
            rows = session.scalars(stmt).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/interviews")
    def list_interviews(application_id: str | None = None) -> list[dict]:
        with SessionLocal() as session:
            stmt = select(InterviewRow).order_by(desc(InterviewRow.created_at))
            if application_id:
                app_row = session.scalars(select(ApplicationRow).where(ApplicationRow.application_id == application_id)).first()
                if app_row:
                    stmt = stmt.where(InterviewRow.application_id == app_row.id)
            rows = session.scalars(stmt).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/search-runs")
    def list_search_runs(limit: int = 20) -> list[dict]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(SearchRunRow).order_by(desc(SearchRunRow.started_at)).limit(max(1, min(500, limit)))
            ).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/audit-logs")
    def list_audit_logs(limit: int = 50, event: str | None = None) -> list[dict]:
        with SessionLocal() as session:
            stmt = select(AuditLogRow).order_by(desc(AuditLogRow.created_at))
            if event:
                stmt = stmt.where(AuditLogRow.event == event)
            stmt = stmt.limit(max(1, min(500, limit)))
            rows = session.scalars(stmt).all()
        return [_row_to_dict(r) for r in rows]

    @app.get("/dashboard")
    def dashboard() -> dict:
        with SessionLocal() as session:
            jobs = session.scalars(select(JobRow)).all()
            apps = session.scalars(select(ApplicationRow)).all()
            runs = session.scalars(select(SearchRunRow).order_by(desc(SearchRunRow.started_at))).all()
            emails_count = session.scalar(select(func.count()).select_from(EmailRow)) or 0
            messages_count = session.scalar(select(func.count()).select_from(MessageRow)) or 0
            followups_count = session.scalar(select(func.count()).select_from(FollowupRow)) or 0

        canonical = [j for j in jobs if not j.is_duplicate]
        rejected = [j for j in jobs if j.rejected]
        kept = [j for j in canonical if not j.rejected]

        def _match(j: JobRow, needle: str) -> bool:
            return needle in (j.location or "").lower()

        tier_counts: dict[str, int] = {}
        for j in kept:
            tier_counts[j.priority] = tier_counts.get(j.priority, 0) + 1

        latest_run = runs[0] if runs else None
        return {
            "jobs_discovered": len(jobs),
            "jobs_after_dedup": len(canonical),
            "duplicates_removed": sum(1 for j in jobs if j.is_duplicate),
            "jobs_rejected": len(rejected),
            "high_match": sum(1 for j in kept if j.match_score >= 85),
            "apply_now": sum(1 for j in kept if j.match_score >= 75),
            "part_time": sum(1 for j in kept if j.employment_type == "part_time"),
            "remote": sum(1 for j in kept if j.remote.startswith("remote")),
            "gurugram": sum(1 for j in kept if _match(j, "gur") or _match(j, "cyber")),
            "noida": sum(1 for j in kept if _match(j, "noida")),
            "ncr_other": sum(1 for j in kept if _match(j, "delhi") or _match(j, "faridabad")),
            "global_remote": sum(1 for j in kept if j.remote in {"remote_global", "remote_global_unverified"}),
            "tier_counts": tier_counts,
            "applications_total": len(apps),
            "applications_review_required": sum(1 for a in apps if a.status == "REVIEW_REQUIRED"),
            "messages_total": messages_count,
            "emails_total": emails_count,
            "followups_total": followups_count,
            "latest_search_run_at": latest_run.started_at.isoformat() if latest_run else None,
            "pipeline_funnel": {
                "Discovered": len(jobs),
                "Canonical (after dedup)": len(canonical),
                "Matched (after hard rules)": len(kept),
                "High priority (>=85)": sum(1 for j in kept if j.match_score >= 85),
                "Applications prepared": len(apps),
            },
        }

    return app


app = create_app()
