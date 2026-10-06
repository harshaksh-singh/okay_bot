from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.dedup.deduplicator import Deduplicator


class ExtractionAgent(BaseAgent):
    name = "extraction"

    def run(self, context: AgentContext, previous: list[AgentResult]) -> AgentResult:
        r = self._start()
        incoming: list = []
        for p in previous:
            if p.agent == "discovery":
                incoming = p.jobs
                break

        dedup = Deduplicator()
        clusters = dedup.cluster(incoming)
        canonical_jobs = [c.canonical for c in clusters if c.canonical is not None]
        duplicates_removed = sum(len(c.members) - 1 for c in clusters)

        r.jobs = canonical_jobs
        r.metadata["clusters"] = len(clusters)
        r.metadata["duplicates_removed"] = duplicates_removed
        r.notes.append(f"extracted {len(canonical_jobs)} canonical jobs ({duplicates_removed} duplicates folded)")
        r.mark_done()
        return r
