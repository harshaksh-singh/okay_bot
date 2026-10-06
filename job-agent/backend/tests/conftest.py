from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TESTS_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_test_db = tempfile.NamedTemporaryFile(suffix=".db", prefix="job_agent_test_", delete=False)
_test_db.close()
_test_data_dir = Path(tempfile.mkdtemp(prefix="job_agent_test_data_"))

os.environ["APP_ENV"] = "test"
os.environ["MOCK_MODE"] = "true"
os.environ["DRY_RUN"] = "true"
os.environ["USER_APPROVAL_REQUIRED"] = "true"
os.environ["AUTO_SUBMIT"] = "false"
os.environ["AUTO_EMAIL"] = "false"
os.environ["DISCOVERY_PILOT_MODE"] = "false"
os.environ["SUBMISSION_ENABLED"] = "false"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db.name}"

for _k in (
    "USER_LINKEDIN_URL",
    "USER_GITHUB_URL",
    "USER_PORTFOLIO_URL",
    "USER_NOTICE_PERIOD_WEEKS",
    "USER_EARLIEST_START",
    "USER_SALARY_MIN_USD_HOURLY",
    "USER_SALARY_MIN_INR_MONTHLY",
):
    os.environ.pop(_k, None)

import pytest

from app.data.mock_jobs import build_mock_jobs
from app.profile import get_profile, load_profile
from app.profile.schema import Profile
from app.schemas import Job


@pytest.fixture(scope="session")
def profile() -> Profile:
    return load_profile()


@pytest.fixture
def mock_jobs() -> list[Job]:
    return build_mock_jobs()


@pytest.fixture
def profile_singleton() -> Profile:
    return get_profile()


def _disable_rate_limiter_sleep():
    try:
        from app.discovery.http_client import HttpClient, RateLimiter

        class _NoopRateLimiter(RateLimiter):
            def wait(self) -> None:
                return None

        def _limiter_for_noop(self, host):
            return _NoopRateLimiter()

        HttpClient._limiter_for = _limiter_for_noop  # type: ignore[assignment]
    except Exception:
        pass
    try:
        from app.submission.throttle import AIMDThrottler
        AIMDThrottler.wait_before_submit = lambda self, platform: 0.0  # type: ignore[assignment]
    except Exception:
        pass


def _block_playwright_launch():
    try:
        from app.browser import assisted as _assisted
        _assisted.is_browser_available = lambda: False  # type: ignore[assignment]
    except Exception:
        pass
    try:
        import app.browser as _bpkg
        _bpkg.is_browser_available = lambda: False  # type: ignore[assignment]
    except Exception:
        pass
    try:
        import playwright.sync_api as _pw_sync

        def _blocked_sync_playwright(*args, **kwargs):
            raise RuntimeError(
                "Playwright launch is blocked in tests. "
                "Mark the test with @pytest.mark.browser to opt in."
            )

        _pw_sync.sync_playwright = _blocked_sync_playwright  # type: ignore[assignment]
    except Exception:
        pass


def _block_socket_connect():
    import socket

    _real_create_connection = socket.create_connection
    _real_connect = socket.socket.connect

    def _guard_create_connection(address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) else str(address)
        if host in ("127.0.0.1", "localhost", "::1", "testserver"):
            return _real_create_connection(address, *args, **kwargs)
        raise RuntimeError(
            f"Blocked outbound network to {host!r} during tests. "
            f"Mark the test with @pytest.mark.network to opt in."
        )

    def _guard_connect(self, address, *args, **kwargs):
        try:
            host = address[0] if isinstance(address, tuple) else str(address)
        except Exception:
            host = ""
        if host in ("127.0.0.1", "localhost", "::1", "testserver", ""):
            return _real_connect(self, address, *args, **kwargs)
        raise RuntimeError(
            f"Blocked outbound socket.connect to {host!r} during tests."
        )

    socket.create_connection = _guard_create_connection  # type: ignore[assignment]
    socket.socket.connect = _guard_connect  # type: ignore[assignment]


_block_socket_connect()
_block_playwright_launch()
_disable_rate_limiter_sleep()


def pytest_collection_modifyitems(config, items):
    selected_marker = config.getoption("-m")
    skip_browser = pytest.mark.skip(reason="browser test - requires @pytest.mark.browser and real Playwright; opt in with -m browser")
    skip_live = pytest.mark.skip(reason="live test - requires real third-party submission; opt in with -m live")
    skip_network = pytest.mark.skip(reason="network test - makes real HTTP; opt in with -m network")
    for item in items:
        if "browser" in item.keywords and "browser" not in (selected_marker or ""):
            item.add_marker(skip_browser)
        if "live" in item.keywords and "live" not in (selected_marker or ""):
            item.add_marker(skip_live)
        if "network" in item.keywords and "network" not in (selected_marker or ""):
            item.add_marker(skip_network)
