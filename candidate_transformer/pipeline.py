"""High-level orchestration for parse -> normalize -> merge -> project."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from candidate_transformer.merge import CandidateMerger
from candidate_transformer.models import Candidate, ProjectionConfig
from candidate_transformer.normalizers import Normalizer
from candidate_transformer.parsers.csv_parser import RecruiterCsvParser
from candidate_transformer.parsers.resume_pdf_parser import ResumePdfParser
from candidate_transformer.projection import CandidateProjector, ProjectionError


class CandidatePipeline:
    def __init__(self, normalizer: Normalizer | None = None) -> None:
        self.normalizer = normalizer or Normalizer()
        self.csv_parser = RecruiterCsvParser()
        self.resume_parser = ResumePdfParser(known_skills=list(self.normalizer.skill_dictionary.keys()))
        self.merger = CandidateMerger(self.normalizer)
        self.projector = CandidateProjector()

    def run(
        self,
        csv_path: Path | None = None,
        resume_path: Path | None = None,
        config_path: Path | None = None,
    ) -> dict[str, Any]:
        records = []
        if csv_path:
            records.extend(self.csv_parser.parse(csv_path))
        if resume_path:
            records.extend(self.resume_parser.parse(resume_path))

        candidate = self.merger.merge(records)
        candidate = Candidate.model_validate(candidate.model_dump())
        config = self._load_projection_config(config_path)
        try:
            return self.projector.project(candidate, config)
        except ProjectionError as exc:
            return {"error": str(exc), "candidate": candidate.model_dump(mode="json")}

    def _load_projection_config(self, config_path: Path | None) -> ProjectionConfig | None:
        if config_path is None:
            return None
        try:
            return ProjectionConfig.model_validate(json.loads(config_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, ValueError):
            return None
