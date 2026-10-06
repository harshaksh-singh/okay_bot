from __future__ import annotations

import difflib
import re
from typing import Any

from app.llm.base import LLMProvider
from app.profile import Profile
from app.schemas import Job


_SENSITIVE_KEYWORDS = {
    "salary expectation": "USER_INPUT_REQUIRED",
    "expected salary": "USER_INPUT_REQUIRED",
    "notice period": "USER_INPUT_REQUIRED",
    "current ctc": "USER_INPUT_REQUIRED",
    "expected ctc": "USER_INPUT_REQUIRED",
    "visa": "USER_INPUT_REQUIRED",
    "sponsorship": "USER_INPUT_REQUIRED",
    "willing to relocate": "USER_INPUT_REQUIRED",
    "earliest start date": "USER_INPUT_REQUIRED",
    "availability for interview": "USER_INPUT_REQUIRED",
    "years of experience": "DERIVED_FACT",
    "do you have experience with": "DERIVED_FACT",
}


class MockLLMProvider(LLMProvider):
    name = "mock"

    def analyze_job(self, job: Job) -> dict[str, Any]:
        text = f"{job.title}\n{job.description}".lower()
        signals = []
        for sig in ("python", "pytorch", "llm", "rag", "rlhf", "docker", "aws", "kubernetes"):
            if sig in text:
                signals.append(sig)
        return {
            "keywords": signals,
            "estimated_difficulty": "medium",
            "model": "deterministic",
        }

    def score_job(self, job: Job, profile: Profile) -> dict[str, Any]:
        from app.matching.scorer import MatchingEngine
        engine = MatchingEngine()
        breakdown, reasons, missing = engine.score(job, profile)
        return {
            "score_breakdown": breakdown.as_dict(),
            "reasons": reasons,
            "missing": missing,
        }

    def generate_resume_rationale(self, job: Job, profile: Profile, variant_name: str) -> str:
        return f"Selected '{variant_name}' resume because {job.title} at {job.company} best aligns with its highlighted skill set."

    def generate_cover_letter(self, job: Job, profile: Profile) -> str:
        from app.cover_letters.generator import CoverLetterGenerator
        gen = CoverLetterGenerator()
        return gen.generate(job, profile)

    def generate_email(self, job: Job, profile: Profile, recipient: str | None = None) -> dict[str, str]:
        subject = f"Application — {job.title} — {profile.full_name}"
        body = (
            f"Hello,\n\n"
            f"I am {profile.full_name}, a {profile.headline.split('—')[0].strip()}. "
            f"I am writing regarding the {job.title} role at {job.company}. "
            f"My current work at Ethara AI and contributions across Handshake AI (Project Dynamo), "
            f"Multi-SWE-bench, Harbor Benchmark and Turing align with the responsibilities you describe.\n\n"
            f"Resume attached. I am happy to share more detail at a time that suits you.\n\n"
            f"Thanks,\n{profile.full_name}\n{profile.email}\n{profile.phone}\n"
        )
        return {"subject": subject, "body": body, "to": recipient or ""}

    def answer_application_question(self, question: str, job: Job, profile: Profile) -> dict[str, Any]:
        q_lower = question.lower().strip()
        for kw, tag in _SENSITIVE_KEYWORDS.items():
            if kw in q_lower:
                return {"answer": None, "source": tag, "requires_user_input": True, "sensitive": True}
        if "full name" in q_lower or q_lower == "name":
            return {"answer": profile.full_name, "source": "PROFILE_FACT", "requires_user_input": False}
        if "email" in q_lower:
            return {"answer": str(profile.email), "source": "PROFILE_FACT", "requires_user_input": False}
        if "phone" in q_lower:
            return {"answer": profile.phone, "source": "PROFILE_FACT", "requires_user_input": False}
        if "location" in q_lower or "city" in q_lower:
            return {"answer": profile.location, "source": "PROFILE_FACT", "requires_user_input": False}
        if "linkedin" in q_lower:
            return {"answer": profile.linkedin_url or "", "source": "PROFILE_FACT", "requires_user_input": profile.linkedin_url is None}
        if "github" in q_lower:
            return {"answer": profile.github_url or "", "source": "PROFILE_FACT", "requires_user_input": profile.github_url is None}
        if "portfolio" in q_lower or "website" in q_lower:
            return {"answer": profile.portfolio_url or "", "source": "PROFILE_FACT", "requires_user_input": profile.portfolio_url is None}
        if "work authorization" in q_lower or "right to work" in q_lower:
            if profile.work_authorizations:
                wa = profile.work_authorizations[0]
                return {"answer": f"{wa.status} ({wa.country})", "source": "PROFILE_FACT", "requires_user_input": False}
            return {"answer": None, "source": "UNKNOWN", "requires_user_input": True}
        if "education" in q_lower or "degree" in q_lower:
            if profile.education:
                e = profile.education[0]
                return {"answer": f"{e.degree}, {e.institution}", "source": "PROFILE_FACT", "requires_user_input": False}
        if "experience" in q_lower:
            months = profile.total_experience_months()
            return {"answer": f"~{months // 12} years ({months} months)", "source": "DERIVED_FACT", "requires_user_input": False}
        if "skill" in q_lower:
            top = sorted(profile.all_skills)[:8]
            return {"answer": ", ".join(top), "source": "PROFILE_FACT", "requires_user_input": False}
        return {"answer": None, "source": "UNKNOWN", "requires_user_input": True}

    def detect_scam(self, job: Job) -> dict[str, Any]:
        from app.scam.detector import ScamDetector
        return ScamDetector().evaluate(job).model_dump()

    def deduplicate_jobs(self, a: Job, b: Job) -> dict[str, Any]:
        ratio = difflib.SequenceMatcher(
            None,
            f"{a.company} {a.title} {a.location}".lower(),
            f"{b.company} {b.title} {b.location}".lower(),
        ).ratio()
        return {"similarity": ratio, "is_duplicate": ratio >= 0.88}
