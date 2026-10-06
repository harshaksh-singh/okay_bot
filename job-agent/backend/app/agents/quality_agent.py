from __future__ import annotations

import re

from app.agents.base import AgentContext, AgentResult, BaseAgent


_FORBIDDEN_CLAIMS = [
    re.compile(r"\b10\+?\s*years?\b", re.I),
    re.compile(r"\b15\+?\s*years?\b", re.I),
    re.compile(r"\b20\+?\s*years?\b", re.I),
    re.compile(r"\bphd\b", re.I),
    re.compile(r"\bprincipal engineer\b", re.I),
    re.compile(r"\bstaff engineer\b", re.I),
    re.compile(r"\bdistinguished engineer\b", re.I),
    re.compile(r"\bchief\s+(ai|technology|technical|engineering)\s+officer\b", re.I),
    re.compile(r"\bus citizen\b", re.I),
    re.compile(r"\bgreen card\b", re.I),
    re.compile(r"\bh-?1b\s*(sponsor|visa|holder)\b", re.I),
    re.compile(r"\bmba\b", re.I),
    re.compile(r"\bphd\s+in\b", re.I),
]

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
_SALARY_LIKE_RE = re.compile(r"(\$\s*\d{1,3}(?:,\d{3})+|\$\s*\d{3,}k|\brs\.?\s*\d+\s*lakh|\b₹\s*\d+)", re.IGNORECASE)


