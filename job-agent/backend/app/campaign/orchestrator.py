from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable


class CampaignStrategy(str, Enum):
    TOP_LATEST = "top_latest"
    BEST_MATCH = "best_match"
    LATEST = "latest"
    AI_ML_FIRST = "ai_ml_first"


_LIVE_CONFIRMED_OUTCOMES = {"SUBMITTED_LIVE", "SUBMITTED_CONFIRMED"}
_SIMULATED_DRY_RUN_OUTCOMES = {"SIMULATED_SUBMIT_DRY_RUN"}
_SECURITY_BLOCKED_HINTS = {"BLOCKED_HARD_STOP", "BLOCKED_SECURITY_BLOCKED", "APPLICATION_BLOCKED_USER_ACTION"}
_LEGAL_BLOCKED_HINTS = {"BLOCKED_LEGAL_BLOCKED"}
_USER_DATA_HINTS = {
    "BLOCKED_REQUIRES_USER_DATA",
    "REQUIRES_USER_DATA",
    "AWAITING_USER_CONFIRMATION",
    "AWAITING_AUTO_SUBMIT_FLAG",
    "SUBMITTED_PENDING_CONFIRMATION",
    "SUBMISSION_UNCERTAIN",
    "AUTONOMOUS_CLICK_FAILED",
    "BLOCKED_SUBMISSION_DISABLED",
}
_INFRA_BLOCKED_HINTS = {"SUBMITTED_PLACEHOLDER_REQUIRES_BROWSER", "BLOCKED_ROBOTS_DISALLOWED"}
_ELIGIBILITY_REJECTED_HINTS = {"REJECTED_BY_ELIGIBILITY", "DRY_RUN_PREPARED"}


@dataclass
class CampaignConfig:
    target_confirmed: int = 10
    max_attempts: int = 30
    strategy: CampaignStrategy = CampaignStrategy.TOP_LATEST
    dry_run: bool = True
    min_match_score: float = 40.0
    freshness_days: int = 7


@dataclass
class CampaignResult:
    config: CampaignConfig
    started_at: datetime
    finished_at: datetime | None = None
    jobs_discovered: int = 0
    jobs_eligible: int = 0
    attempted: int = 0
    confirmed: int = 0
    simulated_dry_run: int = 0
    blocked_security: int = 0
    blocked_legal: int = 0
    requires_user_data: int = 0
    infra_blocked: int = 0
    rejected: int = 0
    failed: int = 0
    skipped_idempotent: int = 0
    outcomes: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def is_target_reached(self) -> bool:
        if self.config.dry_run:
            return self.simulated_dry_run >= self.config.target_confirmed
        return self.confirmed >= self.config.target_confirmed

    def to_dict(self) -> dict:
        return {
            "config": {
                "target_confirmed": self.config.target_confirmed,
                "max_attempts": self.config.max_attempts,
                "strategy": self.config.strategy.value,
                "dry_run": self.config.dry_run,
                "min_match_score": self.config.min_match_score,
                "freshness_days": self.config.freshness_days,
            },
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "jobs_discovered": self.jobs_discovered,
            "jobs_eligible": self.jobs_eligible,
            "attempted": self.attempted,
            "confirmed": self.confirmed,
            "simulated_dry_run": self.simulated_dry_run,
            "blocked_security": self.blocked_security,
            "blocked_legal": self.blocked_legal,
            "requires_user_data": self.requires_user_data,
            "failed": self.failed,
            "skipped_idempotent": self.skipped_idempotent,
            "outcomes": self.outcomes,
            "errors": self.errors,
            "target_reached": self.is_target_reached(),
        }


def compute_idempotency_key(application_id: str, job_id: str, channel: str = "live_submit") -> str:
    raw = f"{application_id}|{job_id}|{channel}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:48]


