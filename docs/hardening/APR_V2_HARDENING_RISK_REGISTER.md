# APR v2 Hardening Risk Register

## HR-01 Contract / Policy / Runtime Taxonomy Drift

- Current-path or latent-seam: `current-path`
- Severity: `high`
- Likelihood: `medium`
- Impact: Recommendation, outlet, domain, or stage semantics can diverge across doctrine, schema, runtime, and benchmark scoring, creating false confidence in contract stability.
- Evidence: `contracts/active/policy_layer.yaml`, `src/apr_core/classify/classification.py`, `src/apr_core/pipeline.py`, `src/apr_core/goldset/runner.py`, `scripts/validate_contract.py`
- Exact files involved: `contracts/active/policy_layer.yaml`, `contracts/active/canonical_audit_record.schema.json`, `src/apr_core/classify/classification.py`, `src/apr_core/pipeline.py`, `src/apr_core/goldset/runner.py`, `tests/contract/test_contract_manifest.py`
- Mitigation: Add lockstep validation over taxonomies and close schema enums where semantics are fixed today.
- Validation gate: `python scripts/validate_contract.py`; targeted contract and surface-lock pytest.
- Rollback / invariant concerns: Preserve active-contract supremacy; do not move benchmark-only semantics into live runtime policy.

## HR-02 Canonical Schema Under-Specifies Nested Semantics

- Current-path or latent-seam: `current-path`
- Severity: `high`
- Likelihood: `high`
- Impact: Contract-valid canonical records can still carry off-taxonomy strings for classification or routing fields.
- Evidence: `contracts/active/canonical_audit_record.schema.json` leaves `classification.*` and `venue.routing_state` as plain strings while runtime and policy treat them as fixed vocabularies.
- Exact files involved: `contracts/active/canonical_audit_record.schema.json`, `docs/CANONICAL_AUDIT_RECORD.md`, `src/apr_core/classify/classification.py`, `src/apr_core/venue/routing.py`, `tests/surface_lock/test_output_surfaces.py`
- Mitigation: Tighten nested enums and closed object shapes additively.
- Validation gate: Contract validation plus output-surface lock tests.
- Rollback / invariant concerns: Additive schema migration only; keep `CanonicalAuditRecord` as the only truth object.

## HR-03 Processing-State Duplication and `RENDERED` Drift

- Current-path or latent-seam: `current-path`
- Severity: `medium`
- Likelihood: `medium`
- Impact: Provenance can imply stage states that `run_audit()` never emits, weakening replay and docs accuracy.
- Evidence: `contracts/active/policy_layer.yaml` includes `RENDERED`; `src/apr_core/pipeline.py` provenance ends at `PACKS_EXECUTED`; rendering is downstream in `src/apr_core/render/markdown.py`.
- Exact files involved: `contracts/active/policy_layer.yaml`, `src/apr_core/pipeline.py`, `src/apr_core/render/markdown.py`, `docs/ARCHITECTURE.md`, `docs/EXECUTION_MODEL.md`
- Mitigation: Split audit-stage provenance from render-stage provenance or document/render the distinction explicitly and test it.
- Validation gate: Contract tests plus targeted provenance/replay tests.
- Rollback / invariant concerns: Rendering must stay downstream and non-canonical.

## HR-04 Benchmark Manifest Contract-Version Mismatch Risk

- Current-path or latent-seam: `current-path`
- Severity: `high`
- Likelihood: `medium`
- Impact: Benchmark summaries could appear healthy while measuring against a stale contract version.
- Evidence: `benchmarks/goldset_dev/manifest.yaml` and `benchmarks/goldset_holdout/manifest.yaml` currently match `2.1.0`, but `benchmarks/goldset/schemas/manifest.schema.json` types `contract_version` only as string and `scripts/validate_goldset.py` does not compare against the active manifest.
- Exact files involved: `benchmarks/goldset_dev/manifest.yaml`, `benchmarks/goldset_holdout/manifest.yaml`, `benchmarks/goldset/schemas/manifest.schema.json`, `scripts/validate_goldset.py`, `src/apr_core/goldset/runner.py`
- Mitigation: Add explicit active-contract parity validation and CI checks.
- Validation gate: `python scripts/validate_goldset.py`; targeted `tests/goldset/test_goldset_runner.py`
- Rollback / invariant concerns: Keep benchmark manifests benchmark-only; do not turn them into runtime-loaded contracts.

