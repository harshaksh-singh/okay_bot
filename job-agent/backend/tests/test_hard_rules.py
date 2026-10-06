from __future__ import annotations

from app.filtering import apply_hard_rules
from app.scam import ScamDetector
from app.schemas.enums import ScamRisk


def _by_id(mock_jobs, source_job_id):
    return next(j for j in mock_jobs if j.source_job_id == source_job_id)


def test_hard_rules_reject_nurse(profile, mock_jobs):
    job = _by_id(mock_jobs, "li-029")
    result = apply_hard_rules(job, profile)
    assert result.reject
    assert any("unrelated" in r for r in result.reasons)


def test_hard_rules_reject_sales_mlm(profile, mock_jobs):
    job = _by_id(mock_jobs, "naukri-030")
    result = apply_hard_rules(job, profile)
    assert result.reject


def test_hard_rules_reject_intern(profile, mock_jobs):
    job = _by_id(mock_jobs, "li-nokia-044")
    result = apply_hard_rules(job, profile)
    assert result.reject
    assert any("intern" in r.lower() for r in result.reasons)


def test_hard_rules_reject_vp_role(profile, mock_jobs):
    job = _by_id(mock_jobs, "li-ms-vp-028")
    result = apply_hard_rules(job, profile)
    assert result.reject


def test_hard_rules_reject_scam_high(profile, mock_jobs):
    scam = _by_id(mock_jobs, "li-scam-031")
    detector = ScamDetector()
    eval_ = detector.evaluate(scam)
    result = apply_hard_rules(scam, profile, scam_risk=eval_.risk)
    assert result.reject
    assert any("scam risk" in r.lower() for r in result.reasons)


def test_hard_rules_keep_good_ai_role(profile, mock_jobs):
    job = _by_id(mock_jobs, "li-ai-ant-001")
    result = apply_hard_rules(job, profile, scam_risk=ScamRisk.NONE)
    assert not result.reject
