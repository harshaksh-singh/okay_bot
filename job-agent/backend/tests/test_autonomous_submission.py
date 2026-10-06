from __future__ import annotations

import pytest

from app.applications.preparer import ApplicationPreparer
from app.schemas.enums import ScamRisk
from app.submission.submitter import ApprovedSubmitter


class TestMockATSEndToEnd:
    def _prepare_scenario(self, preparer, profile, mock_jobs, index, match=90.0):
        job = mock_jobs[index]
        job.match_score = match
        job.scam_risk = ScamRisk.NONE
        job.is_duplicate = False
        job.rejected = False
        job.application_url = job.application_url or "https://example.com/apply"
        app = preparer.prepare(job, profile, dry_run=True)
        app.pending_user_inputs = []
        return job, app

    def test_mixed_outcomes_campaign_continues(self, profile, mock_jobs, monkeypatch):
        monkeypatch.setenv("SUBMISSION_ENABLED", "true")
        monkeypatch.setenv("DRY_RUN", "true")
        monkeypatch.setenv("AUTO_APPLY_MATCH_THRESHOLD", "40")
        monkeypatch.setenv("REVIEW_REQUIRED_MATCH_FLOOR", "20")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            preparer = ApplicationPreparer()
            submitter = ApprovedSubmitter()

            scenarios: list[tuple[str, object, object, str]] = []

            for i in range(7):
                job, app = self._prepare_scenario(preparer, profile, mock_jobs, i)
                scenarios.append(("normal", job, app, ""))

            job, app = self._prepare_scenario(preparer, profile, mock_jobs, 7)
            scenarios.append(
                ("captcha", job, app, "Please solve this reCAPTCHA to continue")
            )

            job, app = self._prepare_scenario(preparer, profile, mock_jobs, 8)
            scenarios.append(
                (
                    "legal",
                    job,
                    app,
                    "Are you a US citizen? Please confirm visa sponsorship status.",
                )
            )

            job, app = self._prepare_scenario(preparer, profile, mock_jobs, 9)
            app.cover_letter_text = (
                "I have 15+ years of experience in principal engineering roles. "
                "I earned my PhD at Stanford."
            )
            scenarios.append(("unknown_data", job, app, ""))

            outcomes: list[tuple[str, str, str | None]] = []
            for label, job, app, page_text in scenarios:
                out = submitter.submit(job, app, page_text=page_text)
                outcomes.append((label, out.outcome, out.hard_stop_reason))

            assert len(outcomes) == 10, "campaign must run through all 10 applications"

            normal = [o for lbl, o, _ in outcomes if lbl == "normal"]
            captcha = [(o, hs) for lbl, o, hs in outcomes if lbl == "captcha"]
            legal = [(o, hs) for lbl, o, hs in outcomes if lbl == "legal"]
            unknown = [o for lbl, o, _ in outcomes if lbl == "unknown_data"]

            assert normal.count("SIMULATED_SUBMIT_DRY_RUN") == 7, (
                f"7 normal jobs must reach SIMULATED_SUBMIT_DRY_RUN (dry-run mode). "
                f"Got: {normal}"
            )

            assert captcha == [("APPLICATION_BLOCKED_USER_ACTION", "CAPTCHA")], (
                f"CAPTCHA page_text must route to APPLICATION_BLOCKED_USER_ACTION with CAPTCHA. "
                f"Got: {captcha}"
            )

            assert legal and legal[0][0] == "APPLICATION_BLOCKED_USER_ACTION", (
                f"legal page_text must route to APPLICATION_BLOCKED_USER_ACTION. Got: {legal}"
            )
            assert legal[0][1] == "UNKNOWN_LEGAL_QUESTION", (
                f"legal page_text must set hard_stop_reason=UNKNOWN_LEGAL_QUESTION. Got: {legal}"
            )

            assert unknown == ["REQUIRES_USER_DATA"], (
                f"hallucinated cover letter must trigger AnswerValidationEngine → REQUIRES_USER_DATA. "
                f"Got: {unknown}"
            )
        finally:
            get_settings.cache_clear()

    def test_submission_disabled_kill_switch_blocks_everything(
        self, profile, mock_jobs, monkeypatch
    ):
        monkeypatch.setenv("SUBMISSION_ENABLED", "false")
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("AUTO_APPLY_MATCH_THRESHOLD", "40")
        monkeypatch.setenv("REVIEW_REQUIRED_MATCH_FLOOR", "20")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            preparer = ApplicationPreparer()
            submitter = ApprovedSubmitter()
            job, app = self._prepare_scenario(preparer, profile, mock_jobs, 0)

            out = submitter.submit(job, app, page_text="")

            assert out.outcome == "BLOCKED_SUBMISSION_DISABLED", (
                f"with SUBMISSION_ENABLED=false, must emit BLOCKED_SUBMISSION_DISABLED "
                f"even if DRY_RUN=false and all other gates would pass. Got: {out.outcome}"
            )
        finally:
            get_settings.cache_clear()

    def test_security_blockers_cannot_be_bypassed_even_with_submission_enabled(
        self, profile, mock_jobs, monkeypatch
    ):
        monkeypatch.setenv("SUBMISSION_ENABLED", "true")
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("AUTO_APPLY_MATCH_THRESHOLD", "40")
        monkeypatch.setenv("REVIEW_REQUIRED_MATCH_FLOOR", "20")
        from app.config import get_settings
        get_settings.cache_clear()
        try:
            preparer = ApplicationPreparer()
            submitter = ApprovedSubmitter()
            job, app = self._prepare_scenario(preparer, profile, mock_jobs, 0)

            for page_text, expected_reason in [
                ("Please solve this reCAPTCHA", "CAPTCHA"),
                ("Enter your 2FA code to continue", "MFA"),
                ("A one-time password is required to continue", "OTP"),
                ("Upload your government passport photo", "IDENTITY_VERIFICATION"),
                ("Pay the $50 application fee to continue", "PAYMENT"),
                ("Are you a US citizen with green card status?", "UNKNOWN_LEGAL_QUESTION"),
            ]:
                out = submitter.submit(job, app, page_text=page_text)
                assert out.outcome == "APPLICATION_BLOCKED_USER_ACTION", (
                    f"security blocker {expected_reason!r} must emit "
                    f"APPLICATION_BLOCKED_USER_ACTION regardless of SUBMISSION_ENABLED. "
                    f"page_text={page_text!r} → outcome={out.outcome}"
                )
                assert out.hard_stop_reason == expected_reason, (
                    f"hard_stop_reason mismatch for page_text={page_text!r}. "
                    f"Expected {expected_reason}, got {out.hard_stop_reason}"
                )
        finally:
            get_settings.cache_clear()


