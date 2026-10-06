from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent


class ResearchAgent(BaseAgent):
    name = "research"

    def run(self, context: AgentContext, previous: list[AgentResult]) -> AgentResult:
        r = self._start()
        incoming = []
        for p in previous:
            if p.agent == "matching":
                incoming = p.jobs
                break

        research_notes: dict[str, dict] = {}
        for job in incoming:
            notes: dict = {}
            if job.company.strip().lower() in {c.lower() for c in context.profile.priority_companies}:
                notes["priority"] = "listed in user's priority companies"
            if job.scam_risk.value in {"medium", "high"}:
                notes["caution"] = f"scam signal: {job.scam_risk.value}"
            notes["match_score"] = job.match_score
            notes["priority_tier"] = job.priority.value
            research_notes[job.job_id] = notes

        r.jobs = incoming
        r.metadata["research_notes"] = research_notes
        r.notes.append(f"researched {len(incoming)} jobs (lightweight Phase 1)")
        r.mark_done()
        return r
