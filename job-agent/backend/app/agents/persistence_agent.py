from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.database import SessionLocal, init_database
from app.database.models import (
    ApplicationRow,
    AuditLogRow,
    ClientCompanyRow,
    ClientFollowupRow,
    ClientInteractionRow,
    ClientLeadRow,
    ClientOpportunityRow,
    EmailRow,
    FollowupRow,
    JobRow,
    MessageRow,
    SearchRunRow,
)
from app.observability import get_logger
from app.schemas import Job
from app.schemas.application import Application

log = get_logger("persistence")


def _job_to_row(j: Job) -> dict:
    s = j.salary
    return dict(
        job_id=j.job_id,
        source=j.source.value,
        source_job_id=j.source_job_id,
        company_name=j.company,
        title=j.title,
        location=j.location or "",
        remote=j.remote.value,
        employment_type=j.employment_type.value,
        shift=j.shift.value,
        hours_per_week=j.hours_per_week,
        salary_min=s.min_value,
        salary_max=s.max_value,
        salary_currency=s.currency,
        salary_unit=s.unit,
        salary_raw=s.raw,
        description=(j.description or "")[:8000],
        requirements=list(j.requirements or []),
        preferred_skills=list(j.preferred_skills or []),
        responsibilities=list(j.responsibilities or []),
        application_url=str(j.application_url) if j.application_url else None,
        application_method=j.application_method.value,
        application_email=j.application_email,
        posted_at=j.posted_at,
        deadline=j.deadline,
        discovered_at=j.discovered_at,
        match_score=j.match_score,
        priority=j.priority.value,
        score_breakdown=j.score_breakdown.as_dict() if hasattr(j.score_breakdown, "as_dict") else dict(j.score_breakdown or {}),
        duplicate_group=j.duplicate_group,
        is_duplicate=j.is_duplicate,
        reason_for_match=list(j.reason_for_match or []),
        missing_requirements=list(j.missing_requirements or []),
        scam_risk=j.scam_risk.value,
        scam_reasons=list(j.scam_reasons or []),
        rejected=j.rejected,
        rejection_reasons=list(j.rejection_reasons or []),
        tags=list(j.tags or []),
        seniority=j.seniority,
    )


def _app_to_row(app: Application) -> dict:
    return dict(
        application_id=app.application_id,
        job_id=app.job_id,
        status=app.status.value,
        application_method=app.application_method.value,
        resume_variant=app.resume_variant,
        resume_path=str(app.resume_path) if app.resume_path else None,
        cover_letter_path=str(app.cover_letter_path) if app.cover_letter_path else None,
        cover_letter_text=app.cover_letter_text,
        form_answers=[a.model_dump() for a in app.form_answers],
        pending_user_inputs=list(app.pending_user_inputs or []),
        submitted_at=app.submitted_at,
        submission_evidence=app.submission_evidence,
        approved_by_user=app.approved_by_user,
        approved_at=app.approved_at,
        followup_due_at=app.followup_due_at,
        last_followup_at=app.last_followup_at,
        status_history=[
            {"status": s.value if hasattr(s, "value") else str(s), "at": t.isoformat() if hasattr(t, "isoformat") else str(t), "note": n}
            for s, t, n in app.status_history
        ],
        notes=app.notes,
    )


