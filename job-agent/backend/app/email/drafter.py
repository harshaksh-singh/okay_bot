from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from app.config import get_settings
from app.observability import get_logger

log = get_logger("email")


@dataclass
class EmailDraft:
    to: str
    subject: str
    body: str
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    attachments: list[Path] = field(default_factory=list)
    sender: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    def as_eml(self) -> bytes:
        msg = EmailMessage()
        msg["To"] = self.to
        if self.sender:
            msg["From"] = self.sender
        msg["Subject"] = self.subject
        if self.cc:
            msg["Cc"] = ", ".join(self.cc)
        if self.bcc:
            msg["Bcc"] = ", ".join(self.bcc)
        msg["Date"] = self.created_at.strftime("%a, %d %b %Y %H:%M:%S +0000")
        msg.set_content(self.body)
        for path in self.attachments:
            try:
                p = Path(path)
                if p.exists():
                    msg.add_attachment(
                        p.read_bytes(),
                        maintype="application",
                        subtype="octet-stream",
                        filename=p.name,
                    )
            except Exception as e:
                log.warning("email.attachment_failed", path=str(path), error=str(e))
        return msg.as_bytes()


class EmailDrafter:
    def __init__(self, drafts_dir: Path | None = None) -> None:
        s = get_settings()
        self.drafts_dir = drafts_dir or (s.data_dir / "email_drafts")
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        self.sender = s.email_sender_address

    def draft(self, draft: EmailDraft, filename: str | None = None) -> Path:
        if not draft.sender and self.sender:
            draft.sender = self.sender
        if filename:
            if not filename.endswith(".eml"):
                filename = f"{filename}.eml"
        else:
            timestamp = draft.created_at.strftime("%Y%m%d_%H%M%S")
            safe_subject = "".join(c if c.isalnum() or c in "-_" else "_" for c in draft.subject)[:40]
            filename = f"{timestamp}_{safe_subject}.eml"
        out = self.drafts_dir / filename
        out.write_bytes(draft.as_eml())
        log.info("email.drafted", path=str(out), to=draft.to, subject=draft.subject)
        return out

    def list_drafts(self) -> list[Path]:
        return sorted(self.drafts_dir.glob("*.eml"))

    def clear_drafts(self) -> int:
        n = 0
        for p in self.list_drafts():
            try:
                p.unlink()
                n += 1
            except Exception:
                pass
        return n
