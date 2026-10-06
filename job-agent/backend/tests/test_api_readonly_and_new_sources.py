from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api import create_app
from app.database import SessionLocal, init_database
from app.database.models import AuditLogRow, SearchRunRow
from app.discovery.base import SourceContext
from app.discovery.sources.google_search import GoogleProgrammableSearchSource
from app.discovery.sources.hackernews import HackerNewsWhoIsHiringSource


class TestDashboardIsReadOnly:
    def test_dashboard_endpoint_does_not_write_to_db(self):
        init_database()
        with SessionLocal() as s:
            before_runs = s.scalar(select(func.count()).select_from(SearchRunRow)) or 0
            before_audits = s.scalar(select(func.count()).select_from(AuditLogRow)) or 0
        app = create_app()
        with TestClient(app) as c:
            r = c.get("/dashboard")
        assert r.status_code == 200
        with SessionLocal() as s:
            after_runs = s.scalar(select(func.count()).select_from(SearchRunRow)) or 0
            after_audits = s.scalar(select(func.count()).select_from(AuditLogRow)) or 0
        assert after_runs == before_runs, "/dashboard must not create SearchRunRow"
        assert after_audits == before_audits, "/dashboard must not create AuditLogRow"

    def test_api_init_does_not_raise_when_db_file_absent(self, tmp_path):
        from app.database.engine import Base, SessionLocal
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        test_engine = create_engine(f"sqlite:///{tmp_path}/cold.db", future=True, connect_args={"check_same_thread": False})
        Base.metadata.create_all(test_engine)
        TestSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False, expire_on_commit=False, future=True)
        with TestSession() as s:
            from app.database.models import JobRow
            from sqlalchemy import select
            assert s.scalars(select(JobRow)).all() == []


class TestGoogleProgrammableSearch:
    def test_discover_without_api_key_errors_gracefully(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_CSE_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_CSE_ENGINE_ID", raising=False)
        src = GoogleProgrammableSearchSource()
        result = src.discover(SourceContext())
        assert any("GOOGLE_CSE_API_KEY" in e for e in result.errors)

    def test_build_queries_uses_defaults_when_context_empty(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CSE_API_KEY", "test_key")
        monkeypatch.setenv("GOOGLE_CSE_ENGINE_ID", "test_engine")
        src = GoogleProgrammableSearchSource()
        qs = src._build_queries(SourceContext())
        assert len(qs) > 0
        assert any("AI Engineer" in q for q in qs)
        assert any("site:boards.greenhouse.io" in q for q in qs)

    def test_parse_item_extracts_company_from_greenhouse_url(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CSE_API_KEY", "x")
        monkeypatch.setenv("GOOGLE_CSE_ENGINE_ID", "x")
        src = GoogleProgrammableSearchSource()
        item = {
            "title": "AI Engineer at Anthropic",
            "link": "https://boards.greenhouse.io/anthropic/jobs/12345",
            "snippet": "Build cool stuff with Python and LLMs. Remote.",
        }
        job = src._parse_item(item, source_query="test")
        assert job is not None
        assert "Anthropic" in job.company
        assert "AI Engineer" in job.title

    def test_discover_handles_api_failure(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CSE_API_KEY", "key")
        monkeypatch.setenv("GOOGLE_CSE_ENGINE_ID", "cx")
        src = GoogleProgrammableSearchSource()
        src.client = MagicMock()
        src.client.get.return_value = None
        result = src.discover(SourceContext(limit=5))
        assert isinstance(result.jobs, list)


class TestHackerNewsSource:
    def test_find_thread_handles_empty(self):
        src = HackerNewsWhoIsHiringSource()
        src.client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"hits": []}
        src.client.get.return_value = mock_resp
        assert src._find_latest_thread_id() is None

    def test_discover_handles_missing_thread(self):
        src = HackerNewsWhoIsHiringSource()
        src.client = MagicMock()
        src.client.get.return_value = None
        result = src.discover(SourceContext())
        assert any("thread" in e.lower() for e in result.errors)

    def test_parse_posting_extracts_structured_fields(self):
        src = HackerNewsWhoIsHiringSource()
        item = {"time": 1700000000}
        text = "Anthropic | AI Engineer | REMOTE | USD 200k-350k. Build Claude with us."
        job = src._parse_posting(42, item, text)
        assert job is not None
        assert "Anthropic" in job.company
        assert str(job.application_url).rstrip("/") == "https://news.ycombinator.com/item?id=42"

    def test_discover_uses_latest_thread_and_parses_children(self):
        src = HackerNewsWhoIsHiringSource()
        src.client = MagicMock()
        search_resp = MagicMock()
        search_resp.status_code = 200
        search_resp.json.return_value = {"hits": [{"title": "Ask HN: Who is hiring? (October 2026)", "objectID": "100"}]}
        thread_resp = MagicMock()
        thread_resp.status_code = 200
        thread_resp.json.return_value = {"kids": [101, 102]}
        comment_resp = MagicMock()
        comment_resp.status_code = 200
        comment_resp.json.return_value = {
            "text": "Mistral AI | ML Engineer | Remote Europe | Python, PyTorch. Apply at jobs.lever.co/mistral",
            "time": 1700000000,
        }
        src.client.get.side_effect = [search_resp, thread_resp, comment_resp, comment_resp]
        result = src.discover(SourceContext(limit=5))
        assert len(result.jobs) >= 1
