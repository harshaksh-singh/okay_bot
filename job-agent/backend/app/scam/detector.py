from __future__ import annotations

import re
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.schemas import Job
from app.schemas.enums import ScamRisk


_RED_FLAGS: list[tuple[str, re.Pattern[str], int]] = [
    ("upfront_payment", re.compile(r"\b(registration\s*fee|training\s*fee|pay(ment)?\s*(up\s*front|upfront|required)|security\s*deposit|processing\s*fee)\b", re.I), 40),
    ("crypto_payment", re.compile(r"\b(pay\s*in\s*(bitcoin|btc|eth|usdt|crypto)|crypto\s*wallet\s*required|airdrop)\b", re.I), 50),
    ("whatsapp_only", re.compile(r"\b(whatsapp\s*only|contact\s*only\s*on\s*whatsapp|dm\s*on\s*whatsapp|send.*whatsapp)\b", re.I), 25),
    ("telegram_only", re.compile(r"\b(telegram\s*only|dm\s*on\s*telegram|@[a-z0-9_]+\s*on\s*telegram)\b", re.I), 25),
    ("mlm_terms", re.compile(r"\b(multi\s*level\s*marketing|mlm|network\s*marketing|downline|pyramid|binary\s*plan|unlimited\s*earning\s*potential|become\s*your\s*own\s*boss)\b", re.I), 35),
    ("unrealistic_salary", re.compile(r"(₹|\$|usd|inr)\s*\d{2,}\s*(lakh|lac|k|crore)\s*(per\s*)?(day|week|month)|earn\s*\$?\d{3,}\s*/\s*day", re.I), 20),
    ("gift_card", re.compile(r"\b(gift\s*card|amazon\s*voucher|paypal\s*friends\s*and\s*family|western\s*union)\b", re.I), 40),
    ("personal_bank_only", re.compile(r"\b(send.*(bank\s*account|aadhaar|pan\s*card|passport)\s*(first|upfront))\b", re.I), 40),
    ("vague_role", re.compile(r"\b(data\s*entry\s*from\s*home|typing\s*job\s*at\s*home|copy\s*paste\s*work|form\s*filling\s*job)\b", re.I), 30),
    ("no_company", re.compile(r"\b(private\s*employer|individual\s*employer|confidential\s*company|not\s*disclosed)\b", re.I), 10),
    ("too_good_to_be_true", re.compile(r"\b(no\s*experience\s*required.*(six\s*figure|high\s*salary|lakh)|work\s*2\s*hours\s*earn)\b", re.I), 25),
    ("recruitment_scam_contact", re.compile(r"\b(hr@gmail|hr@yahoo|recruiter@outlook|director@live)\b", re.I), 25),
]

_SUSPICIOUS_TLDS = {".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".click", ".work", ".support"}
_FREE_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "live.com", "aol.com"}


class ScamEvaluation(BaseModel):
    risk: ScamRisk = ScamRisk.NONE
    score: int = Field(default=0, ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)

    @property
    def is_high_risk(self) -> bool:
        return self.risk == ScamRisk.HIGH


class ScamDetector:
    def evaluate(self, job: Job) -> ScamEvaluation:
        text = " ".join([
            job.title or "",
            job.company or "",
            job.description or "",
            " ".join(job.requirements or []),
            " ".join(job.responsibilities or []),
            job.application_email or "",
            str(job.application_url) if job.application_url else "",
        ])

        score = 0
        reasons: list[str] = []

        for name, pattern, weight in _RED_FLAGS:
            if pattern.search(text):
                score += weight
                reasons.append(f"scam signal: {name}")

        if job.application_email:
            domain = job.application_email.split("@")[-1].lower().strip()
            company_norm = re.sub(r"[^a-z0-9]", "", job.company.lower())
            if domain in _FREE_EMAIL_DOMAINS and company_norm not in domain:
                score += 20
                reasons.append(f"scam signal: free email domain ({domain}) does not match company")

        if job.application_url:
            try:
                parsed = urlparse(str(job.application_url))
                host = (parsed.hostname or "").lower()
                for tld in _SUSPICIOUS_TLDS:
                    if host.endswith(tld):
                        score += 25
                        reasons.append(f"scam signal: suspicious TLD ({tld}) in application URL")
                        break
            except Exception:
                pass

        if not job.company.strip():
            score += 20
            reasons.append("scam signal: no identifiable company")

        if job.salary.raw and re.search(r"(2\s*lakh\s*per\s*day|50000\s*per\s*day|1\s*lakh\s*per\s*day)", job.salary.raw, re.I):
            score += 25
            reasons.append("scam signal: unrealistic salary")

        if score == 0:
            risk = ScamRisk.NONE
        elif score < 20:
            risk = ScamRisk.LOW
        elif score < 50:
            risk = ScamRisk.MEDIUM
        else:
            risk = ScamRisk.HIGH

        return ScamEvaluation(risk=risk, score=min(100, score), reasons=reasons)
