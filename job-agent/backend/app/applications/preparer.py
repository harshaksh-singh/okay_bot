from __future__ import annotations

import hashlib
from pathlib import Path

from app.applications.form_mapper import FormFieldMapper
from app.config import get_settings
from app.cover_letters.generator import CoverLetterGenerator
from app.profile import Profile
from app.resumes.engine import ResumeEngine
from app.resumes.generator import ResumeGenerator
from app.schemas import Job
from app.schemas.application import Application
from app.schemas.enums import ApplicationStatus


def _application_id_for(job_id: str) -> str:
    return "app_" + hashlib.sha1(job_id.encode("utf-8")).hexdigest()[:12]


class ApplicationPreparer:
    def __init__(self, resume_generator: ResumeGenerator | None = None) -> None:
        self.resume_engine = ResumeEngine()
        self.form_mapper = FormFieldMapper()
        self.cover_letter_gen = CoverLetterGenerator()
        self._resume_generator = resume_generator

    def _generator(self) -> ResumeGenerator:
        if self._resume_generator is None:
            s = get_settings()
            self._resume_generator = ResumeGenerator(output_dir=s.generated_resumes_dir)
        return self._resume_generator

    def prepare(self, job: Job, profile: Profile, dry_run: bool = True) -> Application:
        app_id = _application_id_for(job.job_id)

        variant = self.resume_engine.choose_variant(job, profile)
        resume_path: Path | None = None
        if variant:
            user_pdf = variant.file_path
            if user_pdf and user_pdf.exists():
                resume_path = user_pdf
            else:
                resume_path = self._generator().ensure_variant(profile, variant.name)

        cover_letter = self.cover_letter_gen.generate(job, profile)

        answers = self.form_mapper.map(job, profile)
        pending = [a.field_name for a in answers if a.requires_user_input]

        status = ApplicationStatus.APPLICATION_PREPARED if not dry_run else ApplicationStatus.MATCHED

        return Application(
            application_id=app_id,
            job_id=job.job_id,
            status=status,
            application_method=job.application_method,
            resume_variant=variant.name if variant else None,
            resume_path=resume_path,
            cover_letter_text=cover_letter,
            form_answers=answers,
            pending_user_inputs=pending,
            notes="prepared in dry-run" if dry_run else "prepared (ready for user approval)",
        )
