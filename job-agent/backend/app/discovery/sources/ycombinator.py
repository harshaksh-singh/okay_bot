from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.discovery.base import BaseSource, SourceContext, SourceResult
import httpx
from app.observability import get_logger
from app.schemas import Job, JobCreate
from app.schemas.enums import ApplicationMethod, EmploymentType, JobSource, RemotePolicy, ShiftType
from app.schemas.job import SalaryRange

log = get_logger("source.ycombinator")


_YC_API_BASE = "https://api.ycombinator.com/v0.1"


def _employment_type_from_yc(t: str | None) -> EmploymentType:
    if not t:
        return EmploymentType.FULL_TIME
    t_lower = t.lower()
    if "intern" in t_lower:
        return EmploymentType.INTERNSHIP
    if "contract" in t_lower:
        return EmploymentType.CONTRACT
    if "part" in t_lower:
        return EmploymentType.PART_TIME
    return EmploymentType.FULL_TIME


def _remote_from_yc(location: str) -> RemotePolicy:
    loc = (location or "").lower()
    if "remote" in loc and ("india" in loc or "us" in loc or "uk" in loc or "eu" in loc):
        return RemotePolicy.REMOTE_COUNTRY
    if "remote" in loc:
        return RemotePolicy.REMOTE_GLOBAL_UNVERIFIED
    if "hybrid" in loc:
        return RemotePolicy.HYBRID
    if location:
        return RemotePolicy.ONSITE
    return RemotePolicy.UNKNOWN


def _parse_yc_salary(sr_text: str | None) -> SalaryRange:
    import re
    sr = SalaryRange()
    if not sr_text:
        return sr
    sr.raw = sr_text
    m = re.search(r"\$?([\d,]+)[Kk]?\s*(?:-|to)\s*\$?([\d,]+)[Kk]?", sr_text)
    if m:
        try:
            mn = float(m.group(1).replace(",", ""))
            mx = float(m.group(2).replace(",", ""))
            if "k" in sr_text.lower() or (max(mn, mx) < 1000):
                mn *= 1000
                mx *= 1000
            sr.min_value, sr.max_value = mn, mx
            sr.currency = "USD" if "$" in sr_text else None
            sr.unit = "year"
        except Exception:
            pass
    return sr


class YCombinatorSource(BaseSource):
    source_id = JobSource.COMPANY_CAREERS
    requires_browser = False
    requires_credentials = False
    requires_api_key = False
    enabled_by_default = False
    rate_limit_per_minute = 20

    def is_enabled(self) -> bool:
        from app.config import get_settings
        return getattr(get_settings(), "ycombinator_enabled", False)

    def discover(self, context: SourceContext) -> SourceResult:
        r = SourceResult(source=self.source_id)
        http = httpx.Client(timeout=30.0, follow_redirects=True, headers={"User-Agent": "job-agent/1.0 (+https://github.com/)"})

        max_pages = 10
        max_jobs = context.limit or 100
        jobs_found: list[Job] = []
        seen_ids: set[str] = set()

        want_roles = {"engineering", "science", "data", "ml", "ai"}

        for page_num in range(max_pages):
            if len(jobs_found) >= max_jobs:
                break
            url = f"{_YC_API_BASE}/companies"
            params = {"isHiring": "true", "page": str(page_num)}
            try:
                resp = http.get(url, params=params)
                if resp is None or resp.status_code != 200:
                    r.errors.append(f"ycombinator: page {page_num} HTTP {resp.status_code}")
                    break
                data = resp.json()
            except Exception as e:
                r.errors.append(f"ycombinator: page {page_num} error: {e!r}")
                break

            companies = data.get("companies") if isinstance(data, dict) else data
            if not companies:
                break

            for comp in companies:
                comp_name = comp.get("name", "").strip()
                comp_slug = comp.get("slug", "").strip()
                comp_url = comp.get("url") or (f"https://www.ycombinator.com/companies/{comp_slug}" if comp_slug else None)
                for job in comp.get("jobs", []) or []:
                    role = (job.get("role") or "").lower()
                    if want_roles and role and not any(w in role for w in want_roles):
                        continue
                    job_id = str(job.get("id") or "")
                    if not job_id or job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    title = (job.get("title") or "").strip()
                    if not title:
                        continue
                    apply_url = (job.get("url") or "").strip()
                    if not apply_url:
                        continue
                    location = (job.get("location") or "").strip()
                    try:
                        posted_at = None
                        if job.get("created_at"):
                            posted_at = datetime.fromisoformat(job["created_at"].replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
                    except Exception:
                        posted_at = None

                    jc = JobCreate(
                        source=JobSource.COMPANY_CAREERS,
                        source_job_id=f"yc:{job_id}",
                        company=comp_name or "YC Company",
                        title=title,
                        location=location,
                        application_url=apply_url,
                        application_method=ApplicationMethod.DIRECT_URL,
                        description=job.get("description", "") or "",
                        posted_at=posted_at,
                        employment_type=_employment_type_from_yc(job.get("type")),
                        remote_policy=_remote_from_yc(location),
                        shift_type=ShiftType.UNKNOWN,
                        salary=_parse_yc_salary(job.get("salary_range")),
                    )
                    try:
                        from app.schemas.job import Job as _Job
                        jobs_found.append(_Job.from_create(jc) if hasattr(_Job, "from_create") else Job(**jc.model_dump()))
                    except Exception:
                        try:
                            jobs_found.append(Job(**jc.model_dump()))
                        except Exception as e:
                            r.errors.append(f"ycombinator: job create failed: {e!r}")
                            continue
                    if len(jobs_found) >= max_jobs:
                        break
                if len(jobs_found) >= max_jobs:
                    break

            if len(companies) < 10:
                break

        r.jobs = jobs_found
        r.finished_at = datetime.utcnow()
        log.info("ycombinator.discovered", count=len(jobs_found), errors=len(r.errors))
        return r
