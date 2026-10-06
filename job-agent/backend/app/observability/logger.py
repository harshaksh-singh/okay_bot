from __future__ import annotations

import logging
import re
from typing import Any

import structlog

from app.config import get_settings


_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("bearer", re.compile(r"(bearer\s+)([A-Za-z0-9_\-\.]+)", re.I)),
    ("api_key", re.compile(r"(api[_\-]?key[\"'\s:=]+)([A-Za-z0-9_\-]{10,})", re.I)),
    ("sk_openai", re.compile(r"\b(sk-[A-Za-z0-9]{20,})\b")),
    ("anthropic_key", re.compile(r"\b(sk-ant-[A-Za-z0-9\-]{20,})\b")),
    ("google_key", re.compile(r"\b(AIza[0-9A-Za-z\-_]{20,})\b")),
    ("password", re.compile(r"(password[\"'\s:=]+)(\S+)", re.I)),
    ("token", re.compile(r"(token[\"'\s:=]+)([A-Za-z0-9_\-\.]{10,})", re.I)),
    ("cookie", re.compile(r"(cookie[\"'\s:=]+)([^\s;,]+)", re.I)),
    ("session", re.compile(r"(session[\"'\s:=]+)([A-Za-z0-9_\-]{10,})", re.I)),
    ("otp", re.compile(r"(otp[\"'\s:=]+)(\d{4,8})", re.I)),
]


def redact(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, dict):
        return {k: ("***REDACTED***" if _looks_sensitive_key(k) else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(redact(v) for v in value)
    if not isinstance(value, str):
        try:
            value = str(value)
        except Exception:
            return "***UNSTRINGIFIABLE***"
    s = value
    for _, pattern in _SECRET_PATTERNS:
        s = pattern.sub(lambda m: (m.group(1) + "***REDACTED***") if m.lastindex and m.lastindex >= 2 else "***REDACTED***", s)
    return s


_SENSITIVE_KEYS = {
    "password", "passwd", "pwd", "secret", "api_key", "apikey", "auth_token",
    "access_token", "refresh_token", "session_token", "cookie", "session",
    "authorization", "bearer", "otp", "otp_code", "mfa_code", "credit_card",
    "cvv", "ssn", "aadhaar", "pan",
}


def _looks_sensitive_key(key: str) -> bool:
    k = key.lower().replace("-", "_")
    return k in _SENSITIVE_KEYS or any(sk in k for sk in _SENSITIVE_KEYS)


def _redact_processor(_, __, event_dict: dict[str, Any]) -> dict[str, Any]:
    return redact(event_dict)


_configured = False


def setup_logging(level: str | None = None) -> None:
    global _configured
    if _configured:
        return
    s = get_settings()
    log_level = (level or s.log_level or "INFO").upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact_processor,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level, logging.INFO)),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    setup_logging()
    return structlog.get_logger(name)
