from __future__ import annotations

from pathlib import Path

from app.email import EmailDraft, EmailDrafter
from app.observability import redact


def test_redact_openai_key():
    s = redact("Please use sk-abcdefghijklmnopqrstuvwxyz0123456789 for auth")
    assert "sk-abcdefghijklmnopqrstuvwxyz0123456789" not in s
    assert "REDACTED" in s


def test_redact_anthropic_key():
    s = redact("ANTHROPIC_API_KEY=sk-ant-apicustomapikey1234567890abc")
    assert "sk-ant-apicustomapikey" not in s


def test_redact_bearer_token():
    s = redact("Authorization: Bearer eyJhbGciOi.secretpayload.sig")
    assert "eyJhbGciOi" not in s


def test_redact_google_key():
    s = redact("GOOGLE_API_KEY=AIzaSyDummy_1234567890abcdefghij")
    assert "AIzaSy" not in s or "REDACTED" in s


def test_redact_dict_sensitive_keys():
    out = redact({"email": "u@x.com", "password": "s3cret!", "api_key": "k1234567890"})
    assert out["email"] == "u@x.com"
    assert out["password"] == "***REDACTED***"
    assert out["api_key"] == "***REDACTED***"


def test_redact_cookie():
    s = redact("cookie: session=abc123xyz7890abcde; token=def456secretvalue")
    assert "abc123xyz7890abcde" not in s
    assert "def456secretvalue" not in s


def test_email_drafter_writes_eml(tmp_path):
    drafter = EmailDrafter(drafts_dir=tmp_path)
    draft = EmailDraft(
        to="recruiter@company.com",
        subject="Application — AI Engineer — Harshaksh Singh",
        body="Hello, I am applying for the AI Engineer role.",
        sender="harshakshsingh1010@gmail.com",
    )
    path = drafter.draft(draft)
    assert path.exists()
    content = path.read_text()
    assert "To: recruiter@company.com" in content
    assert "From: harshakshsingh1010@gmail.com" in content
    assert "Subject: Application" in content


def test_email_drafter_lists_drafts(tmp_path):
    drafter = EmailDrafter(drafts_dir=tmp_path)
    drafter.draft(EmailDraft(to="a@x.com", subject="Hi 1", body="body 1"))
    drafter.draft(EmailDraft(to="b@x.com", subject="Hi 2", body="body 2"))
    drafts = drafter.list_drafts()
    assert len(drafts) == 2


def test_email_drafter_clear(tmp_path):
    drafter = EmailDrafter(drafts_dir=tmp_path)
    drafter.draft(EmailDraft(to="a@x.com", subject="Hi", body="b"))
    assert drafter.clear_drafts() == 1
    assert len(drafter.list_drafts()) == 0