## HR-05 Docs vs Runtime / Benchmark Reality Drift

- Current-path or latent-seam: `current-path`
- Severity: `medium`
- Likelihood: `medium`
- Impact: Authoritative docs are now aligned, but future contributors can still reintroduce manifest-path or holdout-state drift because no automated docs lockstep gate exists yet.
- Evidence: The 2026-04-09 docs sweep reconciled `README.md`, `benchmarks/goldset/README.md`, `benchmarks/goldset/holdout/README.md`, and `docs/SPEC_IMPLEMENTATION_MATRIX.md` with `benchmarks/goldset_dev/manifest.yaml` and `benchmarks/goldset_holdout/manifest.yaml`; residual stale strings remain only in generated or historical surfaces such as `src/apr_v2.egg-info/`, `dist/`, and prior `output/` artifacts.
- Exact files involved: `README.md`, `benchmarks/goldset/README.md`, `benchmarks/goldset/holdout/README.md`, `docs/SPEC_IMPLEMENTATION_MATRIX.md`, `docs/BENCHMARK_POLICY.md`, `benchmarks/goldset_dev/manifest.yaml`, `benchmarks/goldset_holdout/manifest.yaml`
- Mitigation: Preserve the corrected authoritative docs and add docs lockstep checks against manifests so drift fails closed.
- Validation gate: Docs lockstep tests and benchmark validation.
- Rollback / invariant concerns: Favor documentation corrections over behavior changes when behavior is already coherent.

## HR-06 Canonical Provenance Replay Gap

- Current-path or latent-seam: `current-path`
- Severity: `high`
- Likelihood: `medium`
- Impact: Canonical records are hard to replay or compare across runs because they lack input digests, pack fingerprints, and runtime source fingerprints.
- Evidence: `src/apr_core/pipeline.py` provenance contains versions, time, and stage list only; schema matches that minimal surface.
- Exact files involved: `src/apr_core/pipeline.py`, `contracts/active/canonical_audit_record.schema.json`, `docs/CANONICAL_AUDIT_RECORD.md`, `tests/surface_lock/test_output_surfaces.py`
- Mitigation: Add deterministic replay fields additively to canonical provenance.
- Validation gate: Contract tests, replay tests, and output-surface locks.
- Rollback / invariant concerns: Do not encode mutable external-service identifiers or break existing canonical semantics.

## HR-07 Benchmark Replay / Failure-Taxonomy Gap

- Current-path or latent-seam: `current-path`
- Severity: `medium`
- Likelihood: `medium`
- Impact: Benchmark regressions may remain explainable only by code reading rather than durable, schema-closed audit artifacts.
- Evidence: `src/apr_core/goldset/runner.py` records rich governance data, but many error classes, reason codes, and drift categories are still code-defined strings across schemas and tests.
- Exact files involved: `src/apr_core/goldset/runner.py`, `src/apr_core/goldset/governance/governance_router.py`, `benchmarks/goldset/schemas/summary.schema.json`, `benchmarks/goldset/schemas/ledger_entry.schema.json`
- Mitigation: Close failure taxonomies where stable, add replay fingerprints, and align schemas/tests/docs.
- Validation gate: Goldset runner tests, adversarial tests, ledger schema validation.
- Rollback / invariant concerns: Keep benchmark-only governance additive and non-gating for live runtime semantics.

## HR-08 Non-Atomic Canonical and Report Writes

- Current-path or latent-seam: `current-path`
- Severity: `medium`
- Likelihood: `medium`
- Impact: Interrupted writes can leave partial canonical JSON, markdown, summary JSON, or governance report JSON on disk.
- Evidence: `src/apr_core/utils.py` writes directly with `Path.write_text`; `src/apr_core/cli.py` writes audit/render/goldset outputs directly.
- Exact files involved: `src/apr_core/utils.py`, `src/apr_core/cli.py`
- Mitigation: Introduce atomic temp-file-and-replace write helpers and update CLI call sites.
- Validation gate: Tempdir atomic-write tests plus CLI smoke.
- Rollback / invariant concerns: Preserve local-only file outputs and existing path conventions.

## HR-09 Non-Atomic JSONL Ledger Append

