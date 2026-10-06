from __future__ import annotations

from app.schemas.enums import EmploymentType, JobSource


def test_mock_jobs_count_at_least_50(mock_jobs):
    assert len(mock_jobs) >= 50


def test_mock_jobs_have_canonical_ids(mock_jobs):
    ids = [j.job_id for j in mock_jobs]
    assert all(ids), "every job must have a job_id"
    assert all(j.duplicate_group for j in mock_jobs)


def test_mock_jobs_cover_diverse_employment_types(mock_jobs):
    types = {j.employment_type for j in mock_jobs}
    assert EmploymentType.FULL_TIME in types
    assert EmploymentType.PART_TIME in types
    assert EmploymentType.CONTRACT in types
    assert EmploymentType.FREELANCE in types
    assert EmploymentType.INTERNSHIP in types


def test_mock_jobs_cover_core_locations(mock_jobs):
    locs = " ".join([j.location.lower() for j in mock_jobs])
    assert "gurugram" in locs or "gurgaon" in locs
    assert "noida" in locs
    assert "remote" in locs


def test_mock_jobs_include_scam_candidates(mock_jobs):
    txt = " ".join(j.title + " " + j.description for j in mock_jobs).lower()
    assert "registration fee" in txt or "whatsapp" in txt or "crypto" in txt


def test_mock_jobs_include_duplicate_pair(mock_jobs):
    walmart = [j for j in mock_jobs if "walmart" in j.company.lower()]
    assert len(walmart) >= 2


def test_mock_jobs_include_priority_companies(mock_jobs):
    companies = {j.company.lower() for j in mock_jobs}
    assert any("anthropic" in c for c in companies)
    assert any("openai" in c for c in companies)
    assert any("google" in c for c in companies)


def test_mock_jobs_include_unrelated_role_for_hard_reject(mock_jobs):
    assert any("nurse" in j.title.lower() for j in mock_jobs)
    assert any("sales" in j.title.lower() for j in mock_jobs)


def test_mock_jobs_include_senior_exec_for_hard_reject(mock_jobs):
    assert any("vp" in j.title.lower() or "chief" in j.title.lower() for j in mock_jobs)


def test_mock_jobs_sources_are_diverse(mock_jobs):
    sources = {j.source for j in mock_jobs}
    assert len(sources) >= 5
    assert JobSource.LINKEDIN in sources