class TestAnswerValidationEngine:
    def test_valid_profile_passes(self, profile):
        from app.schemas.application import Application
        from app.schemas.enums import ApplicationStatus
        from app.submission.answer_validation import AnswerValidationEngine

        app = Application(
            application_id="app_x",
            job_id="j_x",
            status=ApplicationStatus.APPLICATION_PREPARED,
            cover_letter_text=f"I am {profile.full_name}, an engineer at Ethara AI.",
        )
        result = AnswerValidationEngine(profile).validate(app)
        assert result.valid, f"clean cover letter must pass: {result.violations}"

    def test_phd_claim_without_profile_phd_blocks(self, profile):
        from app.schemas.application import Application
        from app.schemas.enums import ApplicationStatus
        from app.submission.answer_validation import AnswerValidationEngine

        app = Application(
            application_id="app_phd",
            job_id="j_phd",
            status=ApplicationStatus.APPLICATION_PREPARED,
            cover_letter_text="I hold a PhD in Computer Science from Stanford.",
        )
        result = AnswerValidationEngine(profile).validate(app)
        assert not result.valid
        assert any("phd" in v.issue.lower() for v in result.violations)

    def test_15_years_experience_claim_blocks(self, profile):
        from app.schemas.application import Application
        from app.schemas.enums import ApplicationStatus
        from app.submission.answer_validation import AnswerValidationEngine

        app = Application(
            application_id="app_15y",
            job_id="j_15y",
            status=ApplicationStatus.APPLICATION_PREPARED,
            cover_letter_text="I have 15+ years of experience in ML systems.",
        )
        result = AnswerValidationEngine(profile).validate(app)
        assert not result.valid


