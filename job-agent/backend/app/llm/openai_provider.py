from __future__ import annotations

import os
from typing import Any

from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider
from app.profile import Profile
from app.schemas import Job


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError("openai package not installed; `pip install openai`") from e
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self._client = OpenAI(api_key=api_key)
        self._mock = MockLLMProvider()

    def _chat(self, system: str, user: str, max_tokens: int = 800) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip()

    def analyze_job(self, job: Job) -> dict[str, Any]:
        return self._mock.analyze_job(job)

    def score_job(self, job: Job, profile: Profile) -> dict[str, Any]:
        return self._mock.score_job(job, profile)

    def generate_resume_rationale(self, job: Job, profile: Profile, variant_name: str) -> str:
        return self._mock.generate_resume_rationale(job, profile, variant_name)

    def generate_cover_letter(self, job: Job, profile: Profile) -> str:
        try:
            facts = "\n".join(f"- {f.key}: {f.value}" for f in profile.to_fact_list()[:40])
            system = (
                "You write short, truthful cover letters strictly from provided facts. "
                "Never invent experience, companies, degrees, certifications, or dates. "
                "If a required skill is missing from facts, note it as a gap rather than claiming it. "
                "4-6 short paragraphs. Sign with the applicant's name, email, phone."
            )
            user = (
                f"Facts about the applicant:\n{facts}\n\n"
                f"Job:\nCompany: {job.company}\nRole: {job.title}\nLocation: {job.location}\n"
                f"Description (first 2000 chars):\n{(job.description or '')[:2000]}\n\n"
                f"Write a tailored cover letter."
            )
            return self._chat(system, user, max_tokens=600)
        except Exception:
            return self._mock.generate_cover_letter(job, profile)

    def generate_email(self, job: Job, profile: Profile, recipient: str | None = None) -> dict[str, str]:
        return self._mock.generate_email(job, profile, recipient=recipient)

    def answer_application_question(self, question: str, job: Job, profile: Profile) -> dict[str, Any]:
        return self._mock.answer_application_question(question, job, profile)

    def detect_scam(self, job: Job) -> dict[str, Any]:
        return self._mock.detect_scam(job)

    def deduplicate_jobs(self, a: Job, b: Job) -> dict[str, Any]:
        return self._mock.deduplicate_jobs(a, b)
