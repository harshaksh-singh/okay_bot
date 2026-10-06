from __future__ import annotations

import time

import pytest

from app.discovery.http_client import HttpClient, RateLimiter, RobotsCache


def test_rate_limiter_allows_burst_under_limit():
    rl = RateLimiter(per_minute=5)
    start = time.monotonic()
    for _ in range(5):
        rl.wait()
    assert time.monotonic() - start < 0.2


def test_rate_limiter_blocks_over_limit(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
    rl = RateLimiter(per_minute=3)
    for _ in range(4):
        rl.wait()
    assert any(s > 0 for s in sleeps)


def test_robots_cache_handles_invalid_url_lenient():
    rc = RobotsCache()
    assert rc.can_fetch("not-a-url") is True


def test_http_client_rejects_malformed_url():
    c = HttpClient(respect_robots=False, max_retries=0)
    assert c.get("not://a//url") is None
