"""Pydantic models for raw parsed data and the canonical candidate schema."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceType(str, Enum):
    CSV = "csv"
    RESUME = "resume"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


CONFIDENCE_VALUES: dict[Confidence, float] = {
    Confidence.LOW: 0.35,
    Confidence.MEDIUM: 0.65,
    Confidence.HIGH: 0.9,
}


class Provenance(BaseModel):
    field: str
    source: str
    method: str
    confidence: float = Field(ge=0.0, le=1.0)
    value: Any | None = None


class Location(BaseModel):
    city: str | None = None
    region: str | None = None
    country: str | None = None


class Links(BaseModel):
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    other: list[str] = Field(default_factory=list)


class Skill(BaseModel):
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[str] = Field(default_factory=list)


class Experience(BaseModel):
    company: str | None = None
    title: str | None = None
    start: str | None = None
    end: str | None = None
    summary: str | None = None
    source: str | None = None
    confidence: float = Field(default=0.65, ge=0.0, le=1.0)


class Education(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    end_year: int | None = None
    source: str | None = None
    confidence: float = Field(default=0.65, ge=0.0, le=1.0)


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    full_name: str | None = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    location: Location = Field(default_factory=Location)
    links: Links = Field(default_factory=Links)
    headline: str | None = None
    years_experience: float | None = None
    skills: list[Skill] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("emails")
    @classmethod
    def emails_are_lowercase(cls, emails: list[str]) -> list[str]:
        return [email.lower() for email in emails]


class RawCandidateRecord(BaseModel):
    """Source-specific parsed values before canonical merge."""

    source: SourceType
    source_id: str
    full_name: str | None = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    location_text: str | None = None
    links: Links = Field(default_factory=Links)
    headline: str | None = None
    years_experience: float | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    extraction_warnings: list[str] = Field(default_factory=list)


class ProjectionField(BaseModel):
    path: str
    from_: str | None = Field(default=None, alias="from")
    type: str | None = None
    required: bool = False
    normalize: str | None = None

    @property
    def source_path(self) -> str:
        return self.from_ or self.path


class ProjectionConfig(BaseModel):
    fields: list[ProjectionField] | None = None
    include_provenance: bool = True
    include_confidence: bool = True
    on_missing: Literal["null", "omit", "error"] = "null"
