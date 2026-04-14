# Benchmark Policy

This file is the authoritative benchmark-governance document for APR v2 Gold.

## Scope

- Development benchmark execution defaults to `benchmarks/goldset_dev/manifest.yaml`.
- Blind holdout benchmark execution defaults to `benchmarks/goldset_holdout/manifest.yaml`.
- Both manifests are schema-validated by `benchmarks/goldset/schemas/manifest.schema.json`.
- Both manifests must also match the active runtime contract version in `contracts/active/manifest.yaml`.
- Run summaries are validated by `benchmarks/goldset/schemas/summary.schema.json`.
- Calibration ledger entries are validated by `benchmarks/goldset/schemas/ledger_entry.schema.json`.
- `python scripts/validate_repo_lockstep.py` is the minimum repo lockstep gate for contract validation, benchmark validation, authoritative holdout-doc checks, and CLI smoke coverage.
- `docs/BENCHMARK_PROTOCOL.md` and `docs/GOLDSET_PROTOCOL.md` remain as compatibility pointers only.

## Strata

- `core_gold`: authoritative hard-gate cases. Any failing active `core_gold` case fails the benchmark gate.
- `stress_gold`: active calibration pressure cases. They stay visible in summaries and error-class accounting, but they do not all break the merge gate by default.
- `holdout`: reserved for real untuned public fixtures. Development runs exclude active holdout cases. `apr goldset --holdout` runs holdout-only blind evaluation and redacts expected holdout surfaces from emitted summaries. `--holdout-eval` remains a compatibility alias.

## Case Rules

- Every active case must declare a `case_id`, `split`, `stratum`, `partition`, `category`, `input`, `expected`, and any `required_nonempty_paths`.
- APR v4-aligned case aliases are supported through `central_claim`, `claim_type`, and `expected_decision`. These must remain consistent with the underlying benchmark expectation surface.
- `expected.exact` is restricted to stable benchmarkable surfaces in the canonical audit record.
- `expected.recommendation_band` is allowed when exact recommendation matching would overstate certainty.
- `ambiguity_class` must be explicit when a case is intentionally borderline.
- `case_state: scaffold` is allowed only for excluded future work and may not silently enter merge gates.

## Gate Rules

- Absolute gate failure:
  - any failing active `core_gold` case
  - any `false_accept_on_fatal_case`
  - any `missed_fatal_gate`
- Delta gate failure against the most recent ledger entry:
  - any increase in fatal-gate misses
  - any new wrong recommendation on `null_or_replication` cases
  - any new specialist false reject
  - any new missing required evidence-anchor path on previously passing `core_gold` cases
- Rolling regression governor failure against the last N comparable ledger entries:
  - fatal error count exceeds the rolling baseline envelope
  - any new failure class appears in `core_gold`
- Ambiguous stress cases remain visible in summaries, but their failures do not automatically break the merge gate unless they trip one of the explicit gate conditions above.

## Ledger Rules

- `apr goldset` writes JSONL ledger entries by default to `benchmarks/goldset/output/calibration_ledger.jsonl`.
- `apr goldset --holdout` writes to the separate holdout ledger by default unless a ledger path is passed explicitly. `--holdout-eval` remains a compatibility alias.
- Summary JSON and appended ledger rows are the replay envelope for benchmark runs: they carry manifest path/hash, active contract/policy/schema digests, runtime identity, repo state, prior-run linkage, governance, gates, and case outcomes.
- When summary files are emitted, the summary JSON and governance report are persisted before the ledger row is appended.
- Ledger entries record manifest hash, contract version, result counts, error-class counts, decision-algebra totals, cross-case diagnostics, case deltas, recommendation transitions, gate status, and optional notes/operator metadata.
- Unknown benchmark failure classes or governance reason codes are rejected before summary return or ledger append so durable artifacts fail closed on namespace drift.
- No fake history is backfilled. The ledger is current-forward only.

## Terminology

- `stratum`: governance weight of a case set.
- `split`: execution lane for the case set, currently `dev` or `holdout`.
- `partition`: mechanism-oriented grouping inside a stratum.
- `category`: case-local analytic label.
- `gate_behavior`: `hard`, `monitor`, or `exclude`.
- `error_class`: mechanism-level explanation for a mismatch, not just a surface diff.
