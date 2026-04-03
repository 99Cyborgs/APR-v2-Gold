from __future__ import annotations

"""CLI entrypoints for contract-bound audits and governed benchmark runs.

The goldset flags below do more than alter output formatting: several of them
change which benchmark surfaces are exposed, masked, or compared, while still
preserving APR's rule that benchmark diagnostics must not silently rewrite live
decision policy.
"""

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, validate

from apr_core.goldset import (
    default_calibration_ledger_path,
    default_goldset_governance_config,
    default_holdout_calibration_ledger_path,
    load_goldset_ledger_entry_schema,
    load_goldset_manifest,
    load_goldset_manifest_schema,
    load_goldset_summary_schema,
    run_goldset_manifest,
)
from apr_core.packs import inspect_packs
from apr_core.pipeline import run_audit
from apr_core.policy import load_audit_input_schema, load_canonical_record_schema, load_contract_manifest, load_policy_layer
from apr_core.render import render_markdown_report
from apr_core.utils import git_output, read_json, repo_root, write_json, write_text


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return parsed


def cmd_doctor(_: argparse.Namespace) -> int:
    root = repo_root()
    manifest = load_contract_manifest()
    policy = load_policy_layer()
    Draft202012Validator.check_schema(load_audit_input_schema())
    Draft202012Validator.check_schema(load_canonical_record_schema())
    Draft202012Validator.check_schema(load_goldset_manifest_schema())
    Draft202012Validator.check_schema(load_goldset_summary_schema())
    Draft202012Validator.check_schema(load_goldset_ledger_entry_schema())
    load_goldset_manifest()

    required_paths = [
        root / "contracts" / "active" / "manifest.yaml",
        root / "contracts" / "active" / "audit_input.schema.json",
        root / "contracts" / "active" / "canonical_audit_record.schema.json",
        root / "contracts" / "active" / "policy_layer.yaml",
        root / "docs" / "ARCHITECTURE.md",
        root / "docs" / "BENCHMARK_POLICY.md",
        root / "docs" / "PACK_INTERFACE.md",
        root / "docs" / "CANONICAL_AUDIT_RECORD.md",
        root / "docs" / "GOLDSET_CASE_SCHEMA.md",
        root / "docs" / "SPEC_IMPLEMENTATION_MATRIX.md",
        root / "benchmarks" / "goldset" / "manifest.yaml",
        root / "benchmarks" / "goldset" / "schemas" / "manifest.schema.json",
        root / "benchmarks" / "goldset" / "schemas" / "summary.schema.json",
        root / "benchmarks" / "goldset" / "schemas" / "ledger_entry.schema.json",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        print(json.dumps({"status": "error", "missing_paths": missing}, indent=2))
        return 1

    sample_payload = read_json(root / "fixtures" / "inputs" / "reviewable_sound_paper.json")
    sample_record = run_audit(sample_payload)
    validate(instance=sample_record, schema=load_canonical_record_schema())

    git_code, git_msg = git_output(["rev-parse", "--is-inside-work-tree"], cwd=root)
    git_status = "unavailable"
    if git_code == 0:
        status_code, status_output = git_output(["status", "--porcelain"], cwd=root)
        git_status = "clean" if status_code == 0 and not status_output else "dirty"
        if git_status == "dirty":
            print(json.dumps({"status": "error", "git_status": git_status}, indent=2))
            return 1
    else:
        git_msg = "not a git repository"

    print(
        json.dumps(
            {
                "status": "ok",
                "repo_root": str(root),
                "contract_version": manifest["contract"]["version"],
                "policy_layer_version": policy["policy_layer"]["version"],
                "git_status": git_status,
                "git_detail": git_msg,
            },
            indent=2,
        )
    )
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    payload = read_json(args.input)
    record = run_audit(payload, pack_paths=args.pack_path or [])
    if args.output:
        write_json(args.output, record)
    else:
        print(json.dumps(record, indent=2))
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    record = read_json(args.input)
    validate(instance=record, schema=load_canonical_record_schema())
    rendered = render_markdown_report(record)
    if args.output:
        write_text(args.output, rendered)
    else:
        print(rendered, end="")
    return 0


def cmd_goldset(args: argparse.Namespace) -> int:
    if args.no_ledger:
        ledger_path = None
    elif args.ledger_path:
        ledger_path = args.ledger_path
    elif args.holdout_eval:
        ledger_path = str(default_holdout_calibration_ledger_path())
    else:
        ledger_path = str(default_calibration_ledger_path())
    summary = run_goldset_manifest(
        args.manifest,
        extra_pack_paths=args.pack_path or [],
        ledger_path=ledger_path,
        notes=args.notes,
        operator=args.operator,
        holdout_eval=args.holdout_eval,
        ledger_baseline_window=args.baseline_window,
        regression_threshold=args.regression_threshold,
        fatal_weight_scale=args.fatal_weight_scale,
        loss_quantization=args.loss_quantization if args.loss_quantization else None,
        enable_editorial_weight=args.enable_editorial_weight if args.enable_editorial_weight else None,
        separate_planes=args.separate_planes if args.separate_planes else None,
        export_calibration_extended=args.export_calibration_extended if args.export_calibration_extended else None,
        holdout_blindness_level=args.holdout_blindness_level,
        drift_intervention=args.drift_intervention == "on",
        drift_counterfactuals=args.drift_counterfactuals if args.drift_counterfactuals else None,
    )
    if args.output:
        write_json(args.output, summary)
    else:
        print(json.dumps(summary, indent=2))
    return 0 if summary["gates"]["status"] == "pass" else 1


def cmd_packs(args: argparse.Namespace) -> int:
    report = inspect_packs(args.pack_path)
    print(json.dumps(report, indent=2))
    return 0 if not report["pack_load_failures"] else 1


def build_parser() -> argparse.ArgumentParser:
    governance_defaults = default_goldset_governance_config()
    parser = argparse.ArgumentParser(prog="apr", description="APR v2 deterministic manuscript-audit engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Validate repo, contracts, and local runtime wiring.")
    doctor.set_defaults(func=cmd_doctor)

    audit = subparsers.add_parser("audit", help="Audit a manuscript package and emit canonical JSON.")
    audit.add_argument("input", help="Path to the normalized manuscript package JSON.")
    audit.add_argument("--output", help="Optional output path for canonical JSON.")
    audit.add_argument("--pack-path", action="append", default=[], help="Explicit external pack path. Repeatable.")
    audit.set_defaults(func=cmd_audit)

    render = subparsers.add_parser("render", help="Render markdown from a canonical record only.")
    render.add_argument("input", help="Path to a canonical audit record JSON file.")
    render.add_argument("--output", help="Optional output path for rendered markdown.")
    render.set_defaults(func=cmd_render)

    goldset = subparsers.add_parser("goldset", help="Run the benchmark harness.")
    goldset.add_argument(
        "--manifest",
        default=str(repo_root() / "benchmarks" / "goldset" / "manifest.yaml"),
        help="Path to the gold-set manifest.",
    )
    goldset.add_argument("--output", help="Optional output path for the summary JSON.")
    goldset.add_argument("--pack-path", action="append", default=[], help="Extra pack path to apply to every case.")
    # These flags alter benchmark governance or disclosure surfaces; they are
    # not cosmetic toggles for the same public artifact.
    goldset.add_argument(
        "--holdout-eval",
        action="store_true",
        help="Run blind holdout evaluation only. Holdout expectations are redacted from output surfaces.",
    )
    goldset.add_argument(
        "--ledger-path",
        help="Optional JSONL calibration ledger path. Defaults to the development ledger, or the holdout ledger when --holdout-eval is set.",
    )
    goldset.add_argument(
        "--baseline-window",
        type=_non_negative_int,
        default=governance_defaults["baseline_window"],
        help="Rolling ledger window used for comparable-run baselines.",
    )
    goldset.add_argument(
        "--regression-threshold",
        type=_non_negative_float,
        default=governance_defaults["regression_threshold"],
        help="Base drift threshold for system-level regression diagnostics.",
    )
    goldset.add_argument(
        "--fatal-weight-scale",
        type=_positive_float,
        default=governance_defaults["fatal_weight_scale"],
        help="Multiplier applied to fatal decision-algebra error weights.",
    )
    goldset.add_argument(
        "--loss-quantization",
        action="store_true",
        help="Quantize reported loss surfaces to two decimal places without changing gate logic.",
    )
    goldset.add_argument(
        "--enable-editorial-weight",
        action="store_true",
        help="Apply the non-gating editorial penalty weight to ranking and calibration outputs.",
    )
    goldset.add_argument(
        "--separate-planes",
        action="store_true",
        help="Emit runner metadata for the scientific/editorial two-plane evaluation model.",
    )
    goldset.add_argument(
        "--drift-counterfactuals",
        action="store_true",
        help="Emit per-case counterfactual drift attributions in additive output fields.",
    )
    goldset.add_argument(
        "--export-calibration-extended",
        action="store_true",
        help="Include scientific/editorial score vectors and boundary metadata in calibration export records.",
    )
    goldset.add_argument(
        "--holdout-blindness-level",
        choices=["strict", "moderate", "off"],
        default=governance_defaults["holdout_blindness"]["level"],
        help="Controls recommendation/error masking strength for public holdout summaries.",
    )
    goldset.add_argument(
        "--drift-intervention",
        choices=["on", "off"],
        default="on" if governance_defaults["drift_intervention"]["enabled"] else "off",
        help="Enable or disable lightweight intervention deltas in drift attribution.",
    )
    goldset.add_argument("--no-ledger", action="store_true", help="Disable calibration-ledger comparison and append.")
    goldset.add_argument("--notes", default="", help="Optional free-text note stored with the calibration-ledger entry.")
    goldset.add_argument("--operator", help="Optional operator identifier stored with the calibration-ledger entry.")
    goldset.set_defaults(func=cmd_goldset)

    packs = subparsers.add_parser("packs", help="Inspect explicit or bundled advisory packs.")
    packs.add_argument("--pack-path", action="append", default=None, help="Explicit pack path. Repeatable.")
    packs.set_defaults(func=cmd_packs)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
