"""Confidence scoring policies."""

from __future__ import annotations

from candidate_transformer.models import Confidence, CONFIDENCE_VALUES


def score_from_sources(sources: set[str], malformed: bool = False) -> float:
    if malformed:
        return CONFIDENCE_VALUES[Confidence.LOW]
    if len(sources) >= 2:
        return CONFIDENCE_VALUES[Confidence.HIGH]
    if len(sources) == 1:
        return CONFIDENCE_VALUES[Confidence.MEDIUM]
    return 0.0


def overall_confidence(field_scores: list[float]) -> float:
    non_zero = [score for score in field_scores if score > 0]
    if not non_zero:
        return 0.0
    return round(sum(non_zero) / len(non_zero), 3)
