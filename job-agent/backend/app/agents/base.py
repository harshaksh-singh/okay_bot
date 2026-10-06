from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.profile import Profile
from app.schemas import Job


@dataclass
class AgentContext:
    profile: Profile
    jobs: list[Job] = field(default_factory=list)
    discovery_queries: list[str] = field(default_factory=list)
    discovery_locations: list[str] = field(default_factory=list)
    employment_types: list[str] = field(default_factory=list)
    remote_only: bool = False
    limit_per_source: int | None = None
    dry_run: bool = True
    require_user_approval: bool = True
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    agent: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    jobs: list[Job] = field(default_factory=list)
    rejected_jobs: list[tuple[Job, list[str]]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def mark_done(self) -> None:
        self.finished_at = datetime.utcnow()


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, context: AgentContext, previous: list[AgentResult]) -> AgentResult: ...

    def _start(self) -> AgentResult:
        return AgentResult(agent=self.name)
