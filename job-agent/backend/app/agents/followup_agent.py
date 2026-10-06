from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.schemas.enums import ApplicationStatus


class FollowupAgent(BaseAgent):
    name = "followup"

    def run(self, context: AgentContext, previous: list[AgentResult]) -> AgentResult:
        r = self._start()
        applications = []
        for p in previous:
            if p.agent == "application":
                applications = p.metadata.get("applications", [])
                break

        today = datetime.utcnow().date()
        day5 = today + timedelta(days=5)
        day10 = today + timedelta(days=10)

        scheduled = []
        for app in applications:
            if app.status in {ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN, ApplicationStatus.OFFER}:
                continue
            scheduled.append({"application_id": app.application_id, "due_at": day5.isoformat(), "kind": "day-5"})
            scheduled.append({"application_id": app.application_id, "due_at": day10.isoformat(), "kind": "day-10"})

        r.metadata["followups_scheduled"] = scheduled
        r.metadata["followups_skipped"] = skipped_reasons
        r.notes.append(
            f"scheduled {len(scheduled)} follow-ups across {len(applications)} applications "
            f"({len(skipped_reasons)} skipped by no-follow-up policy)"
        )
        r.mark_done()
        return r
