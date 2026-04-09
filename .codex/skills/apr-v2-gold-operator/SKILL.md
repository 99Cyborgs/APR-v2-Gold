---
name: apr-v2-gold-operator
description: Operate the APR v2 Gold repository with deterministic, contract-first workflows for reconnaissance, contract inspection, schema drift review, CLI smoke runs, fixture audits, canonical-record validation, renderer checks, goldset execution, advisory-pack scaffolding, release-readiness review, and change-impact mapping. Use when Codex is working inside APR v2 Gold and must preserve one canonical audit record, the scientific-record gate before venue routing, advisory-only external packs, and renderer consumption discipline.
---

# APR v2 Gold Operator

## Intended Invocation

Use this repo-local skill inside APR v2 Gold when the task touches repo inspection, contracts, schemas, runtime behavior, renderers, fixtures, benchmarks, release checks, or external advisory packs.

Example:

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator to run a contract integrity audit and produce a touched-file impact memo with exact validation receipts.`

Read `session_bootstrap.md` first, then load only the file needed for the current task:

- `BOUNDARIES.md`
- `WORKFLOWS.md`
- `CHECKLISTS.md`
- `COMMANDS.md`
- `VALIDATION.md`
- `PROMPTS.md`
- `ARTIFACTS.md`
- `OPERATOR_QUICKSTART.md`
- `PACK_SUMMARY.md`

## Purpose

Reduce ambiguity for recurring APR maintenance without weakening repository governance. This skill is for operating the existing deterministic manuscript-audit engine, not for inventing a generic agent framework.

## Operator Doctrine

- One canonical audit record is the only semantic source for renderers and downstream evaluation.
- Renderers may transform presentation, not meaning.
- Scientific-record gating precedes venue routing.
- Contract changes require explicit blast-radius review.
- Domain logic must not silently migrate into `src/apr_core/`.
- Benchmark or fixture convenience must not mutate normative semantics.
- Release readiness requires validation receipts, not narrative confidence.

## Repo Assumptions

- Repo root is the directory containing `pyproject.toml`, `contracts/active/`, `src/apr_core/`, `benchmarks/`, and `fixtures/`.
- `pyproject.toml` exposes `apr` plus wrapper entrypoints `apr-review`, `apr-goldset`, `apr-holdout`, and `apr-doctor`.
- `Makefile` exposes `install`, `test`, `doctor`, `contract`, `goldset-validate`, `goldset`, and `release`.
- The active contract version and policy layer version are both `2.1.0` in `contracts/active/manifest.yaml` and `contracts/active/policy_layer.yaml`.
- `src/apr_core/cli.py` currently loads goldset manifests from `benchmarks/goldset_dev/manifest.yaml` and `benchmarks/goldset_holdout/manifest.yaml`.
- `benchmarks/goldset/` still contains shared benchmark docs, schemas, and ledger output, and some docs still refer to a `benchmarks/goldset/manifest.yaml` path that is not present in the current worktree. Verify manifest location before assuming it.
- `apr doctor` returns nonzero on a dirty git worktree even when runtime wiring is otherwise intact. Treat that as repo-state information, not automatic runtime failure.

## High-Sensitivity Surfaces

Treat these paths as high sensitivity and require explicit blast-radius review before edits:

- `contracts/active/`
- `contracts/active/canonical_audit_record.schema.json`
- `contracts/active/policy_layer.yaml`
- `src/apr_core/`

Additional governed surfaces:

- `src/apr_core/render/`
- `benchmarks/goldset*/`
- `fixtures/external_packs/`
- `pyproject.toml`
- `setup.py`
- `src/apr_core_bootstrap.py`

## Scope

Support:

- repo reconnaissance and architecture summaries
- contract-surface inspection
- schema drift checks
- CLI smoke execution
- fixture-based audit execution
- canonical record validation
- renderer consistency checks
- goldset execution
- external advisory-pack scaffolding
- release-readiness inspection
- regression and artifact sanity review
- change-impact mapping

## Non-Goals

- Redesign APR doctrine.
- Invent new policy semantics in the skill pack.
- Collapse contract, runtime, renderer, benchmark, or advisory-pack boundaries.
- Treat fixture output or rendered markdown as a replacement for canonical records.
- Hide uncertainty about command availability, manifest locations, or repo cleanliness.

## Never Do This

- Do not infer semantic meaning from rendered markdown when the canonical record is available.
- Do not treat packs as allowed to rewrite core recommendation semantics.
- Do not route venue logic before scientific-record assessment.
- Do not move domain-specific logic into core runtime for convenience.
- Do not claim a validation passed unless the command was actually run and the artifact was observed.
- Do not assume benchmark manifest location from README or docs alone when CLI defaults disagree.
- Do not edit unrelated dirty-worktree files to make a local command pass.

## Session Start

Follow `session_bootstrap.md` exactly on cold start. Do not propose edits until you have read the README, package/CLI wiring, active contract files, benchmark surfaces, and fixture surfaces.
