from candidate_transformer.merge import CandidateMerger
from candidate_transformer.models import RawCandidateRecord, SourceType
from candidate_transformer.normalizers import Normalizer


def test_merge_prefers_resume_descriptive_fields_and_deduplicates_contacts():
    records = [
        RawCandidateRecord(
            source=SourceType.CSV,
            source_id="csv-1",
            full_name="Ana Rao",
            emails=["ANA@example.com"],
            phones=["415-555-0134"],
            headline="Data Engineer",
            skills=["py"],
        ),
        RawCandidateRecord(
            source=SourceType.RESUME,
            source_id="resume",
            full_name="Ananya Rao",
            emails=["ana@example.com"],
            phones=["+1 415 555 0134"],
            headline="Senior Data Engineer",
            skills=["Python", "SQL"],
        ),
    ]

    candidate = CandidateMerger(Normalizer(default_region="US")).merge(records)

    assert candidate.full_name == "Ananya Rao"
    assert candidate.headline == "Senior Data Engineer"
    assert candidate.emails == ["ana@example.com"]
    assert candidate.phones == ["+14155550134"]
    assert {skill.name for skill in candidate.skills} == {"Python", "SQL"}
    assert any(item.field == "full_name" for item in candidate.provenance)
