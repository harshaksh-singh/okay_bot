from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.email import EmailDraft, EmailDrafter
from app.llm import get_llm_provider


class CommunicationAgent(BaseAgent):
    name = "communication"

    def __init__(self, drafter: EmailDrafter | None = None) -> None:
        self.drafter = drafter

    def run(self, context: AgentContext, previous: list[AgentResult]) -> AgentResult:
        from app.config import get_settings
        r = self._start()
        s = get_settings()
        llm = get_llm_provider()
        drafter = self.drafter or EmailDrafter()
        email_mode = "READY_TO_SEND" if (s.auto_email_approved and s.pre_approved_applications) else "DRAFT"
        message_mode = "READY_TO_SEND" if (s.auto_message_approved and s.pre_approved_applications) else "DRAFT"

        applications = []
        for p in previous:
            if p.agent == "application":
                applications = p.metadata.get("applications", [])
                break

        matched_jobs = []
        for p in previous:
            if p.agent == "matching":
                matched_jobs = p.jobs
                break
        research_jobs = []
        for p in previous:
            if p.agent == "research":
                research_jobs = p.jobs
                break
        if research_jobs and not matched_jobs:
            matched_jobs = research_jobs

        job_by_id = {j.job_id: j for j in matched_jobs}

        emails: list[dict] = []
        email_paths: list[str] = []
        recruiter_messages: list[dict] = []

        for app in applications:
            job = job_by_id.get(app.job_id)
            if not job:
                continue

            if job.application_email:
                e = llm.generate_email(job, context.profile, recipient=job.application_email)
                emails.append({"job_id": job.job_id, **e, "to": job.application_email})
                try:
                    attachments = [app.resume_path] if app.resume_path else []
                    draft = EmailDraft(
                        to=e["to"],
                        subject=e["subject"],
                        body=e["body"],
                        sender=str(context.profile.email),
                        attachments=attachments,
                    )
                    path = drafter.draft(draft, filename=f"{app.application_id}.eml")
                    email_paths.append(str(path))
                except Exception as ex:
                    r.errors.append(f"email draft failed for {job.job_id}: {ex}")

            msg = (
                f"Hi {{{{recruiter_first_name}}}} — I noticed the {job.title} role at {job.company} "
                f"and wanted to say hi. My background: {context.profile.headline}. "
                f"Would it be okay to share a resume?"
            )
            recruiter_messages.append({"job_id": job.job_id, "message": msg, "channel": "linkedin"})

        r.metadata["emails_drafted"] = len(emails)
        r.metadata["emails"] = emails
        r.metadata["email_draft_paths"] = email_paths
        r.metadata["recruiter_messages"] = recruiter_messages
        r.metadata["email_mode"] = email_mode
        r.metadata["message_mode"] = message_mode
        r.notes.append(
            f"drafted {len(emails)} emails ({len(email_paths)} .eml written) [mode={email_mode}], "
            f"{len(recruiter_messages)} recruiter messages [mode={message_mode}]. "
            f"Actual send transport (OAuth) deferred to Phase 5b."
        )
        r.mark_done()
        return r
