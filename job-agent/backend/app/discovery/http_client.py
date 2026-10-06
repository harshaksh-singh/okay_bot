from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.observability import get_logger

log = get_logger("http")


_USER_AGENT = "job-agent/0.1 (+personal-career-assistant; respects robots.txt and rate limits)"
_DEFAULT_TIMEOUT = 20.0


@dataclass
class RateLimiter:
    per_minute: int = 30
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _timestamps: list[float] = field(default_factory=list)

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            self._timestamps = [t for t in self._timestamps if now - t < 60]
            if len(self._timestamps) >= self.per_minute:
                sleep_for = 60 - (now - self._timestamps[0]) + 0.05
                if sleep_for > 0:
                    time.sleep(sleep_for)
                    now = time.monotonic()
                    self._timestamps = [t for t in self._timestamps if now - t < 60]
            self._timestamps.append(time.monotonic())


class RobotsCache:
    def __init__(self) -> None:
        self._cache: dict[str, RobotFileParser | None] = {}
        self._lock = threading.Lock()

    def can_fetch(self, url: str, user_agent: str = _USER_AGENT) -> bool:
        try:
            parsed = urlparse(url)
            host = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return False
        with self._lock:
            rp = self._cache.get(host)
            if rp is None and host not in self._cache:
                rp = RobotFileParser()
                rp.set_url(f"{host}/robots.txt")
                try:
                    rp.read()
                except Exception:
                    self._cache[host] = None
                    return True
                self._cache[host] = rp
            if rp is None:
                return True
            try:
                return rp.can_fetch(user_agent, url)
            except Exception:
                return True


@dataclass
class CircuitState:
    failure_count: int = 0
    opened_at: float | None = None


class HttpClient:
    def __init__(
        self,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        rate_limit_per_minute: int = 30,
        extra_headers: dict[str, str] | None = None,
        respect_robots: bool = True,
        circuit_failure_threshold: int | None = None,
        circuit_cooldown_seconds: int | None = None,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.extra_headers = extra_headers or {}
        self.respect_robots = respect_robots
        self._rate_limits: dict[str, RateLimiter] = {}
        self._robots = RobotsCache()
        self._rate_lock = threading.Lock()
        self._default_rate = rate_limit_per_minute
        self._circuits: dict[str, CircuitState] = {}
        self._circuit_lock = threading.Lock()
        try:
            from app.config import get_settings
            s = get_settings()
            self._circuit_threshold = circuit_failure_threshold or s.http_circuit_failure_threshold
            self._circuit_cooldown = circuit_cooldown_seconds or s.http_circuit_cooldown_seconds
        except Exception:
            self._circuit_threshold = circuit_failure_threshold or 5
            self._circuit_cooldown = circuit_cooldown_seconds or 600

    def _circuit_open(self, host: str) -> bool:
        with self._circuit_lock:
            st = self._circuits.get(host)
            if not st or st.opened_at is None:
                return False
            if time.monotonic() - st.opened_at > self._circuit_cooldown:
                self._circuits[host] = CircuitState()
                return False
            return True

    def _record_failure(self, host: str) -> None:
        with self._circuit_lock:
            st = self._circuits.setdefault(host, CircuitState())
            st.failure_count += 1
            if st.failure_count >= self._circuit_threshold and st.opened_at is None:
                st.opened_at = time.monotonic()
                log.warning("http.circuit_open", host=host, cooldown_s=self._circuit_cooldown)

    def _record_success(self, host: str) -> None:
        with self._circuit_lock:
            if host in self._circuits:
                self._circuits[host] = CircuitState()

    def circuit_status(self) -> dict[str, dict]:
        with self._circuit_lock:
            return {
                h: {"failure_count": st.failure_count, "open": st.opened_at is not None}
                for h, st in self._circuits.items()
            }

    def _limiter_for(self, host: str) -> RateLimiter:
        with self._rate_lock:
            if host not in self._rate_limits:
                self._rate_limits[host] = RateLimiter(per_minute=self._default_rate)
            return self._rate_limits[host]

    def _default_headers(self) -> dict[str, str]:
        base = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json, text/html, application/rss+xml;q=0.9, */*;q=0.5",
            "Accept-Language": "en",
        }
        base.update(self.extra_headers)
        return base

    def get(self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> httpx.Response | None:
        return self.request("GET", url, params=params, headers=headers)

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json: Any = None,
        data: Any = None,
    ) -> httpx.Response | None:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if not host:
            log.warning("http.invalid_url", url=url)
            return None

        if self._circuit_open(host):
            log.warning("http.circuit_blocked", host=host, url=url)
            return None

        if self.respect_robots and not self._robots.can_fetch(url):
            log.warning("http.robots_disallowed", url=url)
            return None

        limiter = self._limiter_for(host)
        merged_headers = self._default_headers()
        merged_headers.update(headers or {})

        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            limiter.wait()
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=True) as c:
                    resp = c.request(
                        method,
                        url,
                        params=params,
                        headers=merged_headers,
                        json=json,
                        data=data,
                    )
                if resp.status_code in (429, 500, 502, 503, 504):
                    sleep_for = self.backoff_base * (2 ** attempt)
                    log.warning("http.retryable_status", url=url, status=resp.status_code, attempt=attempt, sleep=sleep_for)
                    time.sleep(sleep_for)
                    continue
                if 200 <= resp.status_code < 400:
                    self._record_success(host)
                    return resp
                log.warning("http.non_retryable_status", url=url, status=resp.status_code)
                self._record_failure(host)
                return resp
            except httpx.TimeoutException as e:
                last_err = e
                sleep_for = self.backoff_base * (2 ** attempt)
                log.warning("http.timeout", url=url, attempt=attempt, sleep=sleep_for)
                time.sleep(sleep_for)
            except httpx.HTTPError as e:
                last_err = e
                sleep_for = self.backoff_base * (2 ** attempt)
                log.warning("http.http_error", url=url, attempt=attempt, error=str(e), sleep=sleep_for)
                time.sleep(sleep_for)

        if last_err:
            log.error("http.exhausted_retries", url=url, error=str(last_err))
            self._record_failure(host)
        return None


_default_client: HttpClient | None = None
_robots_singleton: RobotsCache | None = None


def get_http_client() -> HttpClient:
    global _default_client
    if _default_client is None:
        _default_client = HttpClient()
    return _default_client


def _get_robots_cache() -> RobotsCache:
    global _robots_singleton
    if _robots_singleton is None:
        _robots_singleton = RobotsCache()
    return _robots_singleton


def check_robots_allowed(url: str) -> bool:
    if not url:
        return True
    try:
        return _get_robots_cache().can_fetch(url)
    except Exception:
        return True
