from __future__ import annotations

import re
from dataclasses import dataclass

from app.harban.enums import OpportunityType
from app.harban.services import match_services
from app.schemas import Job


_BUYING_SIGNAL_PATTERNS = [
    (re.compile(r"\b(ai\s+consultant|ai\s+contractor|freelance\s+ai|ai\s+agency|ai\s+partner|development\s+partner)\b", re.I), "contract/consultant intent"),
    (re.compile(r"\b(looking\s+for\s+ai\s+(consultant|contractor|agency|partner|developer))\b", re.I), "explicit AI consultant demand"),
    (re.compile(r"\b(llm\s+consultant|rag\s+(developer|consultant)|ai\s+agent\s+(developer|consultant))\b", re.I), "LLM/RAG/agent consultant"),
    (re.compile(r"\b(ai\s+evaluation|llm\s+evaluation|model\s+benchmarking|model\s+evaluation)\b", re.I), "evaluation/benchmarking need"),
    (re.compile(r"\b(hiring\s+ai\s+(engineer|researcher|scientist|team))\b", re.I), "hiring AI team"),
    (re.compile(r"\b(launching|building|developing)\s+(an\s+)?ai\s+(product|platform|feature)\b", re.I), "AI product build-out"),
    (re.compile(r"\b(series\s+[abcd]|seed\s+funding|raised\s+\$)\b", re.I), "funding signal"),
    (re.compile(r"\b(contract\s+ai\s+engineer|contract\s+ml\s+engineer|part[-\s]time\s+contract)\b", re.I), "contract engagement"),
]

_AI_RELEVANCE_PATTERNS = [
    (re.compile(r"\b(llm|large\s+language\s+model|gpt|claude|gemini)\b", re.I), "LLM"),
    (re.compile(r"\b(rag|retrieval\s+augmented)\b", re.I), "RAG"),
    (re.compile(r"\b(ai\s+agent|agentic|langchain|langgraph)\b", re.I), "AI agents"),
    (re.compile(r"\b(ml|machine\s+learning|deep\s+learning|pytorch|tensorflow)\b", re.I), "ML foundations"),
    (re.compile(r"\b(fine[-\s]?tuning|rlhf|sft|lora)\b", re.I), "model training"),
    (re.compile(r"\b(generative\s+ai|genai)\b", re.I), "generative AI"),
    (re.compile(r"\b(evaluation|benchmark|verifier|oracle\s+solution)\b", re.I), "evaluation discipline"),
]

_INDIA_LOCATIONS = {"gurugram", "gurgaon", "noida", "delhi ncr", "delhi", "india", "bangalore", "bengaluru", "mumbai", "hyderabad", "pune", "chennai"}


@dataclass
class ClientScoreBreakdown:
    ai_relevance: float = 0.0
    buying_signal: float = 0.0
    technical_fit: float = 0.0
    company_quality: float = 0.0
    recent_activity: float = 0.0
    hiring_signal: float = 0.0
    geographic_fit: float = 0.0
    reachability: float = 0.0

    def total(self) -> float:
        return (
            self.ai_relevance + self.buying_signal + self.technical_fit + self.company_quality
            + self.recent_activity + self.hiring_signal + self.geographic_fit + self.reachability
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "ai_relevance": self.ai_relevance,
            "buying_signal": self.buying_signal,
            "technical_fit": self.technical_fit,
            "company_quality": self.company_quality,
            "recent_activity": self.recent_activity,
            "hiring_signal": self.hiring_signal,
            "geographic_fit": self.geographic_fit,
            "reachability": self.reachability,
        }


class HarbanClientScorer:
    def score_job_as_client_lead(self, job: Job) -> tuple[ClientScoreBreakdown, list[str], list[str]]:
        text = " ".join([job.title or "", job.description or "", " ".join(job.requirements or [])])
        breakdown = ClientScoreBreakdown()
        buying_reasons: list[str] = []
        ai_reasons: list[str] = []

        ai_hits = sum(1 for p, _ in _AI_RELEVANCE_PATTERNS if p.search(text))
        breakdown.ai_relevance = min(25.0, ai_hits * 5.0)
        for p, label in _AI_RELEVANCE_PATTERNS:
            if p.search(text):
                ai_reasons.append(f"AI signal: {label}")

        buy_hits = 0
        for p, label in _BUYING_SIGNAL_PATTERNS:
            if p.search(text):
                buy_hits += 1
                buying_reasons.append(f"buying signal: {label}")
        breakdown.buying_signal = min(20.0, buy_hits * 7.0)

        services = match_services(text)
        breakdown.technical_fit = min(15.0, len(services) * 5.0)

        from app.data.companies import PRIORITY_COMPANIES
        prio = {c["canonical"] for c in PRIORITY_COMPANIES}
        canon = re.sub(r"[^a-z0-9]", "", (job.company or "").lower())
        if canon in prio or any(canon in p or p in canon for p in prio if canon):
            breakdown.company_quality = 10.0
        else:
            breakdown.company_quality = 5.0

        if job.posted_at:
            from datetime import datetime, timezone
            age_days = (datetime.now(timezone.utc).replace(tzinfo=None) - job.posted_at.replace(tzinfo=None)).days
            if age_days <= 7:
                breakdown.recent_activity = 10.0
            elif age_days <= 30:
                breakdown.recent_activity = 6.0
            else:
                breakdown.recent_activity = 2.0
        else:
            breakdown.recent_activity = 3.0

        breakdown.hiring_signal = 10.0 if "hiring" in text.lower() or "looking" in text.lower() else 5.0

        loc = (job.location or "").lower()
        if any(x in loc for x in _INDIA_LOCATIONS):
            breakdown.geographic_fit = 5.0
        elif "remote" in loc:
            breakdown.geographic_fit = 4.0
        else:
            breakdown.geographic_fit = 2.0

        breakdown.reachability = 5.0 if (job.application_url or job.application_email) else 2.0

        return breakdown, ai_reasons, buying_reasons


class DualOpportunityClassifier:
    def __init__(self, personal_threshold: float = 70.0, client_threshold: float = 70.0) -> None:
        self.personal_threshold = personal_threshold
        self.client_threshold = client_threshold

    def classify(self, personal_score: float, client_score: float) -> OpportunityType:
        p_hit = personal_score >= self.personal_threshold
        c_hit = client_score >= self.client_threshold
        if p_hit and c_hit:
            return OpportunityType.BOTH
        if p_hit:
            return OpportunityType.JOB
        if c_hit:
            return OpportunityType.CLIENT
        return OpportunityType.NEITHER
