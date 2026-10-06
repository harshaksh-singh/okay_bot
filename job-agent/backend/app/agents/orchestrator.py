from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.agents.application_agent import ApplicationAgent
from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.communication_agent import CommunicationAgent
from app.agents.compliance_agent import ComplianceAgent
from app.agents.discovery_agent import DiscoveryAgent
from app.agents.extraction_agent import ExtractionAgent
from app.agents.followup_agent import FollowupAgent
from app.agents.harban_agent import HarbanAgent
from app.agents.matching_agent import MatchingAgent
from app.agents.persistence_agent import PersistenceAgent
from app.agents.quality_agent import QualityAgent
from app.agents.research_agent import ResearchAgent
from app.agents.submission_agent import SubmissionAgent
from app.compliance import ComplianceViolation
from app.schemas import Job
from app.schemas.application import Application


@dataclass
class OrchestratorResult:
    context: AgentContext
    agent_results: list[AgentResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    finished_at: datetime | None = None
    halted_by_compliance: bool = False

    def get(self, agent_name: str) -> AgentResult | None:
        for r in self.agent_results:
            if r.agent == agent_name:
                return r
        return None

    @property
    def discovered_jobs(self) -> list[Job]:
        d = self.get("discovery")
        return d.jobs if d else []

    @property
    def canonical_jobs(self) -> list[Job]:
        d = self.get("extraction")
        return d.jobs if d else []

    @property
    def matched_jobs(self) -> list[Job]:
        d = self.get("matching")
        return d.jobs if d else []

    @property
    def rejected_jobs(self) -> list[tuple[Job, list[str]]]:
        d = self.get("matching")
        return d.rejected_jobs if d else []

    @property
    def applications(self) -> list[Application]:
        a = self.get("application")
        return a.metadata.get("applications", []) if a else []

    @property
    def errors(self) -> list[str]:
        out: list[str] = []
        for r in self.agent_results:
            out.extend(r.errors)
        return out


class JobAgentOrchestrator:
    def __init__(self, agents: list[BaseAgent] | None = None) -> None:
        self.agents: list[BaseAgent] = agents or [
            DiscoveryAgent(),
            ExtractionAgent(),
            MatchingAgent(),
            ResearchAgent(),
            ApplicationAgent(),
            CommunicationAgent(),
            FollowupAgent(),
            ComplianceAgent(),
            QualityAgent(),
        ]

    def run(self, context: AgentContext) -> OrchestratorResult:
        result = OrchestratorResult(context=context)
        for agent in self.agents:
            try:
                ar = agent.run(context, result.agent_results)
            except Exception as e:
                ar = AgentResult(agent=agent.name, errors=[f"{agent.name} raised: {e!r}"])
                ar.mark_done()
            result.agent_results.append(ar)
        result.finished_at = datetime.utcnow()
        return result
