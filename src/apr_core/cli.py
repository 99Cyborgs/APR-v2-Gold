from __future__ import annotations

"""CLI entrypoints for contract-bound audits and governed benchmark runs.

The goldset flags below do more than alter output formatting: several of them
change which benchmark surfaces are exposed, masked, or compared, while still
preserving APR's rule that benchmark diagnostics must not silently rewrite live
decision policy.
"""

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, validate

from apr_core.goldset import (
    append_goldset_ledger_entry,
    build_goldset_ledger_entry,
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
from apr_core.utils import git_output, read_json, repo_root, stable_json_dumps, write_json, write_text, write_text_bundle


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


def _default_dev_manifest() -> str:
    return str(repo_root() / "benchmarks" / "goldset_dev" / "manifest.yaml")


def _default_holdout_manifest() -> str:
    return str(repo_root() / "benchmarks" / "goldset_holdout" / "manifest.yaml")


def _apply_profile_override(payload: dict[str, object], profile: str | None) -> dict[str, object]:
    if not profile:
        return payload
    overridden = dict(payload)
    overridden["outlet_profile_hint"] = profile
    return overridden


def _doctor_report() -> tuple[dict[str, object], int]:
    root = repo_root()
    manifest = load_contract_manifest()
    policy = load_policy_layer()
    Draft202012Validator.check_schema(load_audit_input_schema())
    Draft202012Validator.check_schema(load_canonical_record_schema())
    Draft202012Validator.check_schema(load_goldset_manifest_schema())
    Draft202012Validator.check_schema(load_goldset_summary_schema())
    Draft202012Validator.check_schema(load_goldset_ledger_entry_schema())
    load_goldset_manifest(_default_dev_manifest())
    load_goldset_manifest(_default_holdout_manifest())

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
        root / "benchmarks" / "goldset_dev" / "manifest.yaml",
        root / "benchmarks" / "goldset_holdout" / "manifest.yaml",
        root / "benchmarks" / "goldset" / "schemas" / "manifest.schema.json",
        root / "benchmarks" / "goldset" / "schemas" / "summary.schema.json",
        root / "benchmarks" / "goldset" / "schemas" / "ledger_entry.schema.json",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        return {"status": "error", "missing_paths": missing}, 1

    sample_payload = read_json(root / "fixtures" / "inputs" / "reviewable_sound_paper.json")
    sample_record = run_audit(sample_payload)
    validate(instance=sample_record, schema=load_canonical_record_schema())

    git_code, git_msg = git_output(["rev-parse", "--is-inside-work-tree"], cwd=root)
    git_status = "unavailable"
    if git_code == 0:
        status_code, status_output = git_output(["status", "--porcelain"], cwd=root)
        git_status = "clean" if status_code == 0 and not status_output else "dirty"
    else:
        git_msg = "not a git repository"

    return (
        {
            "status": "ok",
            "repo_root": str(root),
            "contract_version": manifest["contract"]["version"],
            "policy_layer_version": policy["policy_layer"]["version"],
            "git_status": git_status,
            "git_detail": git_msg,
        },
        0,
    )


def cmd_doctor(_: argparse.Namespace) -> int:
    payload, exit_code = _doctor_report()
    print(json.dumps(payload, indent=2))
    return exit_code


def cmd_readiness(_: argparse.Namespace) -> int:
    payload, exit_code = _doctor_report()
    if exit_code != 0:
        print(json.dumps(payload, indent=2))
        return exit_code
    if payload["git_status"] != "clean":
        print(
            json.dumps(
                {
                    **payload,
                    "status": "error",
                    "reason": "release_readiness_requires_clean_worktree",
                },
                indent=2,
            )
        )
        return 1
    print(json.dumps(payload, indent=2))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    payload = _apply_profile_override(read_json(args.input), args.profile)
    record = run_audit(payload, pack_paths=args.pack_path or [])
    if args.output:
        write_json(args.output, record)
    else:
        print(json.dumps(record, indent=2))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    return cmd_audit(args)


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
    holdout_requested = bool(getattr(args, "holdout", False) or getattr(args, "holdout_eval", False))
    manifest_path = args.manifest or (_default_holdout_manifest() if holdout_requested else _default_dev_manifest())
    if args.no_ledger:
        ledger_path = None
    elif args.ledger_path:
        ledger_path = args.ledger_path
    elif holdout_requested:
        ledger_path = str(default_holdout_calibration_ledger_path())
    else:
        ledger_path = str(default_calibration_ledger_path())
    defer_ledger_append = bool(args.output and ledger_path)
    summary = run_goldset_manifest(
        manifest_path,
        extra_pack_paths=args.pack_path or [],
        ledger_path=None if defer_ledger_append else ledger_path,
        notes=args.notes,
        operator=args.operator,
        holdout_eval=holdout_requested,
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
        leakage_guard=args.leakage_guard if args.leakage_guard else None,
        attribution_identifiability=args.attribution_identifiability if args.attribution_identifiability else None,
        invariance_trace=args.invariance_trace if args.invariance_trace else None,
        strict_surface_contract=args.strict_surface_contract if args.strict_surface_contract else None,
    )
    if args.output and defer_ledger_append:
        output_path = Path(args.output)
        governance_report_path = output_path.with_name("governance_report.json")
        write_text_bundle(
            {
                output_path: stable_json_dumps(summary) + "\n",
                governance_report_path: stable_json_dumps(summary["governance_report"]) + "\n",
            }
        )
    if defer_ledger_append:
        entry = build_goldset_ledger_entry(
            summary,
            manifest_path=manifest_path,
            notes=args.notes,
            operator=args.operator,
        )
        append_goldset_ledger_entry(ledger_path, entry)
        summary = {
            **summary,
            "calibration_ledger": {
                "path": str(Path(ledger_path).resolve()),
                "entry_appended": True,
                "baseline_window": summary["calibration_ledger"]["baseline_window"],
            },
        }
    if args.output:
        output_path = Path(args.output)
        governance_report_path = output_path.with_name("governance_report.json")
        write_text_bundle(
            {
                output_path: stable_json_dumps(summary) + "\n",
                governance_report_path: stable_json_dumps(summary["governance_report"]) + "\n",
            }
        )
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

    readiness = subparsers.add_parser(
        "readiness",
        help="Validate release readiness, including clean-worktree policy, on top of doctor checks.",
    )
    readiness.set_defaults(func=cmd_readiness)

    outlet_profiles = load_policy_layer()["policy_layer"]["outlet_profiles"]

    audit = subparsers.add_parser("audit", help="Audit a manuscript package and emit canonical JSON.")
    audit.add_argument("input", help="Path to the normalized manuscript package JSON.")
    audit.add_argument("--output", help="Optional output path for canonical JSON.")
    audit.add_argument("--pack-path", action="append", default=[], help="Explicit external pack path. Repeatable.")
    audit.add_argument("--profile", choices=outlet_profiles, help="Override the outlet profile hint for this run.")
    audit.set_defaults(func=cmd_audit)

    review = subparsers.add_parser("review", help="Alias of audit with editorial-profile override support.")
    review.add_argument("input", help="Path to the normalized manuscript package JSON.")
    review.add_argument("--output", help="Optional output path for canonical JSON.")
    review.add_argument("--pack-path", action="append", default=[], help="Explicit external pack path. Repeatable.")
    review.add_argument("--profile", choices=outlet_profiles, help="Override the outlet profile hint for this run.")
    review.set_defaults(func=cmd_review)

    render = subparsers.add_parser("render", help="Render markdown from a canonical record only.")
    render.add_argument("input", help="Path to a canonical audit record JSON file.")
    render.add_argument("--output", help="Optional output path for rendered markdown.")
    render.set_defaults(func=cmd_render)

    goldset = subparsers.add_parser("goldset", help="Run the benchmark harness.")
    goldset.add_argument(
        "--manifest",
        default=None,
        help="Optional explicit manifest path. Defaults to the dev manifest, or the holdout manifest when --holdout is set.",
    )
    goldset.add_argument("--output", help="Optional output path for the summary JSON.")
    goldset.add_argument("--pack-path", action="append", default=[], help="Extra pack path to apply to every case.")
    # These flags alter benchmark governance or disclosure surfaces; they are
    # not cosmetic toggles for the same public artifact.
    goldset.add_argument(
        "--holdout",
        action="store_true",
        help="Run holdout-only blind evaluation using the holdout manifest by default.",
    )
    goldset.add_argument(
        "--holdout-eval",
        action="store_true",
        help="Backward-compatible alias for --holdout.",
    )
    goldset.add_argument(
        "--ledger-path",
        help="Optional JSONL calibration ledger path. Defaults to the development ledger, or the holdout ledger when --holdout is set.",
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
        "--leakage-guard",
        action="store_true",
        help="Emit additive leakage hardening diagnostics without altering decision classes or loss bands.",
    )
    goldset.add_argument(
        "--attribution-identifiability",
        action="store_true",
        help="Emit additive attribution identifiability diagnostics alongside counterfactual summaries.",
    )
    goldset.add_argument(
        "--invariance-trace",
        action="store_true",
        help="Emit additive decision-trace hashes and silent-drift warnings.",
    )
    goldset.add_argument(
        "--strict-surface-contract",
        action="store_true",
        help="Validate legacy/native score namespace exclusivity inside scoring while preserving both exports.",
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


def review_entry_main() -> int:
    return main(["review", *sys.argv[1:]])


def goldset_entry_main() -> int:
    return main(["goldset", *sys.argv[1:]])


def holdout_entry_main() -> int:
    return main(["goldset", "--holdout", *sys.argv[1:]])


def doctor_entry_main() -> int:
    return main(["doctor", *sys.argv[1:]])


def readiness_entry_main() -> int:
    return main(["readiness", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
