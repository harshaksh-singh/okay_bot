from __future__ import annotations

import re
from datetime import datetime, timezone

from app.discovery.base import BaseSource, SourceContext, SourceResult
from app.discovery.http_client import HttpClient, get_http_client
from app.discovery.sources.greenhouse import (
    _clean_html,
    _detect_employment_type,
    _detect_remote,
    _detect_shift,
    _parse_salary,
)
from app.observability import get_logger
from app.schemas import Job, JobCreate
from app.schemas.enums import ApplicationMethod, JobSource, RemotePolicy

log = get_logger("source.hn")


_WHO_IS_HIRING_SEARCH_URL = (
    "https://hn.algolia.com/api/v1/search?query=who%20is%20hiring&tags=story&hitsPerPage=5"
)
_ITEM_URL_TEMPLATE = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


class HackerNewsWhoIsHiringSource(BaseSource):
    source_id = JobSource.MANUAL
    requires_browser = False
    requires_api_key = False
    enabled_by_default = False
    rate_limit_per_minute = 20

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or get_http_client()

    def is_enabled(self) -> bool:
        from app.config import get_settings
        return get_settings().hackernews_enabled

    def _find_latest_thread_id(self) -> int | None:
        resp = self.client.get(_WHO_IS_HIRING_SEARCH_URL)
        if resp is None or resp.status_code != 200:
            return None
        try:
            hits = resp.json().get("hits", [])
            for h in hits:
                title = (h.get("title") or "").lower()
                if "who is hiring" in title and "ask hn" in title:
                    try:
                        return int(h["objectID"])
                    except (KeyError, ValueError):
                        continue
        except Exception as e:
            log.warning("hn.search_parse", error=str(e))
        return None

    def discover(self, context: SourceContext) -> SourceResult:
        r = SourceResult(source=self.source_id)
        thread_id = self._find_latest_thread_id()
        if not thread_id:
            r.errors.append("hn: could not locate latest 'Ask HN: Who is hiring?' thread")
            return r

        resp = self.client.get(_ITEM_URL_TEMPLATE.format(id=thread_id))
        if resp is None or resp.status_code != 200:
            r.errors.append(f"hn: thread {thread_id} fetch failed")
            return r
        try:
            thread = resp.json()
        except Exception as e:
            r.errors.append(f"hn: thread parse failed: {e!r}")
            return r

        child_ids = thread.get("kids", [])[:50]
        for cid in child_ids:
            resp = self.client.get(_ITEM_URL_TEMPLATE.format(id=cid))
            if resp is None or resp.status_code != 200:
                continue
            try:
                item = resp.json()
            except Exception:
                continue
            if not item or item.get("deleted") or item.get("dead"):
                continue
            text_html = item.get("text", "")
            text = _clean_html(text_html)
            if not text:
                continue
            job = self._parse_posting(cid, item, text)
            if job:
                r.jobs.append(job)

        if context.limit:
            r.jobs = r.jobs[: context.limit]
        r.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        log.info("hn.discovered", count=len(r.jobs), thread=thread_id)
        return r

    def _parse_posting(self, item_id: int, item: dict, text: str) -> Job | None:
        first_line = text.split(".")[0][:200]
        header_match = re.match(r"^\s*([A-Z][A-Za-z0-9&\.\- ]{2,60})\s*[\|—\-]\s*(.{3,120})$", first_line)
        if header_match:
            company = header_match.group(1).strip()
            title = header_match.group(2).strip()[:140]
        else:
            parts = text.split("|")
            if len(parts) >= 2:
                company = parts[0].strip()[:60] or "unknown"
                title = parts[1].strip()[:140] or first_line
            else:
                company = "unknown"
                title = first_line
        if not company or not title:
            return None

        remote = _detect_remote(title, "", text) or RemotePolicy.UNKNOWN
        emp = _detect_employment_type(title, text)
        shift = _detect_shift(title, text)
        salary = _parse_salary(text)

        url = f"https://news.ycombinator.com/item?id={item_id}"
        create = JobCreate(
            source=JobSource.MANUAL,
            source_job_id=f"hn:{item_id}",
            company=company,
            title=title,
            location="",
            remote=remote,
            employment_type=emp,
            shift=shift,
            salary=salary,
            description=text[:5000],
            application_url=url,
            application_method=ApplicationMethod.COMPANY_SITE,
            posted_at=datetime.fromtimestamp(float(item["time"]), tz=timezone.utc).replace(tzinfo=None) if item.get("time") else None,
        )
        return Job.from_create(create)
