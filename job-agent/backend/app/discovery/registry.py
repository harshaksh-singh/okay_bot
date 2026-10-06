from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.discovery.base import BaseSource
from app.discovery.mock_source import MockSource
from app.schemas.enums import JobSource


class SourceRegistry:
    def __init__(self, sources: list[BaseSource]) -> None:
        self._sources: list[BaseSource] = list(sources)

    def all(self) -> list[BaseSource]:
        return list(self._sources)

    def enabled(self) -> list[BaseSource]:
        return [s for s in self._sources if s.is_enabled()]

    def by_type(self, source: JobSource) -> list[BaseSource]:
        return [s for s in self._sources if s.source_id == source]


def _build_sources() -> list[BaseSource]:
    s = get_settings()
    sources: list[BaseSource] = []
    if s.mock_mode:
        sources.append(MockSource())
        return sources

    if s.company_careers_enabled:
        try:
            from app.discovery.sources.greenhouse import build_all_greenhouse_sources
            sources.extend(build_all_greenhouse_sources())
        except Exception:
            pass
        try:
            from app.discovery.sources.lever import build_all_lever_sources
            sources.extend(build_all_lever_sources())
        except Exception:
            pass
        try:
            from app.discovery.sources.ashby import build_all_ashby_sources
            sources.extend(build_all_ashby_sources())
        except Exception:
            pass

    if s.remoteok_enabled:
        try:
            from app.discovery.sources.remoteok import RemoteOkSource
            sources.append(RemoteOkSource())
        except Exception:
            pass

    if s.weworkremotely_enabled:
        try:
            from app.discovery.sources.weworkremotely import WeWorkRemotelySource
            sources.append(WeWorkRemotelySource())
        except Exception:
            pass

    if s.hackernews_enabled:
        try:
            from app.discovery.sources.hackernews import HackerNewsWhoIsHiringSource
            sources.append(HackerNewsWhoIsHiringSource())
        except Exception:
            pass

    if getattr(s, "hn_jobs_enabled", False):
        try:
            from app.discovery.sources.hn_jobs import HackerNewsJobsSource
            sources.append(HackerNewsJobsSource())
        except Exception:
            pass

    if getattr(s, "ycombinator_enabled", False):
        try:
            from app.discovery.sources.ycombinator import YCombinatorSource
            sources.append(YCombinatorSource())
        except Exception:
            pass

    if s.linkedin_enabled:
        try:
            from app.discovery.sources.linkedin import LinkedInSource
            sources.append(LinkedInSource())
        except Exception:
            pass

    _stub_pairs: list[tuple[bool, str]] = [
        (s.indeed_enabled, "IndeedStub"),
        (s.naukri_enabled, "NaukriStub"),
        (s.glassdoor_enabled, "GlassdoorStub"),
        (s.wellfound_enabled, "WellfoundStub"),
        (s.handshake_enabled, "HandshakeStub"),
        (s.cutshort_enabled, "CutshortStub"),
        (s.instahyre_enabled, "InstahyreStub"),
        (s.hirist_enabled, "HiristStub"),
        (s.foundit_enabled, "FounditStub"),
        (s.internshala_enabled, "InternshalaStub"),
        (s.outlier_enabled, "OutlierStub"),
        (s.surge_ai_enabled, "SurgeAiStub"),
        (s.telus_digital_ai_enabled, "TelusDigitalAiStub"),
    ]
    for enabled, cls_name in _stub_pairs:
        if not enabled:
            continue
        try:
            from app.discovery.sources import _common_stub as _stubs
            cls = getattr(_stubs, cls_name)
            sources.append(cls())
        except Exception:
            pass

    if s.google_search_enabled:
        try:
            from app.discovery.sources.google_search import GoogleProgrammableSearchSource
            sources.append(GoogleProgrammableSearchSource())
        except Exception:
            try:
                from app.discovery.sources._common_stub import GoogleSearchStub
                sources.append(GoogleSearchStub())
            except Exception:
                pass
    return sources


@lru_cache(maxsize=1)
def get_registry() -> SourceRegistry:
    return SourceRegistry(_build_sources())


def reset_registry_cache() -> None:
    get_registry.cache_clear()
