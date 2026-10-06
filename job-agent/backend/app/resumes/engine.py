from __future__ import annotations

from app.profile import Profile, ResumeVariant
from app.schemas import Job
from app.schemas.enums import EmploymentType


class ResumeEngine:
    def choose_variant(self, job: Job, profile: Profile) -> ResumeVariant | None:
        if not profile.resume_variants:
            return None

        title_lower = (job.title or "").lower()
        desc_lower = (job.description or "").lower()

        scored: list[tuple[float, ResumeVariant]] = []
        for v in profile.resume_variants:
            score = 0.0
            for role in v.target_roles:
                r = role.lower()
                if r in title_lower:
                    score += 3.0
                elif any(tok in title_lower for tok in r.split() if len(tok) >= 4):
                    score += 1.0
            for skill in v.highlighted_skills:
                s = skill.lower()
                if s in desc_lower or s in title_lower:
                    score += 0.5

            if job.employment_type in {EmploymentType.PART_TIME, EmploymentType.CONTRACT, EmploymentType.FREELANCE}:
                if v.name == "part_time_remote":
                    score += 2.0
            if "evaluation" in title_lower or "evaluator" in title_lower or "benchmark" in title_lower or "rlhf" in title_lower:
                if v.name == "ai_evaluation":
                    score += 2.5
            if "software" in title_lower or "backend" in title_lower or "fullstack" in title_lower or "full stack" in title_lower:
                if v.name == "software_engineer":
                    score += 1.5

            scored.append((score, v))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_variant = scored[0]
        if best_score <= 0:
            return next((v for v in profile.resume_variants if v.name == "ai_ml"), profile.resume_variants[0])
        return best_variant