class TestRobotsCompliance:
    def test_robots_disallowed_blocks_submission(
        self, profile, mock_jobs, monkeypatch
    ):
        monkeypatch.setenv("SUBMISSION_ENABLED", "true")
        monkeypatch.setenv("DRY_RUN", "false")
        monkeypatch.setenv("AUTO_APPLY_MATCH_THRESHOLD", "40")
        monkeypatch.setenv("REVIEW_REQUIRED_MATCH_FLOOR", "20")
        from app.config import get_settings
        get_settings.cache_clear()

        from app.discovery import http_client as hc
        monkeypatch.setattr(hc, "check_robots_allowed", lambda url: False)

        try:
            from app.applications.preparer import ApplicationPreparer
            from app.schemas.enums import ScamRisk
            from app.submission.submitter import ApprovedSubmitter

            job = mock_jobs[0]
            job.match_score = 90.0
            job.scam_risk = ScamRisk.NONE
            job.is_duplicate = False
            job.rejected = False
            job.application_url = "https://example.com/apply"
            app = ApplicationPreparer().prepare(job, profile, dry_run=True)
            app.pending_user_inputs = []

            out = ApprovedSubmitter().submit(job, app)
            assert out.outcome == "BLOCKED_ROBOTS_DISALLOWED", (
                f"disallowed robots.txt must emit BLOCKED_ROBOTS_DISALLOWED. "
                f"Got: {out.outcome}"
            )
            assert out.hard_stop_reason == "ROBOTS_DISALLOWED"
        finally:
            get_settings.cache_clear()

    def test_robots_allowed_proceeds_normally(
        self, profile, mock_jobs, monkeypatch
    ):
        monkeypatch.setenv("SUBMISSION_ENABLED", "true")
        monkeypatch.setenv("DRY_RUN", "true")
        monkeypatch.setenv("AUTO_APPLY_MATCH_THRESHOLD", "40")
        monkeypatch.setenv("REVIEW_REQUIRED_MATCH_FLOOR", "20")
        from app.config import get_settings
        get_settings.cache_clear()

        from app.discovery import http_client as hc
        monkeypatch.setattr(hc, "check_robots_allowed", lambda url: True)

        try:
            from app.applications.preparer import ApplicationPreparer
            from app.schemas.enums import ScamRisk
            from app.submission.submitter import ApprovedSubmitter

            job = mock_jobs[0]
            job.match_score = 90.0
            job.scam_risk = ScamRisk.NONE
            job.is_duplicate = False
            job.rejected = False
            job.application_url = "https://example.com/apply"
            app = ApplicationPreparer().prepare(job, profile, dry_run=True)
            app.pending_user_inputs = []

            out = ApprovedSubmitter().submit(job, app)
            assert out.outcome != "BLOCKED_ROBOTS_DISALLOWED", (
                f"allowed robots.txt must NOT emit BLOCKED_ROBOTS_DISALLOWED. "
                f"Got: {out.outcome}"
            )
        finally:
            get_settings.cache_clear()


class TestApplicationIdExtraction:
    def test_application_id_standard_format(self):
        from app.browser.assisted import _extract_application_id
        text = "Thank you! Your application ID is: APP-123456"
        assert _extract_application_id(text) == "APP-123456"

    def test_confirmation_number_hashmark(self):
        from app.browser.assisted import _extract_application_id
        text = "Confirmation number #ABC789XYZ saved to our records."
        assert _extract_application_id(text) == "ABC789XYZ"

    def test_reference_number_with_colon(self):
        from app.browser.assisted import _extract_application_id
        text = "Please note reference number: GH-2026-00142"
        assert _extract_application_id(text) == "GH-2026-00142"

    def test_lever_url_appid(self):
        from app.browser.assisted import _extract_application_id
        url = "https://jobs.lever.co/acme/apply?leverAppId=abcd-1234-ef56"
        assert _extract_application_id("", url) == "abcd-1234-ef56"

    def test_tracking_code_capture(self):
        from app.browser.assisted import _extract_application_id
        text = "Your tracking code is TRK-X91Y27, keep it for your records."
        assert _extract_application_id(text) == "TRK-X91Y27"

    def test_no_match_returns_none(self):
        from app.browser.assisted import _extract_application_id
        text = "Thank you for applying. We will be in touch."
        assert _extract_application_id(text) is None

    def test_blocklisted_tokens_rejected(self):
        from app.browser.assisted import _extract_application_id
        text = "application id: null"
        assert _extract_application_id(text) is None

    def test_too_short_candidate_rejected(self):
        from app.browser.assisted import _extract_application_id
        text = "application id: X1"
        assert _extract_application_id(text) is None


