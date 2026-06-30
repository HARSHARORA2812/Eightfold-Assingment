"""Recruiter CSV parser."""

from __future__ import annotations

import csv
from pathlib import Path

from candidate_transformer.models import Experience, RawCandidateRecord, SourceType


class RecruiterCsvParser:
    """Parses structured recruiter CSV exports with tolerant column handling."""

    COLUMN_ALIASES = {
        "full_name": ("full_name", "name", "candidate_name"),
        "email": ("email", "emails", "primary_email"),
        "phone": ("phone", "phones", "mobile"),
        "location": ("location", "current_location"),
        "title": ("title", "current_title", "headline"),
        "company": ("company", "current_company"),
        "skills": ("skills", "skill_names"),
        "linkedin": ("linkedin", "linkedin_url"),
        "github": ("github", "github_url"),
        "portfolio": ("portfolio", "portfolio_url", "website"),
        "years_experience": ("years_experience", "experience_years", "yoe"),
    }

    def parse(self, path: Path) -> list[RawCandidateRecord]:
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    return []
                return [record for index, row in enumerate(reader, start=2) if (record := self._parse_row(row, index))]
        except (OSError, csv.Error, UnicodeDecodeError):
            return []

    def _parse_row(self, row: dict[str, str | None], row_number: int) -> RawCandidateRecord | None:
        normalized = {self._canonical_column(key): (value or "").strip() for key, value in row.items() if key}
        if not any(normalized.values()):
            return None

        email_values = self._split_multi(normalized.get("email"))
        phone_values = self._split_multi(normalized.get("phone"))
        has_profile_signal = any(
            normalized.get(key)
            for key in ("email", "phone", "company", "title", "skills", "linkedin", "github", "portfolio")
        )
        if not normalized.get("full_name") or not has_profile_signal:
            return None

        experience = []
        if normalized.get("company") or normalized.get("title"):
            experience.append(
                Experience(
                    company=normalized.get("company") or None,
                    title=normalized.get("title") or None,
                    source="csv",
                )
            )

        years_experience = None
        raw_years = normalized.get("years_experience")
        if raw_years:
            try:
                years_experience = float(raw_years)
            except ValueError:
                pass

        return RawCandidateRecord(
            source=SourceType.CSV,
            source_id=f"{path_safe_id(normalized.get('email') or normalized.get('full_name') or str(row_number))}",
            full_name=normalized.get("full_name") or None,
            emails=email_values,
            phones=phone_values,
            location_text=normalized.get("location") or None,
            headline=normalized.get("title") or None,
            years_experience=years_experience,
            skills=self._split_multi(normalized.get("skills")),
            experience=experience,
            links={
                "linkedin": normalized.get("linkedin") or None,
                "github": normalized.get("github") or None,
                "portfolio": normalized.get("portfolio") or None,
                "other": [],
            },
        )

    def _canonical_column(self, column: str) -> str:
        key = column.strip().lower()
        for canonical, aliases in self.COLUMN_ALIASES.items():
            if key in aliases:
                return canonical
        return key

    def _split_multi(self, raw_value: str | None) -> list[str]:
        if not raw_value:
            return []
        return [item.strip() for item in raw_value.replace("|", ";").split(";") if item.strip()]


def path_safe_id(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else "-" for character in value).strip("-")
