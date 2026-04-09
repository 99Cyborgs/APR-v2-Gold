# APR v2 Gold

## Current State

- `APR v2 Gold` is a Python 3.12 deterministic manuscript-audit engine packaged as `apr-v2` with the `apr` CLI.
- The active local runtime lives in `src/apr_core/`, and the active contract and policy layer live in `contracts/active/`.
- The CLI currently supports repo/runtime validation (`apr doctor`), release readiness checks (`apr readiness`), audit execution (`apr audit`), markdown rendering from canonical records (`apr render`), benchmark execution (`apr goldset`), and advisory-pack inspection (`apr packs`).
- The benchmark harness is live with shared schemas and operator docs in `benchmarks/goldset/`, plus executable manifests in `benchmarks/goldset_dev/manifest.yaml` and `benchmarks/goldset_holdout/manifest.yaml`.
- The benchmarked surfaces currently include central-claim recovery, article and claim classification, reviewability gating, scientific-record gating, venue routing after gating, integrity escalation, human-escalation signaling, and advisory-pack execution visibility.
- The public repo already distinguishes `core_gold`, `stress_gold`, and `holdout` strata, and the holdout lane is active as a separate blind-evaluation manifest that stays outside development tuning by default.

## Goal

- Build a deterministic, contract-driven audit engine that turns a normalized manuscript package into one canonical audit record.
- Keep the system benchmarkable and reproducible so claim recovery, record-readiness decisions, routing, and escalation behavior can be checked against explicit expectations.
- Preserve core semantics in the local engine while allowing external packs to add advisory context without redefining the canonical decision surfaces.

## Next Steps

- Expand benchmark coverage for implemented-but-not-frozen surfaces such as transparency sub-assessment details, rehabilitation-plan ranking, and markdown rendering behavior.
- Expand the active `holdout` lane with additional untuned public fixtures while preserving the existing blind-evaluation split from development cases.
- Continue tightening the benchmark-governance layer so the manifest, schemas, ledger outputs, and spec/implementation boundary stay aligned as the engine evolves.
