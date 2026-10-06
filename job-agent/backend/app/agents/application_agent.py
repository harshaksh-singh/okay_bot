from __future__ import annotations

import hashlib

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.applications.preparer import ApplicationPreparer
from app.schemas.application import Application
from app.schemas.enums import ApplicationStatus


class ApplicationAgent(BaseAgent):
    name = "application"

    def __init__(self) -> None:
        self.preparer = ApplicationPreparer()

    def run(self, context: AgentContext, previous: list[AgentResult]) -> AgentResult:
        r = self._start()
        incoming = []
        for p in previous:
            if p.agent == "research":
                incoming = p.jobs
                break
        if not incoming:
            for p in previous:
                if p.agent == "matching":
                    incoming = p.jobs
                    break

        prepared: list[Application] = []
        from app.config import get_settings as _gs
        _apply_floor = _gs().scoring_thresholds.consider
        top_jobs = [j for j in incoming if j.match_score >= _apply_floor][: context.extras.get("prepare_top_n", 25) if isinstance(context.extras.get("prepare_top_n", 25), int) else 25]

        for job in top_jobs:
            application = self.preparer.prepare(job, context.profile, dry_run=context.dry_run)
            if context.require_user_approval:
                application.status = ApplicationStatus.REVIEW_REQUIRED
            prepared.append(application)

        r.jobs = top_jobs
        r.metadata["prepared_applications"] = [app.application_id for app in prepared]
        r.metadata["pending_user_review"] = len([a for a in prepared if a.status == ApplicationStatus.REVIEW_REQUIRED])
        r.metadata["applications"] = prepared
        r.notes.append(
            f"prepared {len(prepared)} applications "
            f"(dry_run={context.dry_run}, require_approval={context.require_user_approval})"
        )
        r.mark_done()
        return r

    @staticmethod
    def application_id_for(job_id: str) -> str:
        return "app_" + hashlib.sha1(job_id.encode("utf-8")).hexdigest()[:12]
