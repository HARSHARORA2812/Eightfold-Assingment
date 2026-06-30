from pathlib import Path

from candidate_transformer.pipeline import CandidatePipeline


def test_missing_files_do_not_crash(tmp_path: Path):
    result = CandidatePipeline().run(tmp_path / "missing.csv", tmp_path / "missing.pdf", None)

    assert "candidate_id" in result
    assert result["emails"] == []


def test_invalid_csv_does_not_crash(tmp_path: Path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_bytes(b"\xff\xfe\x00")

    result = CandidatePipeline().run(bad_csv, None, None)

    assert "candidate_id" in result
