from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import score_company, score_to_dict
from .models import CompanyInput
from .webapp import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Executive Opportunity Scorer CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    score_parser = subparsers.add_parser("score", help="Score a company input file.")
    score_parser.add_argument("input_file", help="Path to a JSON company input file.")
    score_parser.add_argument("--format", choices=("text", "json"), default="text")

    subparsers.add_parser("list-samples", help="List bundled sample files.")

    ui_parser = subparsers.add_parser("serve-ui", help="Run the schema-driven local UI.")
    ui_parser.add_argument("--host", default="127.0.0.1")
    ui_parser.add_argument("--port", type=int, default=8000)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list-samples":
        sample_dir = Path(__file__).resolve().parent.parent / "data" / "samples"
        for path in sorted(sample_dir.glob("*.json")):
            print(path.name)
        return 0

    if args.command == "serve-ui":
        run_server(args.host, args.port)
        return 0

    payload = json.loads(Path(args.input_file).read_text())
    company = CompanyInput.from_dict(payload)
    result = score_company(company)
    if args.format == "json":
        print(json.dumps(score_to_dict(result), indent=2))
    else:
        _print_text(result)
    return 0


def _print_text(result) -> None:
    print(f"Company: {result.company_name}")
    print(f"Snapshot: {result.snapshot_date}")
    print(f"Recommendation: {result.recommendation}")
    print(f"Fit score: {result.fit_score}")
    print(f"Risk score: {result.risk_score}")
    print(f"Confidence: {result.confidence}")
    print("Top positive signals:")
    for item in result.top_positive_signals or ["None"]:
        print(f"- {item}")
    print("Top risk signals:")
    for item in result.top_risk_signals or ["None"]:
        print(f"- {item}")
    print("Explanation:")
    print(result.explanation)
    print("Next steps:")
    for item in result.next_steps:
        print(f"- {item}")
    print("Sources used:")
    for source in result.sources_used:
        print(f"- {source.label}: {source.url} ({source.observed_at})")


if __name__ == "__main__":
    raise SystemExit(main())
