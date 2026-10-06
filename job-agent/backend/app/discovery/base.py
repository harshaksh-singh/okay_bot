from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from app.schemas import Job
from app.schemas.enums import JobSource


@dataclass
class SourceContext:
    queries: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    employment_types: list[str] = field(default_factory=list)
    remote_only: bool = False
    posted_within_hours: int | None = None
    limit: int | None = None
    extras: dict[str, str] = field(default_factory=dict)


@dataclass
class SourceResult:
    source: JobSource
    jobs: list[Job] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def count(self) -> int:
        return len(self.jobs)


class BaseSource(ABC):
    source_id: JobSource = JobSource.MANUAL
    requires_browser: bool = False
    requires_credentials: bool = False
    requires_api_key: bool = False
    enabled_by_default: bool = False
    rate_limit_per_minute: int = 10

    @abstractmethod
    def is_enabled(self) -> bool: ...

    @abstractmethod
    def discover(self, context: SourceContext) -> SourceResult: ...

    def display_name(self) -> str:
        return self.source_id.value
