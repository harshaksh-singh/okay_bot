from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.discovery.base import SourceContext
from app.discovery.sources.ashby import AshbyOrgSource
from app.discovery.sources.greenhouse import GreenhouseBoardSource, _clean_html, _detect_remote, _parse_salary
from app.discovery.sources.lever import LeverCompanySource
from app.schemas.enums import EmploymentType, RemotePolicy


def _mock_response(json_payload, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = json_payload
    m.text = "<rss></rss>"
    return m


class TestGreenhouseParser:
    def test_parses_minimal_job(self):
        payload = {
            "jobs": [
                {
                    "id": 12345,
                    "title": "AI Engineer, Applied Research",
                    "location": {"name": "Remote - Global"},
                    "content": "<p>We are looking for an engineer. $150,000 to $250,000 per year.</p>",
                    "absolute_url": "https://boards.greenhouse.io/anthropic/jobs/12345",
                    "updated_at": "2026-10-01T10:00:00Z",
                }
            ]
        }
        src = GreenhouseBoardSource("anthropic", "Anthropic")
        src.client = MagicMock()
        src.client.get.return_value = _mock_response(payload)
        result = src.discover(SourceContext())
        assert len(result.jobs) == 1
        job = result.jobs[0]
        assert job.company == "Anthropic"
        assert job.title == "AI Engineer, Applied Research"
        assert job.employment_type == EmploymentType.FULL_TIME
        assert job.remote == RemotePolicy.REMOTE_GLOBAL_UNVERIFIED
        assert job.salary.min_value == 150000

    def test_handles_http_error(self):
        src = GreenhouseBoardSource("fake", "Fake")
        src.client = MagicMock()
        src.client.get.return_value = _mock_response({}, status=404)
        result = src.discover(SourceContext())
        assert not result.jobs
        assert any("404" in e for e in result.errors)

    def test_skips_malformed_entries(self):
        payload = {"jobs": [{"title": ""}, {"id": 1, "title": "Valid", "location": {"name": "Remote"}, "content": "<p>desc</p>", "absolute_url": "https://x.com/1"}]}
        src = GreenhouseBoardSource("x", "X")
        src.client = MagicMock()
        src.client.get.return_value = _mock_response(payload)
        result = src.discover(SourceContext())
        assert len(result.jobs) == 1

    def test_clean_html(self):
        assert _clean_html("<p>Hello&nbsp;<b>world</b></p>") == "Hello world"
        assert _clean_html("") == ""

    def test_salary_parser_dollar_year(self):
        s = _parse_salary("Base salary: $100,000 to $150,000 per year.")
        assert s.min_value == 100000
        assert s.max_value == 150000
        assert s.currency == "USD"
        assert s.unit == "year"

    def test_salary_parser_inr_month(self):
        s = _parse_salary("Monthly compensation ₹40,000 - ₹60,000 per month")
        assert s.currency == "INR"
        assert s.unit == "month"

    def test_detect_remote_hybrid(self):
        assert _detect_remote("Engineer", "Gurugram (Hybrid)", "") == RemotePolicy.HYBRID

    def test_detect_remote_global(self):
        assert _detect_remote("Engineer", "Remote - Global", "fully remote team") == RemotePolicy.REMOTE_GLOBAL_UNVERIFIED

    def test_detect_remote_onsite(self):
        assert _detect_remote("Engineer", "", "in-person 4 days per week") == RemotePolicy.ONSITE


class TestLeverParser:
    def test_parses_minimal_job(self):
        payload = [
            {
                "id": "abc-123",
                "text": "Software Engineer, Platform",
                "categories": {"location": "Paris / Remote Europe"},
                "description": "Build cool stuff with Python.",
                "hostedUrl": "https://jobs.lever.co/mistral/abc-123",
                "createdAt": 1700000000000,
            }
        ]
        src = LeverCompanySource("mistral", "Mistral AI")
        src.client = MagicMock()
        src.client.get.return_value = _mock_response(payload)
        result = src.discover(SourceContext())
        assert len(result.jobs) == 1
        job = result.jobs[0]
        assert job.company == "Mistral AI"
        assert job.application_url is not None

    def test_handles_non_list_payload(self):
        src = LeverCompanySource("x")
        src.client = MagicMock()
        src.client.get.return_value = _mock_response({"error": "nope"})
        result = src.discover(SourceContext())
        assert any("unexpected" in e for e in result.errors)


class TestAshbyParser:
    def test_parses_minimal_job(self):
        payload = {
            "jobs": [
                {
                    "id": "ash-1",
                    "title": "Senior Full Stack Engineer",
                    "locationName": "San Francisco",
                    "employmentType": "FULL_TIME",
                    "workplaceType": "REMOTE",
                    "descriptionHtml": "<p>Cool role</p>",
                    "jobUrl": "https://jobs.ashbyhq.com/cursor/ash-1",
                    "publishedDate": "2026-10-01T00:00:00Z",
                }
            ]
        }
        src = AshbyOrgSource("cursor", "Cursor")
        src.client = MagicMock()
        src.client.get.return_value = _mock_response(payload)
        result = src.discover(SourceContext())
        assert len(result.jobs) == 1
        assert result.jobs[0].employment_type == EmploymentType.FULL_TIME
        assert result.jobs[0].remote == RemotePolicy.REMOTE_GLOBAL_UNVERIFIED

    def test_accepts_list_payload(self):
        payload = [{"id": "a", "title": "AI Engineer", "locationName": "Remote", "descriptionHtml": "", "jobUrl": "https://x.com"}]
        src = AshbyOrgSource("x", "X")
        src.client = MagicMock()
        src.client.get.return_value = _mock_response(payload)
        result = src.discover(SourceContext())
        assert len(result.jobs) == 1
