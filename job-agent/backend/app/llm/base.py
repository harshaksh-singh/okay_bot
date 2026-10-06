from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.profile import Profile
from app.schemas import Job


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    tokens_in: int = 0
    tokens_out: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def analyze_job(self, job: Job) -> dict[str, Any]: ...

    @abstractmethod
    def score_job(self, job: Job, profile: Profile) -> dict[str, Any]: ...

    @abstractmethod
    def generate_resume_rationale(self, job: Job, profile: Profile, variant_name: str) -> str: ...

    @abstractmethod
    def generate_cover_letter(self, job: Job, profile: Profile) -> str: ...

    @abstractmethod
    def generate_email(self, job: Job, profile: Profile, recipient: str | None = None) -> dict[str, str]: ...

    @abstractmethod
    def answer_application_question(self, question: str, job: Job, profile: Profile) -> dict[str, Any]: ...

    @abstractmethod
    def detect_scam(self, job: Job) -> dict[str, Any]: ...

    @abstractmethod
    def deduplicate_jobs(self, a: Job, b: Job) -> dict[str, Any]: ...
