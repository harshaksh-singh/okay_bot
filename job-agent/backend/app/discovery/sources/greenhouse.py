from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.discovery.base import BaseSource, SourceContext, SourceResult
from app.discovery.http_client import HttpClient, get_http_client
from app.observability import get_logger
from app.schemas import Job, JobCreate
from app.schemas.enums import ApplicationMethod, EmploymentType, JobSource, RemotePolicy, ShiftType
from app.schemas.job import SalaryRange

log = get_logger("source.greenhouse")


GREENHOUSE_BOARDS: dict[str, dict[str, Any]] = {
    "openai": {"display": "OpenAI", "token": "openai"},
    "anthropic": {"display": "Anthropic", "token": "anthropic"},
    "perplexityai": {"display": "Perplexity", "token": "perplexityai"},
    "mistralai": {"display": "Mistral AI", "token": "mistralai"},
    "huggingface": {"display": "Hugging Face", "token": "huggingface"},
    "replicate": {"display": "Replicate", "token": "replicate"},
    "groq": {"display": "Groq", "token": "groq"},
    "elevenlabs": {"display": "ElevenLabs", "token": "elevenlabs"},
    "scaleai": {"display": "Scale AI", "token": "scaleai"},
    "databricks": {"display": "Databricks", "token": "databricks"},
    "cursor": {"display": "Cursor", "token": "cursor"},
    "together": {"display": "Together AI", "token": "together"},
    "fireworksai": {"display": "Fireworks AI", "token": "fireworksai"},
    "cohere": {"display": "Cohere", "token": "cohere"},
    "anysphere": {"display": "Anysphere", "token": "anysphere"},
    "weightsandbiases": {"display": "Weights & Biases", "token": "weightsandbiases"},
    "langchain": {"display": "LangChain", "token": "langchain"},
    "openrouter": {"display": "OpenRouter", "token": "openrouter"},
    "notion": {"display": "Notion", "token": "notion"},
    "stripe": {"display": "Stripe", "token": "stripe"},
    "glean": {"display": "Glean", "token": "glean"},
    "sarvamai": {"display": "Sarvam AI", "token": "sarvamai"},
    "handshake": {"display": "Handshake", "token": "handshake"},
}


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_SALARY_RE = re.compile(
    r"(?P<cur>USD|US\$|\$|INR|₹|EUR|€|GBP|£)?\s*"
    r"(?P<min>[\d,]+)\s*(?:k|K)?\s*(?:-|to|–)\s*"
    r"(?:USD|US\$|\$|INR|₹|EUR|€|GBP|£)?\s*"
    r"(?P<max>[\d,]+)\s*(?:k|K)?\s*"
    r"(?P<unit>per\s*(?:year|annum|month|hour|week|day)|/\s*(?:year|month|hour|week|day)|USD|yearly|monthly|hourly)?",
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
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _detect_employment_type(title: str, text: str) -> EmploymentType:
    combined = f"{title} {text}".lower()
    if any(k in combined for k in ("part-time", "part time")):
        return EmploymentType.PART_TIME
    if any(k in combined for k in ("contractor", "contract engagement", "contract role")):
        return EmploymentType.CONTRACT
    if "freelance" in combined:
        return EmploymentType.FREELANCE
    if "intern" in combined and "internal" not in combined:
        return EmploymentType.INTERNSHIP
    if "temporary" in combined:
        return EmploymentType.TEMPORARY
    return EmploymentType.FULL_TIME


def _detect_remote(title: str, location: str, text: str) -> RemotePolicy:
    combined = f"{title} {location} {text}".lower()
    if "hybrid" in combined:
        return RemotePolicy.HYBRID
    if any(k in combined for k in ("remote - india", "remote india", "india remote", "india (remote)")):
        return RemotePolicy.REMOTE_COUNTRY
    if any(k in combined for k in ("remote - us", "remote us", "us remote", "remote - united states")):
        return RemotePolicy.REMOTE_COUNTRY
    if any(k in combined for k in ("remote global", "fully remote", "remote worldwide", "work from anywhere")):
        return RemotePolicy.REMOTE_GLOBAL_UNVERIFIED
    if "remote" in combined and "hybrid" not in combined:
        return RemotePolicy.REMOTE_GLOBAL_UNVERIFIED
    if any(k in combined for k in ("onsite", "on-site", "in person", "in-person")):
        return RemotePolicy.ONSITE
    return RemotePolicy.UNKNOWN


def _detect_shift(title: str, text: str) -> ShiftType:
    combined = f"{title} {text}".lower()
    if "night shift" in combined:
        return ShiftType.NIGHT
    if "evening" in combined:
        return ShiftType.EVENING
    if "weekend" in combined:
        return ShiftType.WEEKEND
    if "flexible hours" in combined or "flexible schedule" in combined:
        return ShiftType.FLEXIBLE
    if "async" in combined or "asynchronous" in combined:
        return ShiftType.ASYNC
    return ShiftType.UNKNOWN


def _parse_salary(text: str) -> SalaryRange:
    sr = SalaryRange()
    if not text:
        return sr
    m = _SALARY_RE.search(text)
    if not m:
        return sr
    cur = (m.group("cur") or "").strip()
    unit_raw = (m.group("unit") or "").lower()
    try:
        mn = float(m.group("min").replace(",", ""))
        mx = float(m.group("max").replace(",", ""))
    except (ValueError, AttributeError):
        return sr
    if "k" in m.group(0).lower() and max(mn, mx) < 1000:
        mn *= 1000
        mx *= 1000
    sr.min_value = mn
    sr.max_value = mx
    sr.currency = (
        "USD" if cur in {"$", "US$", "USD"} else
        "INR" if cur in {"₹", "INR"} else
        "EUR" if cur in {"€", "EUR"} else
        "GBP" if cur in {"£", "GBP"} else
        None
    )
    if "year" in unit_raw or "annum" in unit_raw:
        sr.unit = "year"
    elif "month" in unit_raw:
        sr.unit = "month"
    elif "hour" in unit_raw:
        sr.unit = "hour"
    elif "week" in unit_raw:
        sr.unit = "week"
    elif "day" in unit_raw:
        sr.unit = "day"
    sr.raw = m.group(0).strip()
    return sr


def _parse_posted_at(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc).replace(tzinfo=None)
        s = str(value)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


class GreenhouseBoardSource(BaseSource):
    source_id = JobSource.COMPANY_CAREERS
    requires_browser = False
    requires_credentials = False
    requires_api_key = False
    enabled_by_default = False
    rate_limit_per_minute = 20

    def __init__(self, board_token: str, display_name: str | None = None, client: HttpClient | None = None) -> None:
        self.board_token = board_token
        self.display_name = display_name or GREENHOUSE_BOARDS.get(board_token, {}).get("display", board_token)
        self.client = client or get_http_client()

    def is_enabled(self) -> bool:
        from app.config import get_settings
        return get_settings().company_careers_enabled

    def _url(self) -> str:
        return f"https://boards-api.greenhouse.io/v1/boards/{self.board_token}/jobs?content=true"

    def discover(self, context: SourceContext) -> SourceResult:
        r = SourceResult(source=self.source_id)
        try:
            resp = self.client.get(self._url())
            if resp is None:
                r.errors.append(f"greenhouse[{self.board_token}]: request failed or disallowed")
                return r
            if resp.status_code != 200:
                r.errors.append(f"greenhouse[{self.board_token}]: HTTP {resp.status_code}")
                return r
            payload = resp.json()
        except Exception as e:
            r.errors.append(f"greenhouse[{self.board_token}]: {e!r}")
            return r

        jobs_payload = payload.get("jobs", []) if isinstance(payload, dict) else []
        for raw in jobs_payload:
            try:
                job = self._parse_job(raw)
                if job:
                    r.jobs.append(job)
            except Exception as e:
                log.warning("greenhouse.parse_error", error=str(e), job_id=raw.get("id"))
                continue

        if context.limit:
            r.jobs = r.jobs[: context.limit]
        r.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        log.info("greenhouse.discovered", board=self.board_token, count=len(r.jobs))
        return r

    def _parse_job(self, raw: dict) -> Job | None:
        if not raw or not raw.get("title"):
            return None
        title = raw["title"].strip()
        location = (raw.get("location") or {}).get("name", "")
        description_html = raw.get("content", "")
        description = _clean_html(description_html)[:5000]

        employment_type = _detect_employment_type(title, description)
        remote = _detect_remote(title, location, description)
        shift = _detect_shift(title, description)
        salary = _parse_salary(description)
        posted_at = _parse_posted_at(raw.get("updated_at") or raw.get("first_published"))

        create = JobCreate(
            source=JobSource.COMPANY_CAREERS,
            source_job_id=str(raw["id"]),
            company=self.display_name,
            title=title,
            location=location,
            remote=remote,
            employment_type=employment_type,
            shift=shift,
            salary=salary,
            description=description,
            application_url=raw.get("absolute_url"),
            application_method=ApplicationMethod.COMPANY_SITE,
            posted_at=posted_at,
        )
        return Job.from_create(create)


def build_all_greenhouse_sources(client: HttpClient | None = None) -> list[GreenhouseBoardSource]:
    return [GreenhouseBoardSource(token, meta["display"], client=client) for token, meta in GREENHOUSE_BOARDS.items()]
