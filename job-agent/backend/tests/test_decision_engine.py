from __future__ import annotations

from app.schemas.application import Application
from app.schemas.enums import ApplicationStatus
from app.submission.decision_engine import (
    DecisionResult,
    FieldState,
    SubmissionDecision,
    SubmissionDecisionEngine,
)
from app.submission.hard_stops import HardStopReason


class TestEngineAutoSubmitPath:
    def test_all_verified_fields_filled_no_page_issues_returns_auto_submit(self, mock_jobs):
        job = mock_jobs[0]
        app = Application(application_id="app_t_1", job_id=job.job_id, status=ApplicationStatus.APPLICATION_PREPARED)
        engine = SubmissionDecisionEngine()
        result = engine.evaluate(
            application=app,
            job=job,
            page_text="First name Email Phone LinkedIn Resume Submit",
            filled_fields=["first_name", "last_name", "email", "phone", "linkedin", "resume"],
            detected_field_labels=["First name", "Last name", "Email", "Phone", "LinkedIn URL", "Resume"],
        )
        assert result.decision == SubmissionDecision.AUTO_SUBMIT
        assert result.is_submittable()
        assert all(s.state == FieldState.FIELD_AUTO_FILLED for s in result.field_states)


class TestEngineLegalBlocked:
    def test_arbitration_text_on_page_blocks(self, mock_jobs):
        job = mock_jobs[0]
        app = Application(application_id="app_t_2", job_id=job.job_id, status=ApplicationStatus.APPLICATION_PREPARED)
        engine = SubmissionDecisionEngine()
        result = engine.evaluate(
            application=app,
            job=job,
            page_text="By checking this box I agree to the arbitration agreement and waive my right to trial by jury",
            filled_fields=["first_name", "email"],
            detected_field_labels=["First name", "Email"],
        )
        assert result.decision == SubmissionDecision.LEGAL_BLOCKED
        assert not result.is_submittable()
        assert any("arbitration" in b.lower() for b in result.blockers)

    def test_class_action_waiver_blocks(self, mock_jobs):
        job = mock_jobs[0]
        app = Application(application_id="app_t_3", job_id=job.job_id, status=ApplicationStatus.APPLICATION_PREPARED)
        engine = SubmissionDecisionEngine()
        result = engine.evaluate(
            application=app,
            job=job,
            page_text="I agree to the class action waiver described in the terms.",
            filled_fields=["email"],
        )
        assert result.decision == SubmissionDecision.LEGAL_BLOCKED


class TestEngineSecurityBlocked:
    def test_captcha_widget_blocks(self, mock_jobs):
        job = mock_jobs[0]
        app = Application(application_id="app_t_4", job_id=job.job_id, status=ApplicationStatus.APPLICATION_PREPARED)
        engine = SubmissionDecisionEngine()
        result = engine.evaluate(
            application=app,
            job=job,
            page_text="Standard form",
            filled_fields=["first_name"],
            has_captcha_widget=True,
        )
        assert result.decision == SubmissionDecision.SECURITY_BLOCKED
        assert any("captcha" in b.lower() for b in result.blockers)

    def test_captcha_hard_stop_blocks(self, mock_jobs):
        job = mock_jobs[0]
        app = Application(application_id="app_t_5", job_id=job.job_id, status=ApplicationStatus.APPLICATION_PREPARED)
        engine = SubmissionDecisionEngine()
        result = engine.evaluate(
            application=app,
            job=job,
            page_text="",
            filled_fields=[],
            detected_hard_stops=[(HardStopReason.CAPTCHA, "Please complete the reCAPTCHA")],
        )
        assert result.decision == SubmissionDecision.SECURITY_BLOCKED

    def test_mfa_blocks(self, mock_jobs):
        job = mock_jobs[0]
        app = Application(application_id="app_t_6", job_id=job.job_id, status=ApplicationStatus.APPLICATION_PREPARED)
        engine = SubmissionDecisionEngine()
        result = engine.evaluate(
            application=app,
            job=job,
            detected_hard_stops=[(HardStopReason.MFA, "Enter authenticator code")],
            filled_fields=[],
        )
        assert result.decision == SubmissionDecision.SECURITY_BLOCKED

    def test_payment_wall_blocks(self, mock_jobs):
        job = mock_jobs[0]
        app = Application(application_id="app_t_7", job_id=job.job_id, status=ApplicationStatus.APPLICATION_PREPARED)
        engine = SubmissionDecisionEngine()
        result = engine.evaluate(
            application=app,
            job=job,
            detected_hard_stops=[(HardStopReason.PAYMENT, "application fee required")],
            filled_fields=[],
        )
        assert result.decision == SubmissionDecision.SECURITY_BLOCKED


