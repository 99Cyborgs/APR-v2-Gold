from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, validate

from apr_core.goldset import run_goldset_manifest
from apr_core.packs import inspect_packs
from apr_core.pipeline import run_audit
from apr_core.policy import load_audit_input_schema, load_canonical_record_schema, load_contract_manifest, load_policy_layer
from apr_core.render import render_markdown_report
from apr_core.utils import git_output, read_json, repo_root, write_json, write_text


def cmd_doctor(_: argparse.Namespace) -> int:
    root = repo_root()
    manifest = load_contract_manifest()
    policy = load_policy_layer()
    Draft202012Validator.check_schema(load_audit_input_schema())
    Draft202012Validator.check_schema(load_canonical_record_schema())

    required_paths = [
        root / "contracts" / "active" / "manifest.yaml",
        root / "contracts" / "active" / "audit_input.schema.json",
        root / "contracts" / "active" / "canonical_audit_record.schema.json",
        root / "contracts" / "active" / "policy_layer.yaml",
        root / "docs" / "ARCHITECTURE.md",
        root / "docs" / "PACK_INTERFACE.md",
        root / "docs" / "CANONICAL_AUDIT_RECORD.md",
        root / "benchmarks" / "goldset" / "manifest.yaml",
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
    summary = run_goldset_manifest(args.manifest, extra_pack_paths=args.pack_path or [])
    if args.output:
        write_json(args.output, summary)
    else:
        print(json.dumps(summary, indent=2))
    return 0 if summary["failed"] == 0 else 1


def cmd_packs(args: argparse.Namespace) -> int:
    report = inspect_packs(args.pack_path)
    print(json.dumps(report, indent=2))
    return 0 if not report["pack_load_failures"] else 1


def build_parser() -> argparse.ArgumentParser:
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