class PersistenceAgent(BaseAgent):
    name = "persistence"

    def run(self, context: AgentContext, previous: list[AgentResult]) -> AgentResult:
        r = self._start()

        try:
            init_database()
        except Exception as e:
            r.errors.append(f"persistence.init_db failed: {e!r}")
            r.mark_done()
            return r

        discovery = next((p for p in previous if p.agent == "discovery"), None)
        extraction = next((p for p in previous if p.agent == "extraction"), None)
        matching = next((p for p in previous if p.agent == "matching"), None)
        application_r = next((p for p in previous if p.agent == "application"), None)
        communication = next((p for p in previous if p.agent == "communication"), None)
        followup = next((p for p in previous if p.agent == "followup"), None)

        jobs_to_save: list[Job] = []
        if extraction:
            jobs_to_save.extend(extraction.jobs)
        if matching:
            for j in matching.jobs:
                if j not in jobs_to_save:
                    jobs_to_save.append(j)
            for j, _ in matching.rejected_jobs:
                if j not in jobs_to_save:
                    jobs_to_save.append(j)

        apps_to_save: list[Application] = []
        if application_r:
            apps_to_save = list(application_r.metadata.get("applications", []))

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        jobs_written = 0
        jobs_updated = 0
        apps_written = 0
        apps_updated = 0

        try:
            with SessionLocal() as session:
                for job in jobs_to_save:
                    existing = session.scalars(select(JobRow).where(JobRow.job_id == job.job_id)).first()
                    row_data = _job_to_row(job)
                    if existing:
                        for k, v in row_data.items():
                            setattr(existing, k, v)
                        jobs_updated += 1
                    else:
                        session.add(JobRow(**row_data))
                        jobs_written += 1

                session.flush()

                for app in apps_to_save:
                    existing_app = session.scalars(select(ApplicationRow).where(ApplicationRow.application_id == app.application_id)).first()
                    row_data = _app_to_row(app)
                    if existing_app:
                        for k, v in row_data.items():
                            setattr(existing_app, k, v)
                        apps_updated += 1
                    else:
                        session.add(ApplicationRow(**row_data))
                        apps_written += 1

                session.flush()

                app_id_lookup_by_job = {
                    app.job_id: session.scalars(
                        select(ApplicationRow).where(ApplicationRow.application_id == app.application_id)
                    ).first()
                    for app in apps_to_save
                }
                app_id_lookup_by_app = {
                    app.application_id: session.scalars(
                        select(ApplicationRow).where(ApplicationRow.application_id == app.application_id)
                    ).first()
                    for app in apps_to_save
                }

                if communication:
                    emails = communication.metadata.get("emails", [])
                    email_paths = communication.metadata.get("email_draft_paths", [])
                    msgs = communication.metadata.get("recruiter_messages", [])

                    for m in msgs:
                        app_row = app_id_lookup_by_job.get(m.get("job_id"))
                        if app_row is None:
                            continue
                        existing = session.scalars(
                            select(MessageRow).where(
                                MessageRow.application_id == app_row.id,
                                MessageRow.channel == m.get("channel", "linkedin"),
                                MessageRow.direction == "outbound",
                            )
                        ).first()
                        if existing:
                            existing.body = m.get("message", "")
                        else:
                            session.add(MessageRow(
                                application_id=app_row.id,
                                channel=m.get("channel", "linkedin"),
                                direction="outbound",
                                subject=None,
                                body=m.get("message", ""),
                            ))

                    for idx, e in enumerate(emails):
                        app_row = app_id_lookup_by_job.get(e.get("job_id"))
                        if app_row is None:
                            continue
                        existing_email = session.scalars(
                            select(EmailRow).where(
                                EmailRow.application_id == app_row.id,
                                EmailRow.to_address == e.get("to", ""),
                                EmailRow.subject == e.get("subject", ""),
                            )
                        ).first()
                        attachment_paths = [email_paths[idx]] if idx < len(email_paths) else []
                        if existing_email:
                            existing_email.body = e.get("body", "")
                            existing_email.attachments = attachment_paths
                            existing_email.status = "draft"
                        else:
                            session.add(EmailRow(
                                application_id=app_row.id,
                                to_address=e.get("to", ""),
                                from_address=str(context.profile.email),
                                subject=e.get("subject", ""),
                                body=e.get("body", ""),
                                attachments=attachment_paths,
                                status="draft",
                            ))

                if followup:
                    scheduled = followup.metadata.get("followups_scheduled", [])
                    for item in scheduled:
                        app_row = app_id_lookup_by_app.get(item.get("application_id"))
                        if not app_row:
                            continue
                        try:
                            from datetime import date as _date
                            due = _date.fromisoformat(item["due_at"])
                        except Exception:
                            continue
                        kind = item.get("kind", "application")
                        existing_fu = session.scalars(
                            select(FollowupRow).where(
                                FollowupRow.application_id == app_row.id,
                                FollowupRow.kind == kind,
                            )
                        ).first()
                        if existing_fu:
                            existing_fu.due_at = due
                            existing_fu.status = existing_fu.status or "pending"
                        else:
                            session.add(FollowupRow(
                                application_id=app_row.id,
                                due_at=due,
                                kind=kind,
                                status="pending",
                            ))

                harban_result = next((p for p in previous if p.agent == "harban"), None)
                if harban_result:
                    for comp_data in harban_result.metadata.get("companies", []):
                        canon = comp_data.get("canonical_name")
                        if not canon:
                            continue
                        existing_comp = session.scalars(select(ClientCompanyRow).where(ClientCompanyRow.canonical_name == canon)).first()
                        row_data = dict(
                            canonical_name=canon,
                            display_name=comp_data.get("display_name", canon),
                            website=comp_data.get("website"),
                            industry=comp_data.get("industry"),
                            headquarters=comp_data.get("headquarters"),
                            size_category=comp_data.get("size_category"),
                            funding_signals=comp_data.get("funding_signals", []),
                            technology_signals=comp_data.get("technology_signals", []),
                            ai_usage_signals=comp_data.get("ai_usage_signals", []),
                            hiring_signals=comp_data.get("hiring_signals", []),
                            discovery_source=comp_data.get("discovery_source", "matched_job_posting"),
                            notes=comp_data.get("notes"),
                        )
                        if existing_comp:
                            for k, v in row_data.items():
                                setattr(existing_comp, k, v)
                        else:
                            session.add(ClientCompanyRow(**row_data))

                    for lead_data in harban_result.metadata.get("leads", []):
                        lid = lead_data.get("lead_id")
                        if not lid:
                            continue
                        existing_lead = session.scalars(select(ClientLeadRow).where(ClientLeadRow.lead_id == lid)).first()
                        lead_row_data = dict(
                            lead_id=lid,
                            company_canonical=lead_data.get("company_canonical", ""),
                            contact_full_name=lead_data.get("contact_full_name"),
                            stage=lead_data.get("stage", "DISCOVERED"),
                            score=float(lead_data.get("score") or 0.0),
                            score_breakdown=lead_data.get("score_breakdown", {}),
                            ai_relevance_reasons=lead_data.get("ai_relevance_reasons", []),
                            buying_signal_reasons=lead_data.get("buying_signal_reasons", []),
                            opportunity_type=lead_data.get("opportunity_type", "CLIENT"),
                            linked_job_id=lead_data.get("linked_job_id"),
                            stage_history=[],
                        )
                        if existing_lead:
                            for k, v in lead_row_data.items():
                                setattr(existing_lead, k, v)
                        else:
                            session.add(ClientLeadRow(**lead_row_data))

                    for opp_data in harban_result.metadata.get("opportunities", []):
                        oid = opp_data.get("opportunity_id")
                        if not oid:
                            continue
                        existing_opp = session.scalars(select(ClientOpportunityRow).where(ClientOpportunityRow.opportunity_id == oid)).first()
                        opp_row_data = dict(
                            opportunity_id=oid,
                            source_job_id=opp_data.get("source_job_id"),
                            company_canonical=opp_data.get("company_canonical", ""),
                            description=opp_data.get("description", "")[:5000],
                            classification=opp_data.get("classification", "NEITHER"),
                            personal_employment_score=float(opp_data.get("personal_employment_score") or 0.0),
                            harban_client_score=float(opp_data.get("harban_client_score") or 0.0),
                            rationale=opp_data.get("rationale", []),
                        )
                        if existing_opp:
                            for k, v in opp_row_data.items():
                                setattr(existing_opp, k, v)
                        else:
                            session.add(ClientOpportunityRow(**opp_row_data))

                    for item in harban_result.metadata.get("client_followups_scheduled", []):
                        lid = item.get("lead_id")
                        if not lid:
                            continue
                        try:
                            from datetime import date as _date
                            due = _date.fromisoformat(item["due_at"])
                        except Exception:
                            continue
                        kind = item.get("kind", "day-5")
                        existing_cfu = session.scalars(select(ClientFollowupRow).where(
                            ClientFollowupRow.lead_id == lid, ClientFollowupRow.kind == kind
                        )).first()
                        if existing_cfu:
                            existing_cfu.due_at = due
                        else:
                            session.add(ClientFollowupRow(
                                lead_id=lid,
                                due_at=due,
                                kind=kind,
                                status="pending",
                            ))

                    for draft in harban_result.metadata.get("outreach_drafts", []):
                        lid = draft.get("lead_id")
                        if not lid:
                            continue
                        existing_i = session.scalars(select(ClientInteractionRow).where(
                            ClientInteractionRow.lead_id == lid,
                            ClientInteractionRow.channel == draft.get("channel", "email"),
                            ClientInteractionRow.direction == "outbound",
                            ClientInteractionRow.draft_only == True,  # noqa: E712
                        )).first()
                        interaction_data = dict(
                            lead_id=lid,
                            channel=draft.get("channel", "email"),
                            direction="outbound",
                            subject=draft.get("subject"),
                            body=draft.get("body", ""),
                            personalized_signals=draft.get("personalized_signals", []),
                            draft_only=True,
                        )
                        if existing_i:
                            for k, v in interaction_data.items():
                                setattr(existing_i, k, v)
                        else:
                            session.add(ClientInteractionRow(**interaction_data))

                session.add(SearchRunRow(
                    started_at=now,
                    finished_at=now,
                    sources=(discovery.metadata.get("sources_run", []) if discovery else []),
                    queries=list(context.discovery_queries or []),
                    jobs_discovered=len(discovery.jobs) if discovery else 0,
                    jobs_new=jobs_written,
                    jobs_rejected=len(matching.rejected_jobs) if matching else 0,
                    duplicates_removed=(extraction.metadata.get("duplicates_removed", 0) if extraction else 0),
                    high_priority_count=matching.metadata.get("high_priority", 0) if matching else 0,
                    errors=[{"agent": p.agent, "error": e} for p in previous for e in p.errors],
                ))

                session.add(AuditLogRow(
                    event="pipeline_run_persisted",
                    actor="orchestrator",
                    subject_type="pipeline",
                    subject_id=now.isoformat(),
                    payload={
                        "jobs_written": jobs_written,
                        "jobs_updated": jobs_updated,
                        "apps_written": apps_written,
                        "apps_updated": apps_updated,
                    },
                ))

                for prev_result in previous:
                    session.add(AuditLogRow(
                        event=f"agent_{prev_result.agent}_completed",
                        actor=prev_result.agent,
                        subject_type="agent_run",
                        subject_id=now.isoformat(),
                        payload={
                            "agent": prev_result.agent,
                            "notes": list(prev_result.notes),
                            "error_count": len(prev_result.errors),
                            "errors": list(prev_result.errors)[:5],
                            "started_at": prev_result.started_at.isoformat() if prev_result.started_at else None,
                            "finished_at": prev_result.finished_at.isoformat() if prev_result.finished_at else None,
                            "result_count": len(prev_result.jobs) if hasattr(prev_result, "jobs") else 0,
                        },
                    ))

                session.commit()
        except Exception as e:
            r.errors.append(f"persistence.write failed: {e!r}")
            log.warning("persistence.write_failed", error=str(e))
            r.mark_done()
            return r

        r.metadata.update({
            "jobs_written": jobs_written,
            "jobs_updated": jobs_updated,
            "applications_written": apps_written,
            "applications_updated": apps_updated,
        })
        r.notes.append(
            f"persisted {jobs_written} new / {jobs_updated} updated jobs, "
            f"{apps_written} new / {apps_updated} updated applications"
        )
        r.mark_done()
        return r