class TestEngineUserDataRequired:
    def test_sensitive_eeo_field_in_form_requires_user_data(self, mock_jobs):
        job = mock_jobs[0]
        app = Application(application_id="app_t_8", job_id=job.job_id, status=ApplicationStatus.APPLICATION_PREPARED)
        engine = SubmissionDecisionEngine()
        result = engine.evaluate(
            application=app,
            job=job,
            page_text="Standard application form.",
            filled_fields=["first_name", "email", "phone"],
            detected_field_labels=["First name", "Email", "Phone", "Gender", "Veteran status"],
        )
        assert result.decision == SubmissionDecision.REQUIRES_USER_DATA
        assert any("gender" in b.lower() or "veteran" in b.lower() for b in result.blockers)

    def test_pending_notice_period_requires_user_data(self, mock_jobs):
        job = mock_jobs[0]
        app = Application(
            application_id="app_t_9",
            job_id=job.job_id,
            status=ApplicationStatus.APPLICATION_PREPARED,
            pending_user_inputs=["notice_period"],
        )
        engine = SubmissionDecisionEngine()
        result = engine.evaluate(
            application=app,
            job=job,
            filled_fields=["first_name", "email"],
        )
        assert result.decision == SubmissionDecision.REQUIRES_USER_DATA
        assert any("notice_period" in b for b in result.blockers)


class TestEngineRealWorldFormShapes:
    def test_anthropic_shaped_form_returns_legal_blocked(self, mock_jobs):
        job = mock_jobs[0]
        app = Application(
            application_id="app_anthro",
            job_id=job.job_id,
            status=ApplicationStatus.APPLICATION_PREPARED,
        )
        engine = SubmissionDecisionEngine()
        result = engine.evaluate(
            application=app,
            job=job,
            page_text=(
                "First Name Last Name Email Phone Resume LinkedIn Profile. "
                "Why Anthropic? Have you ever interviewed at Anthropic before? "
                "Agreement to Arbitrate. I understand and agree that both Anthropic "
                "and I waive our respective rights to trial by jury in connection with any claims."
            ),
            filled_fields=["first_name", "last_name", "email", "phone", "linkedin", "resume"],
            detected_field_labels=[
                "First Name", "Last Name", "Email", "Phone", "Resume", "LinkedIn Profile",
                "Agreement to Arbitrate", "Gender", "Hispanic/Latino", "Veteran Status",
            ],
        )
        assert result.decision == SubmissionDecision.LEGAL_BLOCKED
        legal_block_found = any("arbitration" in b.lower() or "waive" in b.lower() for b in result.blockers)
        assert legal_block_found, f"Expected arbitration blocker. Got: {result.blockers}"

    def test_mock_ats_minimal_form_returns_auto_submit(self, mock_jobs):
        job = mock_jobs[0]
        app = Application(
            application_id="app_mock",
            job_id=job.job_id,
            status=ApplicationStatus.APPLICATION_PREPARED,
        )
        engine = SubmissionDecisionEngine()
        result = engine.evaluate(
            application=app,
            job=job,
            page_text="Mock ATS: enter your contact info and submit.",
            filled_fields=["first_name", "last_name", "email", "phone", "resume"],
            detected_field_labels=["First Name", "Last Name", "Email", "Phone", "Resume"],
        )
        assert result.decision == SubmissionDecision.AUTO_SUBMIT, (
            f"Minimal form with all fields filled should AUTO_SUBMIT. "
            f"Decision: {result.decision}, Blockers: {result.blockers}"
        )
