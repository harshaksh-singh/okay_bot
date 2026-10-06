from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.discovery import SourceContext, get_registry


class DiscoveryAgent(BaseAgent):
    name = "discovery"

    def run(self, context: AgentContext, previous: list[AgentResult]) -> AgentResult:
        from app.config import get_settings
        r = self._start()
        s = get_settings()
        registry = get_registry()
        effective_limit = context.limit_per_source
        if s.discovery_pilot_mode:
            if effective_limit is None or effective_limit > s.discovery_pilot_max_per_source:
                effective_limit = s.discovery_pilot_max_per_source
                r.notes.append(f"discovery_pilot_mode=true; capping each source at {effective_limit} jobs")
        ctx = SourceContext(
            queries=context.discovery_queries,
            locations=context.discovery_locations,
            employment_types=context.employment_types,
            remote_only=context.remote_only,
            limit=effective_limit,
        )
        for source in registry.enabled():
            try:
                sr = source.discover(ctx)
                if sr.errors:
                    for e in sr.errors:
                        r.errors.append(f"{source.source_id.value}: {e}")
                r.jobs.extend(sr.jobs)
                r.notes.append(f"{source.source_id.value}: discovered {len(sr.jobs)} jobs")
            except Exception as e:
                r.errors.append(f"{source.source_id.value} raised: {e!r}")

        r.metadata["sources_run"] = [s.source_id.value for s in registry.enabled()]
        r.metadata["jobs_discovered"] = len(r.jobs)
        r.mark_done()
        return r
