from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, validate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from apr_core.goldset import (  # noqa: E402
    load_goldset_ledger_entry_schema,
    load_goldset_manifest,
    load_goldset_manifest_schema,
    load_goldset_summary_schema,
)
from apr_core.utils import read_json  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate APR v2 goldset manifest, summary, or ledger artifacts.")
    parser.add_argument(
        "--manifest",
        default=str(ROOT / "benchmarks" / "goldset_dev" / "manifest.yaml"),
        help="Path to the goldset manifest YAML.",
    )
    parser.add_argument("--summary", help="Optional summary JSON path to validate against the summary schema.")
    parser.add_argument("--ledger", help="Optional JSONL ledger path to validate line by line.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    manifest_schema = load_goldset_manifest_schema()
    summary_schema = load_goldset_summary_schema()
    ledger_schema = load_goldset_ledger_entry_schema()
    Draft202012Validator.check_schema(manifest_schema)
    Draft202012Validator.check_schema(summary_schema)
    Draft202012Validator.check_schema(ledger_schema)
    validated_manifests = {
        str(ROOT / "benchmarks" / "goldset_dev" / "manifest.yaml"),
        str(ROOT / "benchmarks" / "goldset_holdout" / "manifest.yaml"),
        str(Path(args.manifest).resolve()),
    }
    for manifest_path in sorted(validated_manifests):
        load_goldset_manifest(manifest_path)

    if args.summary:
        validate(instance=read_json(args.summary), schema=summary_schema)

    if args.ledger:
        ledger_path = Path(args.ledger)
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            validate(instance=json.loads(line), schema=ledger_schema)

    print("goldset validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
