from __future__ import annotations

from app.profile import Profile
from app.schemas import Job
from app.schemas.application import FormAnswer


_STANDARD_FIELDS: list[tuple[str, str]] = [
    ("full_name", "Full Name"),
    ("first_name", "First Name"),
    ("last_name", "Last Name"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("location", "Current Location"),
    ("linkedin", "LinkedIn URL"),
    ("github", "GitHub URL"),
    ("portfolio", "Portfolio URL"),
    ("resume", "Resume"),
    ("cover_letter", "Cover Letter"),
    ("work_authorization", "Work Authorization"),
    ("current_company", "Current Company"),
    ("current_role", "Current Role"),
    ("years_experience", "Years of Experience"),
    ("education", "Highest Education"),
    ("skills", "Key Skills"),
    ("expected_salary", "Expected Salary"),
    ("notice_period", "Notice Period"),
    ("earliest_start", "Earliest Start Date"),
    ("employment_type", "Preferred Employment Type"),
    ("hours_per_week", "Preferred Hours per Week"),
    ("timezone", "Timezone"),
    ("job_role_canonical", "Role (echo from job)"),
    ("job_company", "Company (echo from job)"),
    ("job_location", "Job Location (echo)"),
]


_SENSITIVE_FIELDS = {
    "expected_salary", "notice_period", "earliest_start", "hours_per_week", "timezone", "work_authorization",
}


class FormFieldMapper:
    def map(self, job: Job, profile: Profile) -> list[FormAnswer]:
        name_parts = profile.full_name.split()
        first = name_parts[0] if name_parts else profile.full_name
        last = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        answers: list[FormAnswer] = []
        for key, question in _STANDARD_FIELDS:
            answer, tag, requires = self._answer_for(key, profile, job, first, last)
            answers.append(
                FormAnswer(
                    field_name=key,
                    question=question,
                    answer=answer,
                    source_tag=tag,
                    requires_user_input=requires,
                    is_sensitive=key in _SENSITIVE_FIELDS,
                )
            )
        return answers

    def _answer_for(self, key: str, profile: Profile, job: Job, first: str, last: str) -> tuple[str | None, str, bool]:
        if key == "full_name":
            return profile.full_name, "PROFILE_FACT", False
        if key == "first_name":
            return first, "PROFILE_FACT", False
        if key == "last_name":
            return last, "PROFILE_FACT", bool(not last)
        if key == "email":
            return str(profile.email), "PROFILE_FACT", False
        if key == "phone":
            return profile.phone, "PROFILE_FACT", False
        if key == "location":
            return profile.location, "PROFILE_FACT", False
        if key == "linkedin":
            return profile.linkedin_url, "PROFILE_FACT", profile.linkedin_url is None
        if key == "github":
            return profile.github_url, "PROFILE_FACT", profile.github_url is None
        if key == "portfolio":
            return profile.portfolio_url, "PROFILE_FACT", profile.portfolio_url is None
        if key == "resume":
            return "attach selected resume variant", "DERIVED_FACT", False
        if key == "cover_letter":
            return "attach generated cover letter", "DERIVED_FACT", False
        if key == "job_role_canonical":
            return job.title, "JOB_FACT", False
        if key == "job_company":
            return job.company, "JOB_FACT", False
        if key == "job_location":
            return job.location or "", "JOB_FACT", False
        if key == "work_authorization":
            if profile.work_authorizations:
                wa = profile.work_authorizations[0]
                return f"{wa.status} ({wa.country})", "PROFILE_FACT", False
            return None, "UNKNOWN", True
        if key == "current_company":
            current = next((e for e in profile.experiences if e.is_current), None)
            if current:
                return current.company, "PROFILE_FACT", False
            return None, "UNKNOWN", True
        if key == "current_role":
            current = next((e for e in profile.experiences if e.is_current), None)
            if current:
                return current.role, "PROFILE_FACT", False
            return None, "UNKNOWN", True
        if key == "years_experience":
            months = profile.total_experience_months()
            return f"{months // 12}", "DERIVED_FACT", False
        if key == "education":
            if profile.education:
                e = profile.education[0]
                return f"{e.degree}, {e.institution}", "PROFILE_FACT", False
            return None, "UNKNOWN", True
        if key == "skills":
            return ", ".join(sorted(profile.all_skills)[:12]), "PROFILE_FACT", False
        if key == "expected_salary":
            if profile.salary_expectation_min_inr_monthly is not None:
                return (
                    f"₹{profile.salary_expectation_min_inr_monthly:,}/month (configured minimum)",
                    "USER_PROVIDED_FACT",
                    False,
                )
            if profile.salary_expectation_min_usd_hourly is not None:
                return (
                    f"${profile.salary_expectation_min_usd_hourly}/hour (configured minimum)",
                    "USER_PROVIDED_FACT",
                    False,
                )
            return None, "USER_INPUT_REQUIRED", True
        if key == "notice_period":
            if profile.availability.notice_period_weeks is not None:
                return f"{profile.availability.notice_period_weeks} weeks", "USER_PROVIDED_FACT", False
            return None, "USER_INPUT_REQUIRED", True
        if key == "earliest_start":
            if profile.availability.earliest_start is not None:
                return profile.availability.earliest_start.isoformat(), "USER_PROVIDED_FACT", False
            return None, "USER_INPUT_REQUIRED", True
        if key == "employment_type":
            return "Open to part-time, contract, freelance, remote, and full-time", "PROFILE_FACT", False
        if key == "hours_per_week":
            if job.hours_per_week:
                return f"{job.hours_per_week} h/week (match job)", "JOB_FACT", False
            return "flexible — match job's standard hours", "DERIVED_FACT", False
        if key == "timezone":
            return "Asia/Kolkata (IST, UTC+5:30)", "PROFILE_FACT", False
        return None, "UNKNOWN", True
