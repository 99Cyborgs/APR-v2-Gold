# APR v2 Hardening Open Questions

These questions were not blocking for this planning pass. Each has a conservative default so later execution can proceed with low ambiguity.

## OQ-01 Branch Promotion Order

- Confirmed fact: the reviewed working branch `codex/full-worktree-publish` is ahead of default branch `main` and contains several benchmark-governance surfaces named in the mission.
- Conservative default: plan future hardening PRs against the working branch first, then explicitly decide whether to merge or replay the sequence onto `main`.
- Impact if ignored: a package can be planned against files that do not yet exist on default branch.

## OQ-02 Holdout Terminology

- Confirmed fact: `benchmarks/goldset_holdout/manifest.yaml` contains 3 active holdout cases, and the highest-signal authoritative docs were reconciled on 2026-04-09 to describe holdout as active blind evaluation.
- Conservative default: treat `README.md`, `benchmarks/goldset/README.md`, `benchmarks/goldset/holdout/README.md`, `docs/SPEC_IMPLEMENTATION_MATRIX.md`, and `docs/BENCHMARK_POLICY.md` as the current authority; ignore stale strings in generated or historical artifacts.
- Impact if ignored: contributors can still mistake derived artifacts for authority and reintroduce drift because no docs lockstep test exists yet.

## OQ-03 Canonical Provenance Scope

- Confirmed fact: canonical provenance currently records versions, timestamp, and completed processing states only.
- Conservative default: add replay fingerprints only for local deterministic surfaces already present in the repo, such as normalized-input digests, pack source identity, and runtime/build fingerprints.
- Impact if ignored: provenance hardening could bloat the canonical record or accidentally introduce non-local fields.

## OQ-04 Pack Fatal-Gate Naming

- Confirmed fact: pack outputs include `fatal_gates`, but the core decision path does not treat them as pack-owned recommendation overrides.
- Conservative default: rename or document them as advisory fatal-gate requests, not core gates.
- Impact if ignored: future contributors can over-interpret pack authority and erode pack restraint.

## OQ-05 `apr doctor` Semantics

- Confirmed fact: `apr doctor` currently validates runtime wiring and also fails on dirty git state.
- Conservative default: keep current behavior until a dedicated readiness-vs-runtime split is explicitly implemented.
- Impact if ignored: local operators may continue to read a dirty-tree failure as a runtime defect rather than a readiness policy failure.

## OQ-06 Replay Metadata Location for Goldset

- Confirmed fact: the benchmark ledger already records commit, contract, manifest, gates, and governance fields, but not every potential replay fingerprint.
- Conservative default: prefer benchmark-only replay metadata in summary/ledger surfaces rather than expanding the live runtime record with benchmark-specific details.
- Impact if ignored: benchmark governance fields can leak into live runtime contract surfaces.

## OQ-07 Release Surface Lock Depth

- Confirmed fact: releases currently rely on active manifest version and clean-tree enforcement, but there is no explicit release-surface lock test.
- Conservative default: add release-surface tests only after docs, contract, and benchmark parity work lands.
- Impact if ignored: release hardening can arrive before the repo’s truth surfaces are fully aligned and cause churn.
