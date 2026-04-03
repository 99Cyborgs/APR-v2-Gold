# Goldset Harness

This directory is the executable benchmark spine for APR v2 Gold.

## Contents

- `manifest.yaml`: authoritative machine-readable case registry.
- `schemas/`: JSON Schemas for the manifest, run summary, and calibration ledger entry.
- `cases/`: fixture-location note only. Executable payloads stay in `fixtures/inputs/`.
- `holdout/`: reserved for real untuned public holdout material. No active public holdout cases exist yet.

## Execution

- Validate structure: `python scripts/validate_goldset.py`
- Run the harness: `apr goldset --output output/goldset_summary.json`
- Run blind holdout evaluation: `apr goldset --holdout-eval --no-ledger --output output/holdout_summary.json`
- Summarize a run: `python scripts/summarize_goldset.py output/goldset_summary.json`

## Governance

- Benchmark policy: `docs/BENCHMARK_POLICY.md`
- Case schema: `docs/GOLDSET_CASE_SCHEMA.md`
- Spec/implementation boundary: `docs/SPEC_IMPLEMENTATION_MATRIX.md`

`apr goldset` writes a JSONL calibration ledger by default to `benchmarks/goldset/output/calibration_ledger.jsonl`.
`apr goldset --holdout-eval` uses the separate holdout ledger by default and redacts holdout expectation surfaces from the emitted summary.
