from __future__ import annotations

from app.matching.scorer import _canonicalize_skill, _extract_tokens, _SKILL_SYNONYMS, _skill_hit
from app.profile import Profile
from app.schemas import Job


class CoverLetterGenerator:
    def generate(self, job: Job, profile: Profile) -> str:
        name = profile.full_name
        role = job.title.strip()
        company = job.company.strip()

        job_tokens = _extract_tokens(f"{job.title} {job.description} {' '.join(job.requirements)}")
        profile_skills = {_canonicalize_skill(s) for s in profile.all_skills}
        shared_skills = []
        for canonical in profile_skills:
            if _skill_hit(canonical, job_tokens):
                shared_skills.append(canonical)
        shared_skills = sorted(set(shared_skills))[:5]

        current = next((e for e in profile.experiences if e.is_current and e.employment_type.lower() == "full-time"), None)
        contractor = [e for e in profile.experiences if e.employment_type == "Independent Contractor"]

        opening = f"Hi {company} team,"

        bullets: list[str] = []
        if current:
            bullets.append(
                f"- At {current.company}, I {current.bullets[0].rstrip('.').lower() if current.bullets else 'build and ship ML systems'}."
            )
        if contractor:
            platforms = ", ".join(sorted({c.company for c in contractor})[:4])
            bullets.append(
                f"- Independent contractor at frontier AI data platforms ({platforms}) — authoring benchmark tasks, "
                "gold reference solutions, and verifier logic for code and reasoning evaluation."
            )
        if profile.projects:
            p = profile.projects[0]
            bullets.append(f"- Built {p.name} ({', '.join(p.tech_stack[:3])}) — {p.bullets[0].rstrip('.') if p.bullets else 'end-to-end project'}.")

        if shared_skills:
            match_line = (
                f"Your role calls for {', '.join(shared_skills)}; "
                f"these overlap directly with my day-to-day work at {current.company if current else 'Ethara AI'}."
            )
        else:
            match_line = (
                f"My background spans LLM fine-tuning (SFT/LoRA), RLHF, RAG, and reproducible Dockerized ML pipelines, "
                f"which align with the responsibilities described."
            )

        closing = (
            f"Resume attached. Happy to walk through the Project Dynamo / Multi-SWE-bench / Harbor Benchmark work "
            f"in more depth whenever it suits you.\n\n"
            f"Thanks,\n{name}\n{profile.email} · {profile.phone}"
        )

        parts = [
            opening,
            "",
            f"I'm writing about the {role} role. I'm a Machine Learning Engineer currently at "
            f"{current.company if current else 'Ethara AI'} working on LLM fine-tuning (SFT and RLHF), "
            f"benchmark task authoring, and reproducible training pipelines.",
            "",
            *bullets,
            "",
            match_line,
            "",
            closing,
        ]
        return "\n".join(parts)
