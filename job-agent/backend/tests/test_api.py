from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.agents import AgentContext, JobAgentOrchestrator
from app.api import create_app
from app.database import init_database


@pytest.fixture(scope="module")
def api_client(profile):
    init_database()
    orch = JobAgentOrchestrator()
    orch.run(AgentContext(profile=profile))
    app = create_app()
    with TestClient(app) as client:
        yield client


class TestAPI:
    def test_health(self, api_client):
        r = api_client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["auto_submit"] is False
        assert data["user_approval_required"] is True

    def test_list_jobs(self, api_client):
        r = api_client.get("/jobs?limit=10")
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        assert len(rows) >= 1
        assert "job_id" in rows[0]
        assert "match_score" in rows[0]

    def test_jobs_filter_by_priority(self, api_client):
        r = api_client.get("/jobs?priority=high_priority&limit=10")
        assert r.status_code == 200
        rows = r.json()
        assert all(j["priority"] == "high_priority" for j in rows)

    def test_get_job_by_id(self, api_client):
        rows = api_client.get("/jobs?limit=1").json()
        if not rows:
            pytest.skip("no jobs in DB")
        job_id = rows[0]["job_id"]
        r = api_client.get(f"/jobs/{job_id}")
        assert r.status_code == 200
        assert r.json()["job_id"] == job_id

    def test_get_missing_job_returns_404(self, api_client):
        r = api_client.get("/jobs/does-not-exist")
        assert r.status_code == 404

    def test_list_applications(self, api_client):
        r = api_client.get("/applications?limit=20")
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)

    def test_list_messages(self, api_client):
        r = api_client.get("/messages")
        assert r.status_code == 200

    def test_list_emails(self, api_client):
        r = api_client.get("/emails")
        assert r.status_code == 200

    def test_list_followups(self, api_client):
        r = api_client.get("/followups")
        assert r.status_code == 200

    def test_list_search_runs(self, api_client):
        r = api_client.get("/search-runs")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1

    def test_list_audit_logs(self, api_client):
        r = api_client.get("/audit-logs")
        assert r.status_code == 200

    def test_dashboard_endpoint(self, api_client):
        r = api_client.get("/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "jobs_discovered" in data
        assert "pipeline_funnel" in data

    def test_api_has_no_write_endpoints(self, api_client):
        r = api_client.post("/jobs")
        assert r.status_code in (404, 405)
        r = api_client.delete("/applications/x")
        assert r.status_code in (404, 405)
