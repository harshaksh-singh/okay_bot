from __future__ import annotations

from datetime import datetime

from app.schemas.application import Application
from app.schemas.enums import ApplicationStatus, is_valid_transition


class InvalidStatusTransition(ValueError):
    pass


class ApplicationTracker:
    def transition(self, application: Application, new_status: ApplicationStatus, note: str | None = None) -> Application:
        if not is_valid_transition(application.status, new_status):
            raise InvalidStatusTransition(
                f"invalid status transition: {application.status.value} -> {new_status.value}"
            )
        now = datetime.utcnow()
        application.status_history.append((application.status, now, note))
        application.status = new_status
        application.updated_at = now

        if new_status == ApplicationStatus.APPROVED:
            application.approved_by_user = True
            application.approved_at = now
        if new_status == ApplicationStatus.SUBMITTED:
            application.submitted_at = now

        return application

    def approve(self, application: Application, note: str | None = "user approved") -> Application:
        if application.status == ApplicationStatus.APPROVED:
            return application
        if application.status in {ApplicationStatus.REVIEW_REQUIRED, ApplicationStatus.MATCHED}:
            return self.transition(application, ApplicationStatus.APPROVED, note)
        raise InvalidStatusTransition(
            f"cannot approve application in status {application.status.value}"
        )

    def mark_prepared(self, application: Application) -> Application:
        return self.transition(application, ApplicationStatus.APPLICATION_PREPARED)

    def mark_submitted(self, application: Application, evidence: str | None = None) -> Application:
        app = self.transition(application, ApplicationStatus.SUBMITTED, note=evidence)
        if evidence:
            app.submission_evidence = evidence
        return app

    def mark_rejected(self, application: Application, reason: str | None = None) -> Application:
        return self.transition(application, ApplicationStatus.REJECTED, note=reason)

    def mark_withdrawn(self, application: Application, reason: str | None = None) -> Application:
        return self.transition(application, ApplicationStatus.WITHDRAWN, note=reason)

    def mark_interview(self, application: Application, note: str | None = None, round_name: str = "screen", interviewer: str | None = None) -> Application:
        app = self.transition(application, ApplicationStatus.INTERVIEW, note)
        try:
            from sqlalchemy import select
            from app.database import SessionLocal, init_database
            from app.database.models import ApplicationRow, InterviewRow
            init_database()
            with SessionLocal() as session:
                app_row = session.scalars(select(ApplicationRow).where(ApplicationRow.application_id == application.application_id)).first()
                if app_row:
                    session.add(InterviewRow(
                        application_id=app_row.id,
                        round_name=round_name,
                        interviewer=interviewer,
                        preparation_notes=note,
                        questions=[],
                    ))
                    session.commit()
        except Exception:
            pass
        return app

    def mark_offer(self, application: Application, note: str | None = None) -> Application:
        return self.transition(application, ApplicationStatus.OFFER, note)
