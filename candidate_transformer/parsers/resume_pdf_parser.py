"""Resume PDF parser using pdfplumber plus conservative regex heuristics."""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from candidate_transformer.models import Education, Experience, RawCandidateRecord, SourceType


class ResumePdfParser:
    EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
    URL_RE = re.compile(r"https?://[^\s,]+|(?:linkedin\.com|github\.com)/[^\s,]+", re.I)
    YEARS_RE = re.compile(r"(\d+(?:\.\d+)?)\+?\s+years?", re.I)

    def __init__(self, known_skills: list[str] | None = None) -> None:
        self.known_skills = known_skills or []

    def parse(self, path: Path) -> list[RawCandidateRecord]:
        if not path.exists():
            return []
        try:
            text = self._extract_text(path)
        except (OSError, ValueError):
            return []
        if not text.strip():
            return [
                RawCandidateRecord(
                    source=SourceType.RESUME,
                    source_id=path.stem,
                    extraction_warnings=["empty pdf"],
                )
            ]

        links = self._extract_links(text)
        return [
            RawCandidateRecord(
                source=SourceType.RESUME,
                source_id=path.stem,
                full_name=self._extract_name(text),
                emails=self.EMAIL_RE.findall(text),
                phones=self.PHONE_RE.findall(text),
                location_text=self._extract_location(text),
                links=links,
                headline=self._extract_headline(text),
                years_experience=self._extract_years(text),
                skills=self._extract_skills(text),
                experience=self._extract_experience(text),
                education=self._extract_education(text),
            )
        ]

    def _extract_text(self, path: Path) -> str:
        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)

    def _extract_name(self, text: str) -> str | None:
        for line in self._clean_lines(text)[:5]:
            if self.EMAIL_RE.search(line) or self.PHONE_RE.search(line) or "linkedin" in line.lower():
                continue
            if 2 <= len(line.split()) <= 5 and not any(char.isdigit() for char in line):
                return line
        return None

    def _extract_headline(self, text: str) -> str | None:
        lines = self._clean_lines(text)
        for index, line in enumerate(lines[:8]):
            if self._extract_name(text) == line:
                continue
            if line.lower().startswith(("location:", "based in")):
                continue
            if "|" in line:
                for part in [part.strip() for part in line.split("|")]:
                    if part and not self.EMAIL_RE.search(part) and not self.PHONE_RE.search(part) and not self.URL_RE.search(part):
                        return part
            if self.URL_RE.search(line):
                continue
            if not self.EMAIL_RE.search(line) and not self.PHONE_RE.search(line) and 3 <= len(line) <= 120:
                return line
        return None

    def _extract_location(self, text: str) -> str | None:
        match = re.search(r"(?:Location|Based in)\s*:\s*(.+)", text, re.I)
        return match.group(1).strip() if match else None

    def _extract_years(self, text: str) -> float | None:
        match = self.YEARS_RE.search(text)
        return float(match.group(1)) if match else None

    def _extract_links(self, text: str) -> dict[str, str | list[str] | None]:
        links = {"linkedin": None, "github": None, "portfolio": None, "other": []}
        for url in self.URL_RE.findall(text):
            normalized = url if url.startswith("http") else f"https://{url}"
            lower = normalized.lower()
            if "linkedin.com" in lower and not links["linkedin"]:
                links["linkedin"] = normalized
            elif "github.com" in lower and not links["github"]:
                links["github"] = normalized
            elif not links["portfolio"]:
                links["portfolio"] = normalized
            else:
                links["other"].append(normalized)
        return links

    def _extract_skills(self, text: str) -> list[str]:
        found: set[str] = set()
        skill_section = self._section(text, "skills")
        haystack = skill_section or text
        for skill in self.known_skills:
            if re.search(rf"\b{re.escape(skill)}\b", haystack, re.I):
                found.add(skill)
        if skill_section:
            for item in re.split(r"[,;|•\n]", skill_section):
                item = item.strip()
                if 1 < len(item) <= 40 and not re.search(r"\d", item):
                    found.add(item)
        return sorted(found, key=str.lower)

    def _extract_experience(self, text: str) -> list[Experience]:
        section = self._section(text, "experience")
        if not section:
            return []
        experiences: list[Experience] = []
        for line in self._clean_lines(section):
            if " at " in line.lower() or " - " in line:
                title, company = self._split_title_company(line)
                experiences.append(Experience(title=title, company=company, summary=line, source="resume", confidence=0.65))
                if len(experiences) >= 5:
                    break
        return experiences

    def _extract_education(self, text: str) -> list[Education]:
        section = self._section(text, "education")
        if not section:
            return []
        educations = []
        degree_re = re.compile(r"(B\.?S\.?|M\.?S\.?|Bachelor|Master|PhD|MBA)[^,\n]*", re.I)
        year_re = re.compile(r"\b(19|20)\d{2}\b")
        for line in self._clean_lines(section):
            degree = degree_re.search(line)
            year = year_re.search(line)
            if degree or year:
                educations.append(
                    Education(
                        institution=line,
                        degree=degree.group(0) if degree else None,
                        end_year=int(year.group(0)) if year else None,
                        source="resume",
                        confidence=0.65,
                    )
                )
        return educations[:3]

    def _section(self, text: str, title: str) -> str | None:
        pattern = re.compile(rf"(?is)\b{re.escape(title)}\b\s*\n(.*?)(?=\n[A-Z][A-Z /&-]{{2,}}\n|\Z)")
        match = pattern.search(text)
        return match.group(1).strip() if match else None

    def _split_title_company(self, line: str) -> tuple[str | None, str | None]:
        if " at " in line.lower():
            parts = re.split(r"\s+at\s+", line, maxsplit=1, flags=re.I)
            return parts[0].strip(" -"), parts[1].strip(" -")
        parts = line.split(" - ", 1)
        return (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else (line, None)

    def _clean_lines(self, text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]
