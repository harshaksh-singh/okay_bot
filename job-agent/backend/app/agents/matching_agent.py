from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.filtering import apply_hard_rules
from app.matching import MatchingEngine, apply_scoring_tier
from app.scam import ScamDetector


class MatchingAgent(BaseAgent):
    name = "matching"

    def __init__(self) -> None:
        self.engine = MatchingEngine()
        self.scam = ScamDetector()

    def run(self, context: AgentContext, previous: list[AgentResult]) -> AgentResult:
        r = self._start()
        incoming = []
        for p in previous:
            if p.agent == "extraction":
                incoming = p.jobs
                break
        if not incoming and context.jobs:
            incoming = context.jobs

        kept = []
        rejected: list[tuple] = []

        for job in incoming:
            scam_eval = self.scam.evaluate(job)
            job.scam_risk = scam_eval.risk
            job.scam_reasons = scam_eval.reasons

            breakdown, reasons, missing = self.engine.score(job, context.profile)
            total = round(breakdown.total(), 2)
            job.score_breakdown = breakdown
            job.match_score = total
            job.reason_for_match = reasons
            job.missing_requirements = missing
            job.priority = apply_scoring_tier(total, self.engine.thresholds)

            hard = apply_hard_rules(job, context.profile, scam_risk=scam_eval.risk)
            if hard.reject:
                job.rejected = True
                job.rejection_reasons = hard.reasons
                rejected.append((job, hard.reasons))
            else:
                kept.append(job)

        kept.sort(key=lambda j: j.match_score, reverse=True)

        r.jobs = kept
        r.rejected_jobs = rejected
        r.metadata["kept"] = len(kept)
        r.metadata["rejected"] = len(rejected)
        r.metadata["high_priority"] = len([j for j in kept if j.match_score >= 85])
        r.notes.append(
            f"scored {len(kept)} kept, {len(rejected)} rejected, "
            f"{r.metadata['high_priority']} high-priority"
        )
        r.mark_done()
        return r
