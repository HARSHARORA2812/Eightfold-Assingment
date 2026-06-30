"""Merge raw source records into one canonical candidate."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from candidate_transformer.confidence import overall_confidence, score_from_sources
from candidate_transformer.models import Candidate, Experience, Location, Provenance, RawCandidateRecord, Skill, SourceType
from candidate_transformer.normalizers import Normalizer


class CandidateMerger:
    """Deterministic conflict resolution for candidate records."""

    SOURCE_PRIORITY = {SourceType.RESUME: 2, SourceType.CSV: 1}

    def __init__(self, normalizer: Normalizer) -> None:
        self.normalizer = normalizer

    def merge(self, records: list[RawCandidateRecord]) -> Candidate:
        normalized_records = sorted(records, key=lambda record: (self.SOURCE_PRIORITY.get(record.source, 0), record.source_id))
        provenance: list[Provenance] = []
        field_scores: list[float] = []

        emails, email_sources = self._merge_unique("emails", normalized_records, provenance, self.normalizer.normalize_email)
        phones, phone_sources = self._merge_phones(normalized_records, provenance)

        full_name, full_name_sources = self._choose_scalar("full_name", normalized_records, provenance)
        headline, headline_sources = self._choose_scalar("headline", normalized_records, provenance)
        years_experience, years_sources = self._choose_scalar("years_experience", normalized_records, provenance)
        location = self._merge_location(normalized_records, provenance)
        links = self._merge_links(normalized_records, provenance)
        skills = self._merge_skills(normalized_records, provenance)
        experience = self._merge_experience(normalized_records, provenance)
        education = self._merge_education(normalized_records, provenance)

        field_scores.extend(
            [
                score_from_sources(full_name_sources),
                score_from_sources(email_sources),
                score_from_sources(phone_sources),
                score_from_sources(headline_sources),
                score_from_sources(years_sources),
            ]
        )
        field_scores.extend(skill.confidence for skill in skills)
        field_scores.extend(item.confidence for item in experience)
        field_scores.extend(item.confidence for item in education)

        return Candidate(
            candidate_id=self._candidate_id(full_name, emails, phones),
            full_name=full_name,
            emails=emails,
            phones=phones,
            location=location,
            links=links,
            headline=headline,
            years_experience=years_experience,
            skills=skills,
            experience=experience,
            education=education,
            provenance=provenance,
            overall_confidence=overall_confidence(field_scores),
        )

    def _choose_scalar(
        self, field_name: str, records: list[RawCandidateRecord], provenance: list[Provenance]
    ) -> tuple[object | None, set[str]]:
        values_by_source: dict[str, object] = {}
        for record in records:
            value = getattr(record, field_name)
            if value is not None and value != "":
                values_by_source[record.source.value] = value
                provenance.append(
                    Provenance(
                        field=field_name,
                        source=record.source.value,
                        method="direct extraction",
                        confidence=score_from_sources({record.source.value}),
                        value=value,
                    )
                )
        if not values_by_source:
            return None, set()
        ordered = sorted(values_by_source.items(), key=lambda item: self.SOURCE_PRIORITY[SourceType(item[0])], reverse=True)
        winning_value = ordered[0][1]
        agreeing_sources = {source for source, value in values_by_source.items() if value == winning_value}
        return winning_value, agreeing_sources

    def _merge_unique(self, field_name, records, provenance, normalize):
        values: list[str] = []
        sources: set[str] = set()
        seen: set[str] = set()
        for record in records:
            for raw_value in getattr(record, field_name):
                value = normalize(raw_value)
                if value is None:
                    provenance.append(
                        Provenance(field=field_name, source=record.source.value, method="malformed extraction dropped", confidence=0.35, value=raw_value)
                    )
                    continue
                if value not in seen:
                    values.append(value)
                    seen.add(value)
                sources.add(record.source.value)
                provenance.append(
                    Provenance(field=field_name, source=record.source.value, method="normalized and deduplicated", confidence=0.65, value=value)
                )
        return values, sources

    def _merge_phones(self, records, provenance):
        values: list[str] = []
        sources: set[str] = set()
        seen: set[str] = set()
        for record in records:
            for raw_phone in record.phones:
                result = self.normalizer.normalize_phone(raw_phone)
                confidence = 0.35 if result.warning else 0.65
                provenance.append(
                    Provenance(field="phones", source=record.source.value, method=result.warning or "E.164 normalization", confidence=confidence, value=result.value or raw_phone)
                )
                if result.value and result.value not in seen:
                    values.append(result.value)
                    seen.add(result.value)
                    sources.add(record.source.value)
        return values, sources

    def _merge_location(self, records, provenance) -> Location:
        for record in sorted(records, key=lambda item: self.SOURCE_PRIORITY[item.source], reverse=True):
            city, region, country = self.normalizer.split_location(record.location_text)
            if city or region or country:
                provenance.append(
                    Provenance(field="location", source=record.source.value, method="split city/region/country and ISO country normalization", confidence=0.65, value=record.location_text)
                )
                return Location(city=city, region=region, country=country)
        return Location()

    def _merge_links(self, records, provenance):
        merged = {"linkedin": None, "github": None, "portfolio": None, "other": []}
        for record in sorted(records, key=lambda item: self.SOURCE_PRIORITY[item.source], reverse=True):
            for key in ("linkedin", "github", "portfolio"):
                value = getattr(record.links, key)
                if value and not merged[key]:
                    merged[key] = value
                    provenance.append(Provenance(field=f"links.{key}", source=record.source.value, method="preferred non-empty link", confidence=0.65, value=value))
            for value in record.links.other:
                if value not in merged["other"]:
                    merged["other"].append(value)
                    provenance.append(Provenance(field="links.other", source=record.source.value, method="deduplicated link", confidence=0.65, value=value))
        return merged

    def _merge_skills(self, records, provenance) -> list[Skill]:
        sources_by_skill: dict[str, set[str]] = defaultdict(set)
        for record in records:
            for raw_skill in record.skills:
                skill = self.normalizer.normalize_skill(raw_skill)
                if not skill:
                    continue
                if record.source.value in sources_by_skill[skill]:
                    continue
                sources_by_skill[skill].add(record.source.value)
                provenance.append(Provenance(field="skills", source=record.source.value, method="canonical skill normalization", confidence=0.65, value=skill))
        return [
            Skill(name=name, confidence=score_from_sources(sources), sources=sorted(sources))
            for name, sources in sorted(sources_by_skill.items(), key=lambda item: item[0].lower())
        ]

    def _merge_experience(self, records, provenance) -> list[Experience]:
        seen: set[tuple[str | None, str | None]] = set()
        merged: list[Experience] = []
        for record in sorted(records, key=lambda item: self.SOURCE_PRIORITY[item.source], reverse=True):
            for item in record.experience:
                key = ((item.company or "").lower(), (item.title or "").lower())
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
                provenance.append(Provenance(field="experience", source=record.source.value, method="latest/preferred source order", confidence=item.confidence, value=item.model_dump()))
        return merged

    def _merge_education(self, records, provenance) -> list:
        seen: set[tuple[str | None, str | None]] = set()
        merged = []
        for record in sorted(records, key=lambda item: self.SOURCE_PRIORITY[item.source], reverse=True):
            for item in record.education:
                key = ((item.institution or "").lower(), (item.degree or "").lower())
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
                provenance.append(Provenance(field="education", source=record.source.value, method="deduplicated education", confidence=item.confidence, value=item.model_dump()))
        return merged

    def _candidate_id(self, full_name: object | None, emails: list[str], phones: list[str]) -> str:
        stable_key = "|".join([str(full_name or ""), ",".join(sorted(emails)), ",".join(sorted(phones))])
        return hashlib.sha256(stable_key.encode("utf-8")).hexdigest()[:16]
