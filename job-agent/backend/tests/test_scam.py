from __future__ import annotations

from app.scam import ScamDetector
from app.schemas.enums import ScamRisk


def _by_id(mock_jobs, source_job_id):
    return next(j for j in mock_jobs if j.source_job_id == source_job_id)


def test_scam_detects_registration_fee_whatsapp(mock_jobs):
    d = ScamDetector()
    job = _by_id(mock_jobs, "li-scam-031")
    e = d.evaluate(job)
    assert e.risk == ScamRisk.HIGH
    assert any("upfront_payment" in r or "registration" in r for r in e.reasons)
    assert any("whatsapp" in r.lower() for r in e.reasons)


def test_scam_detects_crypto_telegram(mock_jobs):
    d = ScamDetector()
    job = _by_id(mock_jobs, "li-scam-032")
    e = d.evaluate(job)
    assert e.risk == ScamRisk.HIGH
    assert any("crypto" in r for r in e.reasons) or any("telegram" in r.lower() for r in e.reasons)


def test_scam_detects_mlm_training_fee(mock_jobs):
    d = ScamDetector()
    job = _by_id(mock_jobs, "naukri-scam-033")
    e = d.evaluate(job)
    assert e.risk in {ScamRisk.MEDIUM, ScamRisk.HIGH}
    assert any("mlm" in r for r in e.reasons) or any("fee" in r for r in e.reasons)


def test_scam_legit_jobs_pass(mock_jobs):
    d = ScamDetector()
    legit = _by_id(mock_jobs, "li-ai-ant-001")
    e = d.evaluate(legit)
    assert e.risk == ScamRisk.NONE


def test_scam_free_email_mismatch_signal(mock_jobs):
    d = ScamDetector()
    job = _by_id(mock_jobs, "li-scam-031")
    e = d.evaluate(job)
    assert any("free email" in r for r in e.reasons)
