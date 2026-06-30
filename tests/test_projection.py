import pytest

from candidate_transformer.models import Candidate, ProjectionConfig, Skill
from candidate_transformer.projection import CandidateProjector, ProjectionError


def test_projection_maps_and_renames_fields():
    candidate = Candidate(
        candidate_id="abc",
        full_name="Ananya Rao",
        emails=["a@example.com"],
        phones=["+14155550134"],
        skills=[Skill(name="Python", confidence=0.9, sources=["csv", "resume"])],
        overall_confidence=0.8,
    )
    config = ProjectionConfig.model_validate(
        {
            "fields": [
                {"path": "name", "from": "full_name"},
                {"path": "primary_email", "from": "emails[0]"},
                {"path": "skills", "from": "skills[].name"},
            ],
            "include_confidence": False,
            "include_provenance": False,
            "on_missing": "null",
        }
    )

    projected = CandidateProjector().project(candidate, config)

    assert projected == {"name": "Ananya Rao", "primary_email": "a@example.com", "skills": ["Python"]}


def test_projection_missing_error_policy_raises():
    candidate = Candidate(candidate_id="abc")
    config = ProjectionConfig.model_validate({"fields": [{"path": "email", "from": "emails[0]"}], "on_missing": "error"})

    with pytest.raises(ProjectionError):
        CandidateProjector().project(candidate, config)
