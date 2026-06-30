"""Deterministic normalizers used by parsers, merging, and projection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import phonenumbers
import pycountry
from dateutil import parser as date_parser


DEFAULT_SKILLS = {
    "py": "Python",
    "python": "Python",
    "python3": "Python",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "react": "React",
    "react.js": "React",
    "node": "Node.js",
    "node.js": "Node.js",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "sql": "SQL",
    "aws": "AWS",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "nlp": "Natural Language Processing",
}


@dataclass(frozen=True)
class NormalizationResult:
    value: str | None
    warning: str | None = None


@dataclass
class Normalizer:
    default_region: str = "US"
    skill_dictionary: dict[str, str] = field(default_factory=lambda: DEFAULT_SKILLS.copy())

    @classmethod
    def from_skill_file(cls, path: str | Path | None, default_region: str = "US") -> "Normalizer":
        normalizer = cls(default_region=default_region)
        if path is None:
            return normalizer

        import json

        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return normalizer

        aliases = data.get("aliases", data)
        for alias, canonical in aliases.items():
            normalizer.skill_dictionary[normalizer._skill_key(alias)] = str(canonical)
        return normalizer

    def normalize_email(self, email: str) -> str | None:
        email = email.strip().lower()
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            return email
        return None

    def normalize_phone(self, raw_phone: str) -> NormalizationResult:
        try:
            parsed = phonenumbers.parse(raw_phone, self.default_region)
        except phonenumbers.NumberParseException:
            return NormalizationResult(None, "invalid phone number")

        if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
            return NormalizationResult(None, "invalid phone number")

        return NormalizationResult(phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164))

    def normalize_country(self, raw_country: str | None) -> str | None:
        if not raw_country:
            return None
        text = raw_country.strip()
        if not text:
            return None
        if len(text) == 2 and pycountry.countries.get(alpha_2=text.upper()):
            return text.upper()

        country = pycountry.countries.get(name=text)
        if not country and len(text) > 2:
            try:
                matches = pycountry.countries.search_fuzzy(text)
            except LookupError:
                matches = []
            country = matches[0] if matches else None
        return country.alpha_2 if country else None

    def normalize_date(self, raw_date: str | None) -> str | None:
        if not raw_date:
            return None
        text = raw_date.strip()
        if not text or text.lower() in {"present", "current", "now"}:
            return None
        try:
            parsed = date_parser.parse(text, default=datetime(1900, 1, 1), fuzzy=True)
        except (ValueError, OverflowError):
            return None
        return f"{parsed.year:04d}-{parsed.month:02d}"

    def normalize_skill(self, skill: str) -> str | None:
        key = self._skill_key(skill)
        if not key:
            return None
        return self.skill_dictionary.get(key, skill.strip())

    def split_location(self, location_text: str | None) -> tuple[str | None, str | None, str | None]:
        if not location_text:
            return None, None, None
        parts = [part.strip() for part in location_text.split(",") if part.strip()]
        if not parts:
            return None, None, None
        country = self.normalize_country(parts[-1])
        city = parts[0] if parts else None
        region = parts[1] if len(parts) > 2 else None
        if len(parts) == 2 and country is None:
            region = parts[1]
        return city, region, country

    def _skill_key(self, skill: str) -> str:
        return re.sub(r"\s+", " ", skill.strip().lower())
