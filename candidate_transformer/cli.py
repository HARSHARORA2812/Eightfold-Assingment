"""Command-line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from candidate_transformer.normalizers import Normalizer
from candidate_transformer.pipeline import CandidatePipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-source candidate data transformer")
    parser.add_argument("--csv", type=Path, help="Recruiter CSV input")
    parser.add_argument("--resume", type=Path, help="Resume PDF input")
    parser.add_argument("--config", type=Path, help="Projection config JSON")
    parser.add_argument("--skills", type=Path, default=Path("candidate_transformer/configs/skills.json"))
    parser.add_argument("--output", type=Path, help="Output JSON file")
    parser.add_argument("--default-region", default="US", help="Default phone parsing region")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    normalizer = Normalizer.from_skill_file(args.skills, default_region=args.default_region)
    result = CandidatePipeline(normalizer).run(args.csv, args.resume, args.config)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0
