from __future__ import annotations

from app.dedup import Deduplicator


def test_dedup_folds_walmart_pair(mock_jobs):
    d = Deduplicator()
    walmart = [j for j in mock_jobs if "walmart" in j.company.lower()]
    assert len(walmart) >= 2
    clusters = d.cluster(walmart)
    assert len(clusters) == 1
    assert len(clusters[0].members) >= 2


def test_dedup_folds_google_gurugram_pair(mock_jobs):
    d = Deduplicator()
    goog = [j for j in mock_jobs if "google" in j.company.lower() and "gur" in j.location.lower()]
    assert len(goog) >= 2
    clusters = d.cluster(goog)
    assert len(clusters) == 1


def test_dedup_different_jobs_stay_separate(mock_jobs):
    d = Deduplicator()
    anth = [j for j in mock_jobs if "anthropic" in j.company.lower()]
    assert len(anth) >= 2
    clusters = d.cluster(anth)
    assert len(clusters) == len(anth)


def test_dedup_marks_non_canonical_as_duplicate(mock_jobs):
    d = Deduplicator()
    walmart = [j for j in mock_jobs if "walmart" in j.company.lower()]
    clusters = d.cluster(walmart)
    cluster = clusters[0]
    non_canon = [m for m in cluster.members if m.job_id != cluster.canonical.job_id]
    assert all(m.is_duplicate for m in non_canon)
    assert not cluster.canonical.is_duplicate


def test_dedup_canonical_jobs_sum_consistent(mock_jobs):
    d = Deduplicator()
    clusters = d.cluster(mock_jobs)
    canonicals = [c.canonical for c in clusters]
    assert len(canonicals) < len(mock_jobs)
    assert sum(len(c.members) for c in clusters) == len(mock_jobs)