- Current-path or latent-seam: `current-path`
- Severity: `medium`
- Likelihood: `medium`
- Impact: Interrupted or concurrent writes can corrupt calibration history or create partial rows.
- Evidence: `_append_ledger_entry()` in `src/apr_core/goldset/runner.py` appends directly to JSONL after validation.
- Exact files involved: `src/apr_core/goldset/runner.py`, `benchmarks/goldset/schemas/ledger_entry.schema.json`, `tests/goldset/test_goldset_runner.py`
- Mitigation: Add crash-safe append strategy, explicit fsync/flush behavior, and tempdir/concurrency tests.
- Validation gate: Goldset ledger tests and replay/append tempdir tests.
- Rollback / invariant concerns: Preserve current-forward ledger doctrine; do not backfill history.

## HR-10 Pack Path Normalization and Import-Boundary Weakness

- Current-path or latent-seam: `current-path`
- Severity: `high`
- Likelihood: `medium`
- Impact: Advisory extension loading is broader than necessary and can make provenance weaker than repo doctrine implies.
- Evidence: `src/apr_core/packs/loader.py` accepts raw paths, normalizes minimally, mutates global `sys.path`, and does not capture pack digests or canonical resolved paths.
- Exact files involved: `src/apr_core/packs/loader.py`, `src/apr_core/packs/protocol.py`, `docs/PACK_INTERFACE.md`, pack fixture tests
- Mitigation: Canonicalize paths, dedupe requests, guard path traversal/symlink surprises, and capture pack source identity in runtime provenance.
- Validation gate: Pack regression tests, surface-lock tests, targeted unit tests around path handling.
- Rollback / invariant concerns: Packs must remain explicit path-based advisory extensions.

## HR-11 Pack Fatal-Gate Semantics Are Ambiguous

- Current-path or latent-seam: `current-path`
- Severity: `medium`
- Likelihood: `medium`
- Impact: Future contributors can misread pack fatal-gate requests as authorization to own core recommendation semantics.
- Evidence: `docs/PACK_INTERFACE.md` says packs may add scoped fatal-gate requests; `src/apr_core/packs/loader.py` normalizes `fatal_gates`; `_decision_from_states()` in `src/apr_core/pipeline.py` does not treat them as core fatal overrides.
- Exact files involved: `docs/PACK_INTERFACE.md`, `src/apr_core/packs/loader.py`, `src/apr_core/pipeline.py`, pack tests
- Mitigation: Clarify naming and tests so pack gates remain advisory requests or explicitly scoped non-core signals.
- Validation gate: Pack regression tests and docs lockstep checks.
- Rollback / invariant concerns: Packs must not own core recommendation semantics.

## HR-12 Provider / Adapter Admission Risk

- Current-path or latent-seam: `latent-seam`
- Severity: `high`
- Likelihood: `medium`
- Impact: Future seam activation could violate deterministic local-first architecture and introduce ungoverned contracts.
- Evidence: `src/apr_core/providers/protocol.py` and `src/apr_core/adapters/__init__.py` define dormant seams only; `docs/EXECUTION_MODEL.md` says no external provider is active.
- Exact files involved: `src/apr_core/providers/protocol.py`, `src/apr_core/providers/__init__.py`, `src/apr_core/adapters/__init__.py`, `docs/EXECUTION_MODEL.md`, `docs/MIGRATION_POLICY.md`
- Mitigation: Add explicit admission checklist, inertness tests, and docs defining conditions for future activation.
- Validation gate: Targeted seam-inertness tests and docs lockstep checks.
- Rollback / invariant concerns: Do not activate providers/adapters as part of hardening.

## HR-13 Release / Install Truth Surface Duplication

- Current-path or latent-seam: `current-path`
- Severity: `medium`
- Likelihood: `medium`
- Impact: Version, package, and release-surface changes can become partially updated across packaging, scripts, docs, and tests.
- Evidence: Version authority exists in `setup.py`, manifest, and tests; release semantics live in `scripts/build_release.py`, `docs/RELEASE_POLICY.md`, CI, and `pyproject.toml`.
- Exact files involved: `pyproject.toml`, `setup.py`, `contracts/active/manifest.yaml`, `scripts/build_release.py`, `.github/workflows/ci.yml`, `docs/RELEASE_POLICY.md`, `tests/contract/test_contract_manifest.py`
- Mitigation: Add release-surface lock tests and make version/source relationships explicit in validation docs.
- Validation gate: Clean-tree release smoke plus contract validation.
- Rollback / invariant concerns: Preserve `apr-v2` package identity and `apr` CLI bootstrap path.
