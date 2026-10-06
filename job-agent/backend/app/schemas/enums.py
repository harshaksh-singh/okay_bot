from __future__ import annotations

from enum import Enum


class JobSource(str, Enum):
    MOCK = "mock"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    NAUKRI = "naukri"
    GLASSDOOR = "glassdoor"
    WELLFOUND = "wellfound"
    HANDSHAKE = "handshake"
    HANDSHAKE_AI = "handshake_ai"
    CUTSHORT = "cutshort"
    INSTAHYRE = "instahyre"
    HIRIST = "hirist"
    FOUNDIT = "foundit"
    INTERNSHALA = "internshala"
    REMOTEOK = "remoteok"
    WEWORKREMOTELY = "weworkremotely"
    OUTLIER = "outlier"
    SURGE_AI = "surge_ai"
    SCALE_AI = "scale_ai"
    TELUS_DIGITAL_AI = "telus_digital_ai"
    COMPANY_CAREERS = "company_careers"
    GOOGLE_SEARCH = "google_search"
    BING_SEARCH = "bing_search"
    REFERRAL = "referral"
    MANUAL = "manual"


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
    VOLUNTEER = "volunteer"
    UNKNOWN = "unknown"


class RemotePolicy(str, Enum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE_LOCAL = "remote_local"
    REMOTE_COUNTRY = "remote_country"
    REMOTE_GLOBAL = "remote_global"
    REMOTE_GLOBAL_UNVERIFIED = "remote_global_unverified"
    UNKNOWN = "unknown"


class ShiftType(str, Enum):
    DAY = "day"
    EVENING = "evening"
    NIGHT = "night"
    WEEKEND = "weekend"
    FLEXIBLE = "flexible"
    ASYNC = "async"
    ROTATING = "rotating"
    UNKNOWN = "unknown"


class PriorityTier(str, Enum):
    APPLY_IMMEDIATELY = "apply_immediately"
    HIGH_PRIORITY = "high_priority"
    APPLY = "apply"
    CONSIDER = "consider"
    LOW_PRIORITY = "low_priority"
    REJECT = "reject"

    @property
    def emoji(self) -> str:
        return {
            PriorityTier.APPLY_IMMEDIATELY: "🔥",
            PriorityTier.HIGH_PRIORITY: "🔥",
            PriorityTier.APPLY: "🟢",
            PriorityTier.CONSIDER: "🟡",
            PriorityTier.LOW_PRIORITY: "🟠",
            PriorityTier.REJECT: "🔴",
        }[self]


class ApplicationStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    MATCHED = "MATCHED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    APPLICATION_PREPARED = "APPLICATION_PREPARED"
    APPLICATION_STARTED = "APPLICATION_STARTED"
    AWAITING_USER = "AWAITING_USER"
    SUBMITTED = "SUBMITTED"
    REJECTED = "REJECTED"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    WITHDRAWN = "WITHDRAWN"
    DUPLICATE = "DUPLICATE"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
    REPLIED = "REPLIED"
    NO_FURTHER_CONTACT_REQUESTED = "NO_FURTHER_CONTACT_REQUESTED"
    CLOSED = "CLOSED"


class ScamRisk(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApplicationMethod(str, Enum):
    PLATFORM_APPLY = "platform_apply"
    COMPANY_SITE = "company_site"
    EMAIL = "email"
    REFERRAL = "referral"
    RECRUITER_MESSAGE = "recruiter_message"
    FORM_URL = "form_url"
    UNKNOWN = "unknown"


ALLOWED_STATUS_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.DISCOVERED: {
        ApplicationStatus.MATCHED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.DUPLICATE,
        ApplicationStatus.EXPIRED,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.MATCHED: {
        ApplicationStatus.REVIEW_REQUIRED,
        ApplicationStatus.APPROVED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.DUPLICATE,
        ApplicationStatus.EXPIRED,
    },
    ApplicationStatus.REVIEW_REQUIRED: {
        ApplicationStatus.APPROVED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.EXPIRED,
    },
    ApplicationStatus.APPROVED: {
        ApplicationStatus.APPLICATION_PREPARED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.APPLICATION_PREPARED: {
        ApplicationStatus.APPLICATION_STARTED,
        ApplicationStatus.AWAITING_USER,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.APPLICATION_STARTED: {
        ApplicationStatus.AWAITING_USER,
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.FAILED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.AWAITING_USER: {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.FAILED,
        ApplicationStatus.EXPIRED,
    },
    ApplicationStatus.SUBMITTED: {
        ApplicationStatus.REJECTED,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.EXPIRED,
        ApplicationStatus.REPLIED,
        ApplicationStatus.NO_FURTHER_CONTACT_REQUESTED,
        ApplicationStatus.CLOSED,
    },
    ApplicationStatus.INTERVIEW: {
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.OFFER: {
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.WITHDRAWN: set(),
    ApplicationStatus.DUPLICATE: set(),
    ApplicationStatus.EXPIRED: set(),
    ApplicationStatus.FAILED: {
        ApplicationStatus.APPLICATION_PREPARED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.REPLIED: {
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.REJECTED,
        ApplicationStatus.NO_FURTHER_CONTACT_REQUESTED,
        ApplicationStatus.CLOSED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.NO_FURTHER_CONTACT_REQUESTED: set(),
    ApplicationStatus.CLOSED: set(),
}


def is_valid_transition(from_status: ApplicationStatus, to_status: ApplicationStatus) -> bool:
    if from_status == to_status:
        return True
    return to_status in ALLOWED_STATUS_TRANSITIONS.get(from_status, set())
