from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from app.schemas import Job


_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^a-z0-9 ]+")
_COMPANY_SUFFIX_RE = re.compile(
    r"\b(inc|incorporated|ltd|limited|llp|llc|pvt|private|technologies|technology|labs|lab|ai|solutions|services|corp|corporation|systems|software|india)\b",
    re.IGNORECASE,
)


def normalize_company(name: str) -> str:
    s = (name or "").lower().strip()
    s = _PUNCT_RE.sub(" ", s)
    s = _COMPANY_SUFFIX_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s)
    return s.strip()


def normalize_title(title: str) -> str:
    s = (title or "").lower().strip()
    s = _PUNCT_RE.sub(" ", s)
    s = s.replace("sr", "senior").replace("jr", "junior")
    s = _WS_RE.sub(" ", s)
    tokens = sorted(set(s.split()))
    return " ".join(tokens)


_LOCATION_NOISE = {
    "india", "hybrid", "remote", "onsite", "haryana", "karnataka", "tamil",
    "nadu", "maharashtra", "uttar", "pradesh", "telangana", "west", "bengal",
    "nct", "delhi-ncr", "ncr",
}


def normalize_location(location: str) -> str:
    s = (location or "").lower().strip()
    s = _PUNCT_RE.sub(" ", s)
    s = s.replace("bengaluru", "bangalore").replace("gurgaon", "gurugram")
    s = _WS_RE.sub(" ", s)
    return s.strip()


def location_tokens(location: str) -> set[str]:
    normalized = normalize_location(location)
    return {t for t in normalized.split() if t and t not in _LOCATION_NOISE}


def canonicalize_url(url: str | None) -> str:
    if not url:
        return ""
    try:
        p = urlparse(str(url))
        return f"{p.scheme}://{p.netloc.lower()}{p.path.rstrip('/')}"
    except Exception:
        return str(url)


@dataclass
class DuplicateCluster:
    group_id: str
    members: list[Job] = field(default_factory=list)
    canonical: Job | None = None


class Deduplicator:
    def __init__(self, similarity_threshold: float = 0.88) -> None:
        self.threshold = similarity_threshold

    def _signature_strict(self, job: Job) -> tuple[str, str, str, str]:
        return (
            normalize_company(job.company),
            normalize_title(job.title),
            normalize_location(job.location),
            canonicalize_url(str(job.application_url) if job.application_url else ""),
        )

    def _are_near_duplicates(self, a: Job, b: Job) -> tuple[bool, float]:
        c_a, t_a, l_a, u_a = self._signature_strict(a)
        c_b, t_b, l_b, u_b = self._signature_strict(b)

        if a.source_job_id and b.source_job_id and a.source == b.source and a.source_job_id == b.source_job_id:
            return True, 1.0

        if u_a and u_b and u_a == u_b:
            return True, 1.0

        if c_a != c_b:
            if difflib.SequenceMatcher(None, c_a, c_b).ratio() < 0.85:
                return False, 0.0

        title_ratio = difflib.SequenceMatcher(None, t_a, t_b).ratio()
        if title_ratio < 0.70:
            return False, title_ratio

        if title_ratio >= 0.90:
            return True, title_ratio

        if l_a and l_b and l_a != l_b:
            tokens_a = location_tokens(a.location)
            tokens_b = location_tokens(b.location)
            if tokens_a and tokens_b and not (tokens_a & tokens_b):
                return False, title_ratio

        return title_ratio >= self.threshold, title_ratio

    def cluster(self, jobs: list[Job]) -> list[DuplicateCluster]:
        clusters: list[DuplicateCluster] = []
        assigned: dict[str, int] = {}

        for job in jobs:
            placed = False
            for idx, cluster in enumerate(clusters):
                sample = cluster.members[0]
                dup, _ = self._are_near_duplicates(job, sample)
                if dup:
                    cluster.members.append(job)
                    assigned[job.job_id] = idx
                    placed = True
                    break
            if not placed:
                clusters.append(DuplicateCluster(group_id=job.duplicate_group or job.job_id, members=[job]))
                assigned[job.job_id] = len(clusters) - 1

        for cluster in clusters:
            cluster.canonical = self._pick_canonical(cluster.members)
            canon_group = cluster.canonical.duplicate_group or cluster.canonical.job_id
            cluster.group_id = canon_group
            for m in cluster.members:
                m.duplicate_group = canon_group
                m.is_duplicate = m.job_id != cluster.canonical.job_id
        return clusters

    @staticmethod
    def _pick_canonical(members: list[Job]) -> Job:
        return max(
            members,
            key=lambda j: (
                len(j.description or ""),
                1 if j.application_url else 0,
                1 if (j.salary.min_value or j.salary.max_value) else 0,
                -len(j.source.value),
            ),
        )
