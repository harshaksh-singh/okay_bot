from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.campaign.orchestrator import CampaignStrategy
from app.campaign.ranking import rank_jobs, select_top_n


def _mock_job(id: str, title: str, match_score: float, days_ago: int, description: str = ""):
    now = datetime.now(timezone.utc)
    posted = now - timedelta(days=days_ago)
    return SimpleNamespace(
        id=id,
        title=title,
        description=description,
        match_score=match_score,
        posted_at=posted,
    )


def _build_fixture_20():
    return [
        _mock_job("j01", "Senior ML Engineer - LLM Evaluation", 92.0, 0, "RLHF SFT PyTorch deep learning"),
        _mock_job("j02", "AI Engineer - RAG Systems", 90.0, 1, "AI engineer RAG LLM"),
        _mock_job("j03", "Generative AI Research Engineer", 88.0, 2, "generative AI research neural"),
        _mock_job("j04", "ML Engineer - Core Platform", 86.0, 5, "machine learning ML engineer"),
        _mock_job("j05", "Senior Software Engineer - Backend", 80.0, 0, "backend python microservices"),
        _mock_job("j06", "Software Engineer - Full Stack", 75.0, 2, "full stack react python"),
        _mock_job("j07", "Data Scientist - Analytics", 72.0, 4, "data scientist analytics SQL"),
        _mock_job("j08", "Backend Engineer - Java Platform", 70.0, 1, "Java Spring kafka backend"),
        _mock_job("j09", "ML Engineer - Perception (OLD POSTING)", 94.0, 45, "perception computer vision ML"),
        _mock_job("j10", "AI Fellow - Project Dynamo (OLD)", 93.0, 60, "AI RLHF SFT evaluation"),
        _mock_job("j11", "Research Engineer - Audio AI", 89.0, 90, "research engineer AI audio"),
        _mock_job("j12", "Site Reliability Engineer", 65.0, 0, "SRE Kubernetes AWS"),
        _mock_job("j13", "DevOps Engineer", 62.0, 1, "DevOps CI/CD Terraform"),
        _mock_job("j14", "Platform Engineer", 60.0, 3, "platform infra Kubernetes"),
        _mock_job("j15", "Account Executive", 40.0, 0, "sales enterprise B2B"),
        _mock_job("j16", "Technical Writer", 35.0, 0, "writer documentation"),
        _mock_job("j17", "Product Manager", 50.0, 2, "PM product strategy"),
        _mock_job("j18", "Designer - UX", 48.0, 1, "designer Figma UX"),
        _mock_job("j19", "QA Engineer - Automation", 55.0, 7, "QA automation Selenium"),
        _mock_job("j20", "Security Engineer", 68.0, 10, "security pentest"),
    ]


class TestBestMatch:
    def test_best_match_sorts_by_score_desc(self):
        jobs = _build_fixture_20()
        ranked = rank_jobs(jobs, CampaignStrategy.BEST_MATCH)
        scores = [j.match_score for j in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_best_match_top_1_is_highest(self):
        jobs = _build_fixture_20()
        top = select_top_n(jobs, 1, CampaignStrategy.BEST_MATCH)
        assert top[0].id == "j09"

    def test_best_match_top_3_ids(self):
        jobs = _build_fixture_20()
        top = select_top_n(jobs, 3, CampaignStrategy.BEST_MATCH)
        assert [j.id for j in top] == ["j09", "j10", "j01"]


class TestLatest:
    def test_latest_sorts_by_date_desc(self):
        jobs = _build_fixture_20()
        ranked = rank_jobs(jobs, CampaignStrategy.LATEST)
        timestamps = [j.posted_at.timestamp() for j in ranked]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_latest_excludes_old_despite_high_score(self):
        jobs = _build_fixture_20()
        top5 = select_top_n(jobs, 5, CampaignStrategy.LATEST)
        top_ids = {j.id for j in top5}
        assert "j09" not in top_ids
        assert "j10" not in top_ids
        assert "j11" not in top_ids


class TestAIMLFirst:
    def test_ai_ml_jobs_rank_before_non_ai_jobs(self):
        jobs = _build_fixture_20()
        ranked = rank_jobs(jobs, CampaignStrategy.AI_ML_FIRST)
        ids_order = [j.id for j in ranked]
        ai_first_rank = ids_order.index("j01")
        sales_rank = ids_order.index("j15")
        writer_rank = ids_order.index("j16")
        assert ai_first_rank < sales_rank
        assert ai_first_rank < writer_rank


class TestTopLatest:
    def test_top_latest_balances_match_and_freshness(self):
        jobs = _build_fixture_20()
        top5 = select_top_n(jobs, 5, CampaignStrategy.TOP_LATEST)
        top_ids = {j.id for j in top5}
        assert "j01" in top_ids
        assert "j02" in top_ids
        assert "j09" not in top_ids
        assert "j15" not in top_ids
        assert "j16" not in top_ids

    def test_top_latest_respects_target_n(self):
        jobs = _build_fixture_20()
        for n in [1, 5, 10, 15, 20]:
            assert len(select_top_n(jobs, n, CampaignStrategy.TOP_LATEST)) == n


class TestDeterminism:
    def test_same_input_same_output(self):
        jobs = _build_fixture_20()
        r1 = [j.id for j in rank_jobs(jobs, CampaignStrategy.TOP_LATEST)]
        r2 = [j.id for j in rank_jobs(list(reversed(jobs)), CampaignStrategy.TOP_LATEST)]
        assert r1 == r2
