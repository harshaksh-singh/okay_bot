from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.harban import (
    ClientCompany,
    ClientContact,
    ClientLead,
    ClientOpportunity,
    ClientStage,
    DualOpportunityClassifier,
    HarbanClientScorer,
    OpportunityType,
)
from app.harban.outreach import HarbanOutreachGenerator, OutreachLimiter, schedule_followup_dates
from app.harban.services import match_services
from app.observability import get_logger

log = get_logger("agent.harban")


def _canonicalize(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return base or "unknown"


def _lead_id(canonical: str) -> str:
    return "lead_" + hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]


def _opportunity_id(job_id: str) -> str:
    return "opp_" + hashlib.sha1(job_id.encode("utf-8")).hexdigest()[:12]


class HarbanAgent(BaseAgent):
    name = "harban"

    def __init__(self) -> None:
        self.scorer = HarbanClientScorer()
        self.classifier = DualOpportunityClassifier()

    def run(self, context: AgentContext, previous: list[AgentResult]) -> AgentResult:
        r = self._start()

        from app.config import get_settings
        if not get_settings().harban_enabled:
            r.notes.append("harban_enabled=false; skipping Harban client discovery")
            r.mark_done()
            return r
        if not get_settings().client_discovery_enabled:
            r.notes.append("client_discovery_enabled=false; skipping Harban client discovery")
            r.metadata["counts"] = {"opportunities_total": 0, "leads_discovered": 0, "outreach_drafted": 0}
            r.mark_done()
            return r

        matched = []
        rejected = []
        for p in previous:
            if p.agent == "matching":
                matched = p.jobs
                rejected = [j for j, _ in p.rejected_jobs]
                break

        all_jobs = list(matched) + list(rejected)
        leads: list[ClientLead] = []
        companies: dict[str, ClientCompany] = {}
        opportunities: list[ClientOpportunity] = []
        outreach_drafts: list[dict] = []

        outreach_gen = HarbanOutreachGenerator(context.profile)
        limiter = OutreachLimiter()

        settings = get_settings()

        for job in all_jobs:
            breakdown, ai_reasons, buying_reasons = self.scorer.score_job_as_client_lead(job)
            client_score = breakdown.total()
            classification = self.classifier.classify(personal_score=job.match_score, client_score=client_score)

            opp = ClientOpportunity(
                opportunity_id=_opportunity_id(job.job_id),
                source_job_id=job.job_id,
                company_canonical=_canonicalize(job.company),
                description=(job.description or "")[:4000],
                classification=classification,
                personal_employment_score=job.match_score,
                harban_client_score=client_score,
                rationale=ai_reasons + buying_reasons,
            )
            opportunities.append(opp)

            if classification in {OpportunityType.CLIENT, OpportunityType.BOTH} and client_score >= settings.harban_client_score_threshold:
                canon = _canonicalize(job.company)
                if canon not in companies:
                    companies[canon] = ClientCompany(
                        canonical_name=canon,
                        display_name=job.company,
                        website=None,
                        headquarters=job.location or None,
                        ai_usage_signals=ai_reasons,
                        hiring_signals=[f"job post: {job.title}"] + buying_reasons,
                        discovery_source="matched_job_posting",
                    )

                lead = ClientLead(
                    lead_id=_lead_id(canon),
                    company_canonical=canon,
                    stage=ClientStage.DISCOVERED,
                    score=round(client_score, 2),
                    score_breakdown=breakdown.as_dict(),
                    ai_relevance_reasons=ai_reasons,
                    buying_signal_reasons=buying_reasons,
                    opportunity_type=classification,
                    linked_job_id=job.job_id,
                )
                leads.append(lead)

                signals = (buying_reasons[:2] + ai_reasons[:1])[:3]
                if signals and settings.client_outreach_enabled:
                    can_send, _ = limiter.can_add_prospect()
                    if can_send:
                        limiter.record_prospect()
                        template_body = outreach_gen.generate_outreach_template(
                            company=companies[canon],
                            signals=signals,
                            client_need_text=job.description or "",
                        )
                        draft_status = "BLOCKED_REQUIRES_REAL_CONTACT" if settings.requires_real_contact else "DRAFT_READY_FOR_REVIEW"
                        draft_notes = (
                            "No verified public professional contact has been sourced for this company. "
                            "Per brief Section 30 and REQUIRES_REAL_CONTACT=true, this draft is BLOCKED "
                            "from any send until the user supplies a real recipient from a public professional profile."
                        ) if settings.requires_real_contact else (
                            "REQUIRES_REAL_CONTACT=false; user has acknowledged responsibility for recipient legitimacy before any send."
                        )
                        outreach_drafts.append({
                            "lead_id": lead.lead_id,
                            "company": job.company,
                            "channel": "email",
                            "subject": f"Potential AI/LLM engineering support for {job.company}",
                            "body": template_body,
                            "recipient": None,
                            "personalized_signals": list(signals),
                            "services_referenced": [],
                            "draft_only": True,
                            "status": draft_status,
                            "notes": draft_notes,
                        })
                elif signals and not settings.client_outreach_enabled:
                    r.notes.append(f"client_outreach_enabled=false; skipped outreach draft for {job.company}")

        from datetime import date
        today = date.today()
        followups_scheduled: list[dict] = []
        eligible_lead_ids: set[str] = set()
        for d in outreach_drafts:
            lid = d.get("lead_id")
            status = d.get("status", "")
            if lid and not status.startswith("BLOCKED_") and d.get("recipient"):
                eligible_lead_ids.add(lid)

        for lead in leads:
            if lead.lead_id not in eligible_lead_ids:
                continue
            for kind, due in schedule_followup_dates(today):
                followups_scheduled.append({
                    "lead_id": lead.lead_id,
                    "due_at": due.isoformat(),
                    "kind": kind,
                    "status": "pending",
                })

        r.metadata["opportunities"] = [o.model_dump(mode="json") for o in opportunities]
        r.metadata["leads"] = [l.model_dump(mode="json") for l in leads]
        r.metadata["companies"] = [c.model_dump(mode="json") for c in companies.values()]
        r.metadata["outreach_drafts"] = outreach_drafts
        r.metadata["client_followups_scheduled"] = followups_scheduled
        r.metadata["counts"] = {
            "opportunities_total": len(opportunities),
            "classified_job": sum(1 for o in opportunities if o.classification == OpportunityType.JOB),
            "classified_client": sum(1 for o in opportunities if o.classification == OpportunityType.CLIENT),
            "classified_both": sum(1 for o in opportunities if o.classification == OpportunityType.BOTH),
            "classified_neither": sum(1 for o in opportunities if o.classification == OpportunityType.NEITHER),
            "leads_discovered": len(leads),
            "outreach_drafted": len(outreach_drafts),
            "client_followups_scheduled": len(followups_scheduled),
        }
        r.notes.append(
            f"harban: {len(opportunities)} opportunities classified; {len(leads)} qualified client leads; "
            f"{len(outreach_drafts)} outreach drafts prepared"
        )
        r.mark_done()
        return r