def classify_outcome(outcome_str: str) -> str:
    if outcome_str in _LIVE_CONFIRMED_OUTCOMES:
        return "confirmed"
    if outcome_str in _SIMULATED_DRY_RUN_OUTCOMES:
        return "simulated_dry_run"
    if outcome_str in _INFRA_BLOCKED_HINTS:
        return "infra_blocked"
    if outcome_str in _SECURITY_BLOCKED_HINTS or "SECURITY" in outcome_str:
        return "blocked_security"
    if outcome_str in _LEGAL_BLOCKED_HINTS or "LEGAL" in outcome_str:
        return "blocked_legal"
    if outcome_str in _USER_DATA_HINTS or "USER_DATA" in outcome_str or "AWAITING" in outcome_str:
        return "requires_user_data"
    if outcome_str == "SKIPPED_IDEMPOTENT":
        return "skipped_idempotent"
    if outcome_str in _ELIGIBILITY_REJECTED_HINTS:
        return "rejected"
    return "failed"


class CampaignOrchestrator:
    def __init__(self, pipeline_runner: Callable | None = None) -> None:
        self._pipeline_runner = pipeline_runner

    def _default_pipeline_runner(self, profile):
        from app.cli.main import _build_context
        from app.agents.orchestrator import JobAgentOrchestrator
        ctx = _build_context(profile)
        return JobAgentOrchestrator().run(ctx)

    def run(self, config: CampaignConfig, profile) -> CampaignResult:
        import os
        now = datetime.utcnow()
        result = CampaignResult(config=config, started_at=now)

        runner = self._pipeline_runner or self._default_pipeline_runner

        env_overrides = {}
        if config.dry_run:
            env_overrides["DRY_RUN"] = "true"
            env_overrides["AUTO_SUBMIT_APPROVED"] = "false"
        _prev_env = {k: os.environ.get(k) for k in env_overrides}
        for k, v in env_overrides.items():
            os.environ[k] = v
        try:
            from app.config import get_settings
            get_settings.cache_clear()
        except Exception:
            pass

        try:
            pipeline_result = runner(profile)
        except Exception as e:
            result.errors.append(f"pipeline_fatal: {e!r}")
            result.finished_at = datetime.utcnow()
            return result
        finally:
            for k, prev in _prev_env.items():
                if prev is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = prev
            try:
                from app.config import get_settings as _gs
                _gs.cache_clear()
            except Exception:
                pass

        try:
            matched = getattr(pipeline_result, "matched_jobs", None) or []
            result.jobs_discovered = len(matched) if hasattr(matched, "__len__") else 0
        except Exception:
            result.jobs_discovered = 0

        submission = None
        try:
            submission = pipeline_result.get("submission") if hasattr(pipeline_result, "get") else None
        except Exception:
            submission = None

        if submission is None:
            result.errors.append("no_submission_agent_result")
            result.finished_at = datetime.utcnow()
            return result

        outcomes = []
        try:
            outcomes = submission.metadata.get("outcomes", []) or []
        except Exception:
            outcomes = []

        result.jobs_eligible = len(outcomes)
        result.attempted = len(outcomes)

        for o in outcomes:
            outcome_str = o.get("outcome", "") if isinstance(o, dict) else getattr(o, "outcome", "")
            category = classify_outcome(outcome_str)

            if category == "confirmed":
                result.confirmed += 1
            elif category == "simulated_dry_run":
                result.simulated_dry_run += 1
            elif category == "blocked_security":
                result.blocked_security += 1
            elif category == "blocked_legal":
                result.blocked_legal += 1
            elif category == "requires_user_data":
                result.requires_user_data += 1
            elif category == "infra_blocked":
                result.infra_blocked += 1
            elif category == "rejected":
                result.rejected += 1
            elif category == "skipped_idempotent":
                result.skipped_idempotent += 1
            else:
                result.failed += 1

            if len(result.outcomes) < 100:
                result.outcomes.append({
                    "outcome": outcome_str,
                    "category": category,
                    "application_id": o.get("application_id") if isinstance(o, dict) else None,
                    "job_id": o.get("job_id") if isinstance(o, dict) else None,
                })

        result.finished_at = datetime.utcnow()
        return result
