from __future__ import annotations

from datetime import datetime, timezone

from app.campaign.orchestrator import CampaignStrategy


_AI_ML_KEYWORDS = (
    "ai", "ml", "machine learning", "llm", "rag", "artificial intelligence",
    "deep learning", "nlp", "neural", "transformer", "gpt", "rlhf", "sft",
    "pytorch", "tensorflow", "generative", "ai engineer", "ml engineer",
    "data scientist", "applied ai", "research engineer", "evaluation",
)


def _match_score(job) -> float:
    return float(getattr(job, "match_score", 0.0) or 0.0)


def _posted_at(job) -> datetime:
    pa = getattr(job, "posted_at", None)
    if isinstance(pa, datetime):
        if pa.tzinfo is None:
            return pa.replace(tzinfo=timezone.utc)
        return pa.astimezone(timezone.utc)
    return datetime(2020, 1, 1, tzinfo=timezone.utc)


def _ai_ml_relevance(job) -> float:
    title = (getattr(job, "title", "") or "").lower()
    description = (getattr(job, "description", "") or "").lower()
    text = f"{title} {description}"
    hits = sum(1 for k in _AI_ML_KEYWORDS if k in text)
    return min(float(hits), 5.0)


def _freshness_score(job, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    posted = _posted_at(job)
    days = max(0.0, (now - posted).total_seconds() / 86400.0)
    if days <= 1:
        return 10.0
    if days <= 3:
        return 8.0
    if days <= 7:
        return 6.0
    if days <= 14:
        return 4.0
    if days <= 30:
        return 2.0
    return 0.0


def rank_jobs(jobs: list, strategy: CampaignStrategy) -> list:
    if strategy == CampaignStrategy.BEST_MATCH:
        return sorted(jobs, key=lambda j: (-_match_score(j), -_posted_at(j).timestamp()))
    if strategy == CampaignStrategy.LATEST:
        return sorted(jobs, key=lambda j: (-_posted_at(j).timestamp(), -_match_score(j)))
    if strategy == CampaignStrategy.AI_ML_FIRST:
        return sorted(jobs, key=lambda j: (-_ai_ml_relevance(j), -_match_score(j), -_posted_at(j).timestamp()))
    return sorted(
        jobs,
        key=lambda j: (
            -(_match_score(j) + _freshness_score(j) * 2.5 + _ai_ml_relevance(j) * 0.5),
            -_posted_at(j).timestamp(),
        ),
    )


def select_top_n(jobs: list, n: int, strategy: CampaignStrategy = CampaignStrategy.TOP_LATEST) -> list:
    return rank_jobs(jobs, strategy)[:n]
