from __future__ import annotations

import random
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from app.discovery.base import BaseSource, SourceContext, SourceResult
from app.observability import get_logger
from app.schemas import Job, JobCreate
from app.schemas.enums import ApplicationMethod, EmploymentType, JobSource, RemotePolicy, ShiftType
from app.schemas.job import SalaryRange

log = get_logger("source.linkedin")

_LI_SEARCH_BASE = "https://www.linkedin.com/jobs/search/"

_JOB_ID_RE = re.compile(r"/jobs/view/(\d+)")


def _profile_dir() -> Path:
    from app.config import get_settings
    s = get_settings()
    return Path(s.playwright_user_data_dir) / "profiles" / "linkedin"


class LinkedInSource(BaseSource):
    source_id = JobSource.LINKEDIN
    requires_browser = True
    requires_credentials = False
    requires_api_key = False
    enabled_by_default = False
    rate_limit_per_minute = 10

    def is_enabled(self) -> bool:
        from app.config import get_settings
        return get_settings().linkedin_enabled

    def discover(self, context: SourceContext) -> SourceResult:
        r = SourceResult(source=self.source_id)

        profile_dir = _profile_dir()
        if not profile_dir.exists() or not any(profile_dir.iterdir()):
            r.errors.append(
                f"LinkedIn session not configured at {profile_dir}. "
                "Run `make login-linkedin` and sign in once before enabling discovery."
            )
            return r

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            r.errors.append("playwright not installed; run `.venv/bin/pip install playwright && .venv/bin/playwright install chromium`")
            return r

        queries = context.queries or ["AI Engineer", "ML Engineer"]
        locations = context.locations or ["Remote", "Gurugram, India"]
        max_jobs = context.limit or 30
        max_pages_per_query = 2

        jobs: list[Job] = []
        seen_ids: set[str] = set()

        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    headless=True,
                    viewport={"width": 1280, "height": 900},
                )
                page = ctx.new_page()
                try:
                    for query in queries:
                        for location in locations:
                            if len(jobs) >= max_jobs:
                                break
                            for page_num in range(max_pages_per_query):
                                if len(jobs) >= max_jobs:
                                    break
                                start = page_num * 25
                                url = (
                                    f"{_LI_SEARCH_BASE}?keywords={quote_plus(query)}"
                                    f"&location={quote_plus(location)}"
                                    f"&f_WT=2"
                                    f"&f_TPR=r604800"
                                    f"&sortBy=DD"
                                    f"&start={start}"
                                )
                                try:
                                    page.goto(url, wait_until="load", timeout=25000)
                                except Exception as e:
                                    r.errors.append(f"linkedin: nav failed q={query!r} loc={location!r} page={page_num}: {e!r}")
                                    continue

                                if "/checkpoint/" in page.url or "/authwall/" in page.url:
                                    r.errors.append("linkedin: session hit auth-wall / checkpoint; re-run `make login-linkedin`")
                                    return r

                                try:
                                    page.wait_for_selector(
                                        "li.jobs-search-results__list-item, div.job-card-container, div[data-job-id]",
                                        timeout=8000,
                                    )
                                except Exception:
                                    break

                                cards = page.locator("li.jobs-search-results__list-item").all()
                                if not cards:
                                    cards = page.locator("div.job-card-container").all()
                                if not cards:
                                    break

                                for card in cards:
                                    try:
                                        href_loc = card.locator("a.job-card-container__link, a.job-card-list__title--link, a[href*='/jobs/view/']").first
                                        if href_loc.count() == 0:
                                            continue
                                        href = href_loc.get_attribute("href") or ""
                                        if not href:
                                            continue
                                        if href.startswith("/"):
                                            href = "https://www.linkedin.com" + href
                                        m = _JOB_ID_RE.search(href)
                                        if not m:
                                            continue
                                        job_id = m.group(1)
                                        if job_id in seen_ids:
                                            continue
                                        seen_ids.add(job_id)

                                        title = ""
                                        for t_sel in [
                                            "a.job-card-list__title",
                                            "a.job-card-container__link",
                                            ".job-card-list__title",
                                        ]:
                                            t_loc = card.locator(t_sel).first
                                            if t_loc.count() > 0:
                                                title = (t_loc.text_content() or "").strip()
                                                if title:
                                                    break

                                        company = ""
                                        for c_sel in [
                                            ".job-card-container__primary-description",
                                            ".artdeco-entity-lockup__subtitle",
                                            ".job-card-container__company-name",
                                        ]:
                                            c_loc = card.locator(c_sel).first
                                            if c_loc.count() > 0:
                                                company = (c_loc.text_content() or "").strip()
                                                if company:
                                                    break

                                        card_location = ""
                                        for l_sel in [
                                            ".job-card-container__metadata-item",
                                            ".artdeco-entity-lockup__caption",
                                        ]:
                                            l_loc = card.locator(l_sel).first
                                            if l_loc.count() > 0:
                                                card_location = (l_loc.text_content() or "").strip()
                                                if card_location:
                                                    break

                                        if not title:
                                            continue

                                        apply_url = f"https://www.linkedin.com/jobs/view/{job_id}/"

                                        jc = JobCreate(
                                            source=JobSource.LINKEDIN,
                                            source_job_id=f"linkedin:{job_id}",
                                            company=company or "LinkedIn Posting",
                                            title=title,
                                            location=card_location,
                                            application_url=apply_url,
                                            application_method=ApplicationMethod.EASY_APPLY,
                                            description="",
                                            posted_at=None,
                                            employment_type=EmploymentType.FULL_TIME,
                                            remote_policy=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED if "remote" in (card_location or "").lower() else RemotePolicy.UNKNOWN,
                                            shift_type=ShiftType.UNKNOWN,
                                            salary=SalaryRange(),
                                        )
                                        jobs.append(Job(**jc.model_dump()))

                                        if len(jobs) >= max_jobs:
                                            break
                                    except Exception as e:
                                        r.errors.append(f"linkedin: card parse failed: {e!r}")
                                        continue

                                time.sleep(random.uniform(3.5, 6.5))
                finally:
                    try:
                        ctx.close()
                    except Exception:
                        pass
        except Exception as e:
            r.errors.append(f"linkedin: playwright error: {e!r}")

        r.jobs = jobs
        r.finished_at = datetime.utcnow()
        log.info("linkedin.discovered", count=len(jobs), errors=len(r.errors))
        return r
