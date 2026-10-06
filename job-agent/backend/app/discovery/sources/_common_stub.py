from __future__ import annotations

from app.discovery.base import BaseSource, SourceContext, SourceResult
from app.schemas.enums import JobSource


class Phase2SourceStub(BaseSource):
    source_id: JobSource = JobSource.MANUAL
    phase2_notice: str = "This source will be implemented in Phase 2."
    settings_flag: str = ""

    def is_enabled(self) -> bool:
        if not self.settings_flag:
            return False
        from app.config import get_settings
        return bool(getattr(get_settings(), self.settings_flag, False))

    def discover(self, context: SourceContext) -> SourceResult:
        r = SourceResult(source=self.source_id)
        r.errors.append(self.phase2_notice)
        return r


class IndeedStub(Phase2SourceStub):
    source_id = JobSource.INDEED
    settings_flag = "indeed_enabled"
    phase2_notice = "Indeed: logged-in scraping violates ToS. Discovery routes through assisted-application mode (user drives Indeed in their own browser)."


class NaukriStub(Phase2SourceStub):
    source_id = JobSource.NAUKRI
    settings_flag = "naukri_enabled"
    phase2_notice = "Naukri: logged-in scraping violates ToS. Discovery routes through persistent Playwright profile (user logs in themselves)."


class GoogleSearchStub(Phase2SourceStub):
    source_id = JobSource.GOOGLE_SEARCH
    settings_flag = "google_search_enabled"
    phase2_notice = "Google CSE adapter is live when GOOGLE_CSE_API_KEY + GOOGLE_CSE_ENGINE_ID are set; this stub only triggers on misconfiguration."


class CompanyCareersStub(Phase2SourceStub):
    source_id = JobSource.COMPANY_CAREERS
    settings_flag = "company_careers_enabled"
    phase2_notice = "Company careers: Greenhouse / Lever / Ashby adapters are live; this stub only triggers on misconfiguration."


class GlassdoorStub(Phase2SourceStub):
    source_id = JobSource.GLASSDOOR
    settings_flag = "glassdoor_enabled"
    phase2_notice = (
        "Glassdoor logged-in scraping violates ToS. Per brief Section 60, this is Discovery + User-Assisted Application mode: "
        "user visits glassdoor.com in their own browser, bot opens the specific role URL on request."
    )


class WellfoundStub(Phase2SourceStub):
    source_id = JobSource.WELLFOUND
    settings_flag = "wellfound_enabled"
    phase2_notice = (
        "Wellfound (AngelList) logged-in scraping violates ToS. Discovery routes through assisted-application mode: "
        "user signs in to wellfound.com themselves; bot opens job pages and prepares answers."
    )


class HandshakeStub(Phase2SourceStub):
    source_id = JobSource.HANDSHAKE
    settings_flag = "handshake_enabled"
    phase2_notice = (
        "Handshake (joinhandshake.com) is student/alumni-only; logged-in scraping violates ToS. "
        "Handshake AI (the frontier-model data platform at joinhandshake.ai) IS a priority company; see priority_companies."
    )


class CutshortStub(Phase2SourceStub):
    source_id = JobSource.CUTSHORT
    settings_flag = "cutshort_enabled"
    phase2_notice = "Cutshort logged-in scraping violates ToS. Discovery routes through assisted-application mode."


class InstahyreStub(Phase2SourceStub):
    source_id = JobSource.INSTAHYRE
    settings_flag = "instahyre_enabled"
    phase2_notice = "Instahyre logged-in scraping violates ToS. Discovery routes through assisted-application mode."


class HiristStub(Phase2SourceStub):
    source_id = JobSource.HIRIST
    settings_flag = "hirist_enabled"
    phase2_notice = "Hirist logged-in scraping violates ToS. Discovery routes through assisted-application mode."


class FounditStub(Phase2SourceStub):
    source_id = JobSource.FOUNDIT
    settings_flag = "foundit_enabled"
    phase2_notice = "Foundit (ex-Monster India) logged-in scraping violates ToS. Discovery routes through assisted-application mode."


class InternshalaStub(Phase2SourceStub):
    source_id = JobSource.INTERNSHALA
    settings_flag = "internshala_enabled"
    phase2_notice = "Internshala logged-in scraping violates ToS. User signs in themselves in persistent Playwright profile."


class OutlierStub(Phase2SourceStub):
    source_id = JobSource.OUTLIER
    settings_flag = "outlier_enabled"
    phase2_notice = (
        "Outlier.ai contractor platform has no public job API. User signs in at outlier.ai themselves; "
        "bot can prepare project applications on request."
    )


class SurgeAiStub(Phase2SourceStub):
    source_id = JobSource.SURGE_AI
    settings_flag = "surge_ai_enabled"
    phase2_notice = (
        "Surge AI contractor platform has no public job API. User signs in at surgehq.ai themselves; "
        "bot can prepare project applications on request."
    )


class TelusDigitalAiStub(Phase2SourceStub):
    source_id = JobSource.TELUS_DIGITAL_AI
    settings_flag = "telus_digital_ai_enabled"
    phase2_notice = (
        "TELUS Digital AI contractor platform has no public job API. User signs in at "
        "telusinternational.com themselves; bot can prepare project applications on request."
    )
