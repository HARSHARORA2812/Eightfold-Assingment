"""Runtime projection layer for custom output schemas."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

from candidate_transformer.models import Candidate, ProjectionConfig


MISSING = object()


class ProjectionError(ValueError):
    pass


class CandidateProjector:
    def project(self, candidate: Candidate, config: ProjectionConfig | None = None) -> dict[str, Any]:
        data = candidate.model_dump(mode="json")
        if config is None or config.fields is None:
            result = data
        else:
            result = {}
            for field in config.fields:
                value = self._resolve_path(data, field.source_path)
                if value is MISSING:
                    if config.on_missing == "error" or field.required:
                        raise ProjectionError(f"Missing required projection path: {field.source_path}")
                    if config.on_missing == "omit":
                        continue
                    value = None
                result[field.path] = value

        if config and not config.include_provenance:
            result.pop("provenance", None)
        if config and not config.include_confidence:
            self._strip_confidence(result)
        return result

    def _resolve_path(self, data: Any, path: str) -> Any:
        current = data
        for token in self._tokens(path):
            if isinstance(token, int):
                if not isinstance(current, list) or token >= len(current):
                    return MISSING
                current = current[token]
            elif token == "[]":
                if not isinstance(current, list):
                    return MISSING
                remainder = path.split("[].", 1)[1] if "[]." in path else ""
                return [self._resolve_path(item, remainder) if remainder else item for item in current]
            else:
                if not isinstance(current, dict) or token not in current:
                    return MISSING
                current = current[token]
        return current

    def _tokens(self, path: str) -> list[str | int]:
        tokens: list[str | int] = []
        for part in path.split("."):
            match = re.fullmatch(r"([A-Za-z_][\w]*)(?:\[(\d*)\])?", part)
            if not match:
                tokens.append(part)
                continue
            tokens.append(match.group(1))
            if match.group(2) == "":
                tokens.append("[]")
            elif match.group(2) is not None:
                tokens.append(int(match.group(2)))
        return tokens

    def _strip_confidence(self, data: Any) -> None:
        if isinstance(data, dict):
            data.pop("overall_confidence", None)
            data.pop("confidence", None)
            for value in data.values():
                self._strip_confidence(value)
        elif isinstance(data, list):
            for item in data:
                self._strip_confidence(item)


def validate_projection_output(projected: dict[str, Any]) -> dict[str, Any]:
    try:
        return dict(projected)
    except (TypeError, ValidationError) as exc:
        raise ProjectionError(str(exc)) from exc
