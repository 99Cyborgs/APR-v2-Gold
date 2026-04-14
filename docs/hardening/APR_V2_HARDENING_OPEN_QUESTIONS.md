# APR v2 Hardening Open Questions

These questions were not blocking for this planning pass. Each has a conservative default so later execution can proceed with low ambiguity.

## OQ-01 Branch Promotion Order

- Confirmed fact: the reviewed working branch `codex/full-worktree-publish` is ahead of default branch `main` and contains several benchmark-governance surfaces named in the mission.
- Conservative default: plan future hardening PRs against the working branch first, then explicitly decide whether to merge or replay the sequence onto `main`.
- Impact if ignored: a package can be planned against files that do not yet exist on default branch.

## OQ-02 Holdout Terminology

- Confirmed fact: `benchmarks/goldset_holdout/manifest.yaml` contains 3 active holdout cases, and the highest-signal authoritative docs were reconciled on 2026-04-09 to describe holdout as active blind evaluation.
- Conservative default: treat `README.md`, `benchmarks/goldset/README.md`, `benchmarks/goldset/holdout/README.md`, `docs/SPEC_IMPLEMENTATION_MATRIX.md`, and `docs/BENCHMARK_POLICY.md` as the current authority; ignore stale strings in generated or historical artifacts.
- Impact if ignored: contributors can still mistake derived artifacts for authority even though the authoritative docs now have automated lockstep coverage.

## OQ-03 Canonical Provenance Scope

- Confirmed fact: canonical provenance currently records versions, timestamp, and completed processing states only.
- Conservative default: add replay fingerprints only for local deterministic surfaces already present in the repo, such as normalized-input digests, pack source identity, and runtime/build fingerprints.
- Impact if ignored: provenance hardening could bloat the canonical record or accidentally introduce non-local fields.

## OQ-04 Pack Fatal-Gate Naming

- Resolved on `2026-04-13`: `docs/PACK_INTERFACE.md` and `docs/CANONICAL_AUDIT_RECORD.md` now say `pack_results[*].fatal_gates` are advisory pack requests only, and `tests/regression/test_pack_loading.py::test_physics_pack_fatal_gates_remain_advisory_requests` proves a non-empty `fatal_gates` case does not change the core recommendation.
- Residual risk if ignored elsewhere: future wording drift could still overstate pack authority, but the current runtime and doctrine surfaces are explicit.

## OQ-05 `apr doctor` Semantics

- Resolved on `2026-04-13`: `src/apr_core/cli.py::cmd_doctor()` returns runtime and repo wiring status as-is, while `cmd_readiness()` applies the clean-worktree release gate with `reason=release_readiness_requires_clean_worktree`.
- Validation evidence: `tests/regression/test_cli_smoke.py::test_doctor_command_reports_dirty_git_without_failing`, `tests/regression/test_cli_smoke.py::test_readiness_command_rejects_dirty_git`, `tests/regression/test_cli_smoke.py::test_doctor_cli_smoke`, and `::test_readiness_cli_smoke`.
- Residual risk if ignored elsewhere: stale operator docs could still misdescribe the split, but the runtime path itself is no longer ambiguous.

## OQ-06 Replay Metadata Location for Goldset

- Confirmed fact: the benchmark summary/ledger replay envelope now records manifest path/hash, contract/policy/schema digests, runtime identity, repo state, prior-run linkage, governance, gates, and case outcomes.
- Conservative default: preserve benchmark-only replay metadata in summary/ledger surfaces and extend that envelope there before considering any benchmark-specific addition to the live runtime record.
- Impact if ignored: benchmark governance fields can leak into live runtime contract surfaces.

## OQ-07 Release Surface Lock Depth

- Confirmed fact: releases rely on active manifest version and clean-tree enforcement, and `tests/regression/test_release_contract.py` now locks the package/bootstrap/version/exclusion truth surface.
- Conservative default: preserve the existing release-surface lock test and extend it only when package or release doctrine changes.
- Impact if ignored: future release changes can still drift if contributors update packaging or docs without keeping the explicit lock test aligned.