class TestCheckboxClassifier:
    def test_safe_consent_labels_classify_as_safe(self):
        from app.browser.assisted import _classify_checkbox_label
        for label in [
            "I agree to the Terms of Service",
            "I accept the Privacy Policy",
            "I acknowledge the Terms of Use and Privacy Policy",
            "I consent to data processing under GDPR",
            "Email me about similar roles",
            "I have read the Privacy Policy",
            "I certify that the information provided is accurate",
        ]:
            assert _classify_checkbox_label(label) == "safe_consent", (
                f"{label!r} must be safe_consent"
            )

    def test_legal_binding_labels_classify_as_block(self):
        from app.browser.assisted import _classify_checkbox_label
        for label in [
            "I agree to binding arbitration",
            "I waive my right to a trial by jury",
            "I agree to a class-action waiver",
            "I certify under penalty of perjury",
            "I accept the non-disclosure agreement",
            "I agree to non-compete terms",
            "I accept assignment of invention rights",
        ]:
            assert _classify_checkbox_label(label) == "legal_block", (
                f"{label!r} must be legal_block"
            )

    def test_unknown_labels_classify_as_unknown(self):
        from app.browser.assisted import _classify_checkbox_label
        for label in [
            "",
            "Click here",
            "Confirm",
            "I understand the role requirements",
            "Yes",
            "Save my preferences for next time",
        ]:
            assert _classify_checkbox_label(label) == "unknown", (
                f"{label!r} must be unknown (not auto-checked)"
            )

    def test_safe_consent_cannot_mask_a_legal_blocker(self):
        from app.browser.assisted import _classify_checkbox_label
        mixed = "I agree to the Terms of Service and binding arbitration"
        assert _classify_checkbox_label(mixed) == "legal_block", (
            "any legal signal must override safe_consent matches"
        )


class TestDropdownMatcher:
    def test_exact_match_wins(self):
        from app.browser.assisted import _match_dropdown_option
        options = ["Yes, I am authorized", "No, I require sponsorship", "Prefer not to say"]
        assert _match_dropdown_option(options, "Yes, I am authorized") == "Yes, I am authorized"

    def test_substring_match_fallback(self):
        from app.browser.assisted import _match_dropdown_option
        options = ["Yes - US citizen or permanent resident", "No - require sponsorship"]
        assert _match_dropdown_option(options, "citizen") == options[0]

    def test_no_match_returns_none(self):
        from app.browser.assisted import _match_dropdown_option
        options = ["Yes", "No"]
        assert _match_dropdown_option(options, "Maybe") is None

    def test_empty_inputs_return_none(self):
        from app.browser.assisted import _match_dropdown_option
        assert _match_dropdown_option([], "yes") is None
        assert _match_dropdown_option(["yes"], "") is None


class TestSubmitButtonDetection:
    def test_recognises_submit_apply_labels_as_submit(self):
        from app.browser.assisted import _SUBMIT_LABEL_RE
        for label in [
            "Submit",
            "Submit application",
            "Apply",
            "Apply now",
            "Send application",
            "Complete application",
            "Finish application",
        ]:
            assert _SUBMIT_LABEL_RE.match(label), f"{label!r} must match submit regex"

    def test_rejects_non_submit_labels(self):
        from app.browser.assisted import _NON_SUBMIT_LABEL_RE
        for label in [
            "Save",
            "Save draft",
            "Cancel",
            "Back",
            "Previous",
            "Preview",
            "Edit",
            "Close",
            "Discard",
            "Skip",
        ]:
            assert _NON_SUBMIT_LABEL_RE.match(label), (
                f"{label!r} must match non-submit regex (hard-exclude)"
            )

    def test_submit_regex_does_not_match_navigation_labels(self):
        from app.browser.assisted import _SUBMIT_LABEL_RE
        for label in ["Save", "Save draft", "Cancel", "Back", "Preview", "Edit"]:
            assert not _SUBMIT_LABEL_RE.match(label), (
                f"{label!r} must NOT be treated as submit"
            )
