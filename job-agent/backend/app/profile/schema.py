from __future__ import annotations

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class FactSource(str, Enum):
    PROFILE_FACT = "PROFILE_FACT"
    JOB_FACT = "JOB_FACT"
    USER_PROVIDED_FACT = "USER_PROVIDED_FACT"
    DERIVED_FACT = "DERIVED_FACT"
    UNKNOWN = "UNKNOWN"


class Fact(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    value: str
    source: FactSource = FactSource.PROFILE_FACT
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    notes: str | None = None


class Experience(BaseModel):
    company: str
    role: str
    employment_type: str
    start_date: date
    end_date: date | None = None
    location: str
    is_remote: bool = False
    bullets: list[str] = Field(default_factory=list)
    skills_used: list[str] = Field(default_factory=list)
    is_current: bool = False

    @property
    def duration_months(self) -> int:
        end = self.end_date or date.today()
        return max(0, (end.year - self.start_date.year) * 12 + (end.month - self.start_date.month))


class Project(BaseModel):
    name: str
    date_range: str
    tech_stack: list[str]
    bullets: list[str] = Field(default_factory=list)
    url: str | None = None


class SkillCategory(BaseModel):
    name: str
    skills: list[str]


class Education(BaseModel):
    degree: str
    institution: str
    location: str
    start_date: date
    end_date: date
    grade: str | None = None
    is_current: bool = False


class ResumeVariant(BaseModel):
    name: str
    target_roles: list[str]
    file_path: Path | None = None
    description: str = ""
    highlighted_skills: list[str] = Field(default_factory=list)


class Availability(BaseModel):
    current_employment: str = "Full-time"
    open_to_part_time: bool = True
    open_to_contract: bool = True
    open_to_freelance: bool = True
    open_to_remote: bool = True
    preferred_schedules: list[str] = Field(default_factory=list)
    notice_period_weeks: int | None = None
    earliest_start: date | None = None


class LocationPreferences(BaseModel):
    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)
    remote: list[str] = Field(default_factory=list)
    will_relocate: bool = False
    current_location: str = ""


class WorkAuthorization(BaseModel):
    country: str
    status: str = "UNKNOWN"
    requires_sponsorship: bool | None = None


class Profile(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    full_name: str
    headline: str
    email: EmailStr
    phone: str
    location: str
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None

    summary: str
    experiences: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    skill_categories: list[SkillCategory] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    languages_spoken: list[str] = Field(default_factory=list)

    location_preferences: LocationPreferences = Field(default_factory=LocationPreferences)
    availability: Availability = Field(default_factory=Availability)
    work_authorizations: list[WorkAuthorization] = Field(default_factory=list)

    tier1_target_roles: list[str] = Field(default_factory=list)
    tier2_target_roles: list[str] = Field(default_factory=list)
    tier3_target_roles: list[str] = Field(default_factory=list)
    hard_pass_terms: list[str] = Field(default_factory=list)

    priority_companies: list[str] = Field(default_factory=list)
    excluded_companies: list[str] = Field(default_factory=list)

    resume_variants: list[ResumeVariant] = Field(default_factory=list)

    salary_expectation_min_inr_monthly: int | None = None
    salary_expectation_min_usd_hourly: int | None = None

    @property
    def all_skills(self) -> set[str]:
        skills: set[str] = set()
        for cat in self.skill_categories:
            skills.update(s.lower() for s in cat.skills)
        return skills

    @property
    def all_target_roles(self) -> set[str]:
        return {
            r.lower()
            for r in self.tier1_target_roles + self.tier2_target_roles + self.tier3_target_roles
        }

    def total_experience_months(self) -> int:
        if not self.experiences:
            return 0
        earliest = min(e.start_date for e in self.experiences)
        latest = max((e.end_date or date.today()) for e in self.experiences)
        return max(0, (latest.year - earliest.year) * 12 + (latest.month - earliest.month))

    def to_fact_list(self) -> list[Fact]:
        facts: list[Fact] = [
            Fact(key="name", value=self.full_name),
            Fact(key="email", value=str(self.email)),
            Fact(key="phone", value=self.phone),
            Fact(key="location", value=self.location),
            Fact(key="headline", value=self.headline),
        ]
        if self.linkedin_url:
            facts.append(Fact(key="linkedin", value=self.linkedin_url))
        if self.github_url:
            facts.append(Fact(key="github", value=self.github_url))
        if self.portfolio_url:
            facts.append(Fact(key="portfolio", value=self.portfolio_url))
        for e in self.experiences:
            facts.append(
                Fact(
                    key=f"experience:{e.company}",
                    value=f"{e.role} at {e.company} ({e.start_date} -> {e.end_date or 'Present'})",
                )
            )
        for edu in self.education:
            facts.append(
                Fact(
                    key=f"education:{edu.institution}",
                    value=f"{edu.degree} at {edu.institution} ({edu.start_date} -> {edu.end_date})",
                )
            )
        return facts

    def model_dump_safe(self) -> dict[str, Any]:
        d = self.model_dump(mode="json")
        return d
