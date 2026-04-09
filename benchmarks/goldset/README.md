# Goldset Harness

This directory is the executable benchmark spine for APR v2 Gold.

## Contents

- `../goldset_dev/manifest.yaml`: authoritative machine-readable registry for the default development lane.
- `../goldset_holdout/manifest.yaml`: authoritative machine-readable registry for the blind holdout lane.
- `schemas/`: JSON Schemas for the manifest, run summary, and calibration ledger entry.
- `cases/`: fixture-location note only. Executable payloads stay in `fixtures/inputs/`.
- `holdout/`: compatibility note directory only. Active holdout execution is defined by `../goldset_holdout/manifest.yaml`.

## Execution

- Validate structure: `python scripts/validate_goldset.py`
- Run the harness: `apr goldset --output output/goldset_summary.json`
- Run blind holdout evaluation: `apr goldset --holdout --no-ledger --output output/holdout_summary.json`
- Summarize a run: `python scripts/summarize_goldset.py output/goldset_summary.json`

## Governance

- Benchmark policy: `docs/BENCHMARK_POLICY.md`
- Case schema: `docs/GOLDSET_CASE_SCHEMA.md`
- Spec/implementation boundary: `docs/SPEC_IMPLEMENTATION_MATRIX.md`

`apr goldset` writes a JSONL calibration ledger by default to `benchmarks/goldset/output/calibration_ledger.jsonl`.
`apr goldset --holdout` uses the separate holdout ledger by default and redacts holdout expectation surfaces from the emitted summary.
`apr goldset --holdout-eval` and `apr-holdout` remain compatibility entrypoints for the same blind holdout lane.
