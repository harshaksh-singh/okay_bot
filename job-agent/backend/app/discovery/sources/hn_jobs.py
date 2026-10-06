from __future__ import annotations

import re
from datetime import datetime, timezone

from app.discovery.base import BaseSource, SourceContext, SourceResult
from app.discovery.http_client import get_http_client
from app.observability import get_logger
from app.schemas import Job, JobCreate
from app.schemas.enums import ApplicationMethod, EmploymentType, JobSource, RemotePolicy, ShiftType
from app.schemas.job import SalaryRange

log = get_logger("source.hn_jobs")

_HN_API = "https://hacker-news.firebaseio.com/v0"

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE)
_AI_KEYWORDS = re.compile(
    r"\b(ai|ml|machine\s*learning|llm|rag|artificial\s*intelligence|deep\s*learning|"
    r"nlp|neural|transformer|gpt|evaluation|rlhf|sft|lora|pytorch|tensorflow|"
    r"generative|data\s*scien|ml\s*engineer|ai\s*engineer|applied\s*ai|research\s*engineer|"
    r"software\s*engineer|backend|python)\b",
    re.IGNORECASE,
)


def _clean_html(html: str) -> str:
    if not html:
        return ""
    try:
        import html as html_mod
        decoded = html_mod.unescape(html)
    except Exception:
        decoded = html
    text = _HTML_TAG_RE.sub(" ", decoded)
    return re.sub(r"\s+", " ", text).strip()


def _detect_remote(text: str) -> RemotePolicy:
    t = text.lower()
    if "remote" in t and ("india" in t or "us only" in t or "us-only" in t):
        return RemotePolicy.REMOTE_COUNTRY
    if "remote" in t:
        return RemotePolicy.REMOTE_GLOBAL_UNVERIFIED
    if "hybrid" in t:
        return RemotePolicy.HYBRID
    if "onsite" in t or "on-site" in t or "in-person" in t:
        return RemotePolicy.ONSITE
    return RemotePolicy.UNKNOWN


def _employment_from_text(text: str) -> EmploymentType:
    t = text.lower()
    if "intern" in t:
        return EmploymentType.INTERNSHIP
    if "contract" in t or "freelance" in t:
        return EmploymentType.CONTRACT
    if "part-time" in t or "part time" in t:
        return EmploymentType.PART_TIME
    return EmploymentType.FULL_TIME


class HackerNewsJobsSource(BaseSource):
    source_id = JobSource.COMPANY_CAREERS
    requires_browser = False
    requires_credentials = False
    requires_api_key = False
    enabled_by_default = False
    rate_limit_per_minute = 60

    def is_enabled(self) -> bool:
        from app.config import get_settings
        return getattr(get_settings(), "hn_jobs_enabled", False)

    def discover(self, context: SourceContext) -> SourceResult:
        r = SourceResult(source=self.source_id)
        http = get_http_client()

        try:
            resp = http.get(f"{_HN_API}/jobstories.json")
            if resp.status_code != 200:
                r.errors.append(f"hn_jobs: list HTTP {resp.status_code}")
                return r
            story_ids = resp.json()
        except Exception as e:
            r.errors.append(f"hn_jobs: list fetch failed: {e!r}")
            return r

        if not isinstance(story_ids, list):
            r.errors.append("hn_jobs: unexpected list format")
            return r

        max_jobs = context.limit or 50
        jobs: list[Job] = []
        for sid in story_ids[:200]:
            if len(jobs) >= max_jobs:
                break
            try:
                item_resp = http.get(f"{_HN_API}/item/{sid}.json")
                if item_resp.status_code != 200:
                    continue
                item = item_resp.json()
            except Exception:
                continue
            if not item or item.get("type") != "job":
                continue

            title = (item.get("title") or "").strip()
            if not title:
                continue
            if not _AI_KEYWORDS.search(title):
                continue

            apply_url = item.get("url") or f"https://news.ycombinator.com/item?id={sid}"
            text_html = item.get("text") or ""
            description = _clean_html(text_html) or title

            parts = re.split(r"\s+is\s+hiring\s+", title, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                company = parts[0].strip()
                role = parts[1].strip()
            else:
                company = title.split("|")[0].strip()[:60]
                role = title

            posted_at = None
            if item.get("time"):
                try:
                    posted_at = datetime.fromtimestamp(float(item["time"]), tz=timezone.utc).replace(tzinfo=None)
                except Exception:
                    pass

            try:
                jc = JobCreate(
                    source=JobSource.COMPANY_CAREERS,
                    source_job_id=f"hn:{sid}",
                    company=company or "HN Job",
                    title=role or title,
                    location="",
                    application_url=apply_url,
                    application_method=ApplicationMethod.DIRECT_URL,
                    description=description,
                    posted_at=posted_at,
                    employment_type=_employment_from_text(f"{title} {description}"),
                    remote_policy=_detect_remote(f"{title} {description}"),
                    shift_type=ShiftType.UNKNOWN,
                    salary=SalaryRange(),
                )
                jobs.append(Job(**jc.model_dump()))
            except Exception as e:
                r.errors.append(f"hn_jobs: job build failed id={sid}: {e!r}")
                continue

        r.jobs = jobs
        r.finished_at = datetime.utcnow()
        log.info("hn_jobs.discovered", count=len(jobs), errors=len(r.errors))
        return r
