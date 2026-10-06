from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Company(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    name: str
    canonical_name: str
    careers_url: HttpUrl | None = None
    homepage: HttpUrl | None = None
    headquarters: str | None = None
    industry: str | None = None
    categories: list[str] = Field(default_factory=list)
    is_priority: bool = False
    priority_score: int = Field(default=0, ge=0, le=100)
    notes: str | None = None
    excluded: bool = False
