"""Parser interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from candidate_transformer.models import RawCandidateRecord


class CandidateParser(ABC):
    """All source parsers emit raw records into the same internal boundary."""

    @abstractmethod
    def parse(self, path: Path) -> list[RawCandidateRecord]:
        raise NotImplementedError