class QualityAgent(BaseAgent):
    name = "quality"

    def run(self, context: AgentContext, previous: list[AgentResult]) -> AgentResult:
        r = self._start()
        issues: list[dict] = []

        applications = []
        communication = None
        matching_jobs: list = []
        for p in previous:
            if p.agent == "application":
                applications = p.metadata.get("applications", [])
            if p.agent == "communication":
                communication = p
            if p.agent == "matching":
                matching_jobs = p.jobs
        job_by_id = {j.job_id: j for j in matching_jobs}

        profile_companies = {e.company.lower() for e in context.profile.experiences}
        profile_companies.add(context.profile.full_name.lower())
        priority_companies = {c.lower() for c in context.profile.priority_companies}
        profile_degrees = {e.degree.lower() for e in context.profile.education}
        profile_institutions = {e.institution.lower() for e in context.profile.education}

        profile_year_range: set[int] = set()
        for e in context.profile.experiences:
            start_y = e.start_date.year
            end_y = (e.end_date.year if e.end_date else 2030)
            profile_year_range.update(range(start_y, end_y + 1))
        for e in context.profile.education:
            profile_year_range.update(range(e.start_date.year, e.end_date.year + 1))

        _CAMEL_COMPANY_RE = re.compile(r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+){0,3})\b")
        _COMMON_WORDS = {
            "The", "I", "At", "In", "For", "With", "And", "Or", "A", "An", "Of", "To",
            "Resume", "Project", "Projects", "Python", "Java", "Docker", "LLM", "LLMs",
            "AI", "ML", "RLHF", "SFT", "LoRA", "RAG", "Gurugram", "Noida", "India",
            "Hindi", "English", "Maithili", "APAC", "US", "UK", "EU", "USA",
            "September", "October", "November", "December", "January", "February",
            "March", "April", "May", "June", "July", "August",
            "Hello", "Hi", "Thanks", "Sincerely", "Regards",
            "Harshaksh", "Singh", "Ethara", "Handshake", "Multi", "SWE", "Harbor", "Turing", "Outlier",
            "Technology", "Technologies", "Platform", "Platforms", "Engineering",
            "GitHub", "Google", "OpenAI", "Anthropic", "Microsoft", "Meta", "NVIDIA",
            "Software", "Machine", "Learning", "Generative", "Infrastructure",
            "Benchmark", "Dynamo", "Research", "Fellow", "Author",
            "B.Tech", "CSE", "Noida Institute", "NIET",
        }

        def _scan(subject_id: str, surface: str, text: str) -> None:
            if not text:
                return
            for pattern in _FORBIDDEN_CLAIMS:
                if pattern.search(text):
                    issues.append({
                        "application_id": subject_id,
                        "surface": surface,
                        "issue": f"forbidden claim pattern matched: {pattern.pattern}",
                    })

            allowed_companies = set(profile_companies) | set(priority_companies)
            job = job_by_id.get(subject_id)
            if job:
                allowed_companies.add(job.company.lower())
            for match in _CAMEL_COMPANY_RE.finditer(text):
                phrase = match.group(1)
                if phrase in _COMMON_WORDS:
                    continue
                if any(tok in _COMMON_WORDS for tok in phrase.split()):
                    continue
                phrase_lower = phrase.lower()
                if any(ac in phrase_lower or phrase_lower in ac for ac in allowed_companies):
                    continue

            for m in _YEAR_RE.finditer(text):
                try:
                    y = int(m.group(1))
                except ValueError:
                    continue
                if y < 1990:
                    issues.append({
                        "application_id": subject_id,
                        "surface": surface,
                        "issue": f"suspicious old year reference: {y}",
                    })
                elif y > 2035:
                    issues.append({
                        "application_id": subject_id,
                        "surface": surface,
                        "issue": f"suspicious future year reference: {y}",
                    })

            if _SALARY_LIKE_RE.search(text):
                if surface not in {"job_description", "resume"}:
                    issues.append({
                        "application_id": subject_id,
                        "surface": surface,
                        "issue": "unverified salary / compensation claim in generated text",
                    })

            lower = text.lower()
            if "phd" in lower and "phd" not in {d for d in profile_degrees if "phd" in d}:
                issues.append({
                    "application_id": subject_id,
                    "surface": surface,
                    "issue": "generated text claims PhD; not in profile.education",
                })
            if "mba" in lower and "mba" not in {d for d in profile_degrees if "mba" in d}:
                issues.append({
                    "application_id": subject_id,
                    "surface": surface,
                    "issue": "generated text claims MBA; not in profile.education",
                })

            allowed_institutions = profile_institutions
            if "stanford" in lower and not any("stanford" in inst for inst in allowed_institutions):
                issues.append({
                    "application_id": subject_id,
                    "surface": surface,
                    "issue": "generated text references Stanford; not in profile.education",
                })
            if ("mit" in lower and " mit " in f" {lower} ") and not any("mit" in inst for inst in allowed_institutions):
                issues.append({
                    "application_id": subject_id,
                    "surface": surface,
                    "issue": "generated text references MIT; not in profile.education",
                })

        for app in applications:
            _scan(app.application_id, "cover_letter", app.cover_letter_text or "")

            if app.resume_path and app.resume_path.exists():
                try:
                    _scan(app.application_id, "resume", app.resume_path.read_text(errors="ignore"))
                except Exception:
                    pass

            for ans in app.form_answers:
                if ans.answer:
                    _scan(app.application_id, f"form:{ans.field_name}", str(ans.answer))
                if ans.source_tag == "UNKNOWN" and ans.answer and not ans.requires_user_input:
                    issues.append({
                        "application_id": app.application_id,
                        "surface": "form_answer_tag",
                        "issue": f"answer tagged UNKNOWN but non-empty: {ans.field_name}",
                    })

        if communication:
            for msg in communication.metadata.get("recruiter_messages", []):
                _scan(msg.get("job_id", ""), "recruiter_message", msg.get("message", ""))
            for email in communication.metadata.get("emails", []):
                _scan(email.get("job_id", ""), "email_subject", email.get("subject", ""))
                _scan(email.get("job_id", ""), "email_body", email.get("body", ""))

        from app.config import get_settings
        s = get_settings()

        blocked_application_ids: set[str] = set()
        if s.truthfulness_hard_block and issues:
            blocked_application_ids = {i["application_id"] for i in issues if i.get("application_id", "").startswith("app_")}
            for app in applications:
                if app.application_id in blocked_application_ids:
                    try:
                        from app.schemas.enums import ApplicationStatus
                        app.status = ApplicationStatus.REVIEW_REQUIRED
                        app.notes = (app.notes or "") + " | QualityAgent: truthfulness hard-block flagged this application for review"
                    except Exception:
                        pass

        r.metadata["quality_issues"] = issues
        r.metadata["surfaces_checked"] = ["cover_letter", "resume", "form_answers", "recruiter_messages", "email_subject", "email_body"]
        r.metadata["truthfulness_hard_block_active"] = s.truthfulness_hard_block
        r.metadata["blocked_application_ids"] = sorted(blocked_application_ids)
        r.notes.append(
            f"quality check: {len(issues)} issues across {len(applications)} applications; "
            f"truthfulness_hard_block={s.truthfulness_hard_block}; "
            f"{len(blocked_application_ids)} applications routed to REVIEW_REQUIRED"
        )
        r.mark_done()
        return r
