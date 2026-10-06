from __future__ import annotations

from app.matching import MatchingEngine, apply_scoring_tier
from app.schemas.enums import PriorityTier


def _job_by_id(mock_jobs, source_job_id):
    return next(j for j in mock_jobs if j.source_job_id == source_job_id)


def test_matching_anthropic_ai_engineer_scores_high(profile, mock_jobs):
    engine = MatchingEngine()
    job = _job_by_id(mock_jobs, "li-ai-ant-001")
    breakdown, reasons, missing = engine.score(job, profile)
    total = breakdown.total()
    assert total >= 70
    assert any("priority company" in r.lower() for r in reasons)
    assert any("rlhf" in r.lower() or "sft" in r.lower() or "pytorch" in r.lower() or "llm" in r.lower() for r in reasons)


def test_matching_part_time_ai_evaluation_boost(profile, mock_jobs):
    engine = MatchingEngine()
    job = _job_by_id(mock_jobs, "li-abt-038")
    breakdown, reasons, _ = engine.score(job, profile)
    assert breakdown.employment_type > 0
    assert breakdown.schedule > 0
    assert any("evening" in r.lower() or "part-time" in r.lower() for r in reasons)


def test_matching_gurugram_hybrid_scores_well(profile, mock_jobs):
    engine = MatchingEngine()
    job = _job_by_id(mock_jobs, "naukri-walmart-020")
    breakdown, reasons, _ = engine.score(job, profile)
    assert any("gurugram" in r.lower() or "cyber" in r.lower() for r in reasons)
    assert breakdown.location > 0


def test_matching_senior_vp_role_scores_low_experience(profile, mock_jobs):
    engine = MatchingEngine()
    job = _job_by_id(mock_jobs, "li-ms-vp-028")
    breakdown, _, missing = engine.score(job, profile)
    assert breakdown.experience < 10
    assert any("senior" in m.lower() for m in missing) or any("years" in m.lower() for m in missing)


def test_matching_unrelated_role_scores_low(profile, mock_jobs):
    engine = MatchingEngine()
    job = _job_by_id(mock_jobs, "li-029")
    breakdown, _, _ = engine.score(job, profile)
    total = breakdown.total()
    assert total < 40


def test_matching_tier_assignment(monkeypatch):
    monkeypatch.setenv("SCORE_APPLY_IMMEDIATELY", "95")
    monkeypatch.setenv("SCORE_HIGH_PRIORITY", "85")
    monkeypatch.setenv("SCORE_APPLY", "75")
    monkeypatch.setenv("SCORE_CONSIDER", "65")
    monkeypatch.setenv("SCORE_LOW_PRIORITY", "50")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        assert apply_scoring_tier(96) == PriorityTier.APPLY_IMMEDIATELY
        assert apply_scoring_tier(85) == PriorityTier.HIGH_PRIORITY
        assert apply_scoring_tier(76) == PriorityTier.APPLY
        assert apply_scoring_tier(66) == PriorityTier.CONSIDER
        assert apply_scoring_tier(51) == PriorityTier.LOW_PRIORITY
        assert apply_scoring_tier(10) == PriorityTier.REJECT
    finally:
        get_settings.cache_clear()


def test_matching_weights_sum_near_one(profile):
    engine = MatchingEngine()
    assert abs(engine.weights.total() - 1.0) < 0.001


def test_matching_remote_global_unverified_lower_than_india(profile, mock_jobs):
    engine = MatchingEngine()
    hf = _job_by_id(mock_jobs, "li-hf-006")
    scale = _job_by_id(mock_jobs, "li-scale-007")
    hf_breakdown, _, _ = engine.score(hf, profile)
    scale_breakdown, _, _ = engine.score(scale, profile)
    assert scale_breakdown.location >= hf_breakdown.location


def test_matching_part_time_wins_over_full_time(profile, mock_jobs):
    engine = MatchingEngine()
    pt = _job_by_id(mock_jobs, "li-dwavelet-026")
    ft = _job_by_id(mock_jobs, "li-swiggy-013")
    pt_total = engine.score(pt, profile)[0].total()
    ft_total = engine.score(ft, profile)[0].total()
    assert pt_total > ft_total
