from __future__ import annotations

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.compliance import ComplianceViolation
from app.config import get_settings


_HARD_BYPASS_FIELDS = ("captcha_bypass", "mfa_bypass", "otp_bypass", "rate_limit_bypass")


class ComplianceAgent(BaseAgent):
    name = "compliance"

    def run(self, context: AgentContext, previous: list[AgentResult]) -> AgentResult:
        r = self._start()
        s = get_settings()

        hard: list[str] = []
        soft: list[str] = []

        for field in _HARD_BYPASS_FIELDS:
            if getattr(s, field, False):
                hard.append(f"{field.upper()}=true forbidden by Section 30 (platform compliance)")

        if s.auto_submit and not s.user_approval_required:
            hard.append("AUTO_SUBMIT=true with USER_APPROVAL_REQUIRED=false violates Section 13 (human-in-the-loop)")
        elif s.auto_submit:
            soft.append("AUTO_SUBMIT=true (approval still required by USER_APPROVAL_REQUIRED=true)")

        if s.auto_email and not s.user_approval_required:
            hard.append("AUTO_EMAIL=true with USER_APPROVAL_REQUIRED=false violates Section 18 (email approval)")
        elif s.auto_email:
            soft.append("AUTO_EMAIL=true (approval still required)")

        if s.auto_message and not s.user_approval_required:
            hard.append("AUTO_MESSAGE=true with USER_APPROVAL_REQUIRED=false violates Section 19 (recruiter approval)")

        r.metadata["hard_violations"] = hard
        r.metadata["soft_warnings"] = soft
        r.metadata["compliance_violations"] = hard + soft
        r.metadata["safety_defaults_ok"] = not hard

        if hard:
            r.errors.extend(hard)
            r.mark_done()
            if s.compliance_hard_block:
                raise ComplianceViolation(hard)
            r.notes.append("compliance_hard_block=false; violations logged but not raised (not recommended)")
            return r

        if soft:
            r.notes.append(f"compliance soft warnings: {len(soft)}")
        else:
            r.notes.append("compliance OK")
        r.mark_done()
        return r
