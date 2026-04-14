# APR v2 Hardening Risk Register

## HR-01 Contract / Policy / Runtime Taxonomy Drift

- Current-path or latent-seam: `current-path`
- Severity: `high`
- Likelihood: `medium`
- Impact: Residual risk is now future maintenance drift rather than an open validation hole: fixed contract taxonomies are already locked across policy, runtime, and canonical schema, but additive namespaces still need coordinated updates.
- Evidence: `scripts/validate_contract.py` now fail-closes ordered policy/runtime parity for article, claim, domain, outlet, recommendation, and processing-state taxonomies and checks canonical schema enum lockstep; `tests/contract/test_contract_manifest.py` mirrors that coverage for the policy/runtime surface.
- Exact files involved: `contracts/active/policy_layer.yaml`, `contracts/active/canonical_audit_record.schema.json`, `src/apr_core/classify/classification.py`, `src/apr_core/pipeline.py`, `src/apr_core/goldset/runner.py`, `tests/contract/test_contract_manifest.py`
- Mitigation: Preserve the current lockstep validator and contract tests, and require intentional coordinated updates when fixed taxonomies change.
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

## HR-03 Processing-State Duplication and Renderer-Boundary Drift

- Current-path or latent-seam: `current-path`
- Severity: `medium`
- Likelihood: `medium`
- Impact: Future policy or docs changes could reintroduce confusion about whether rendering belongs inside canonical provenance, weakening replay semantics and operator understanding.
- Evidence: `contracts/active/policy_layer.yaml` now stops at `PACKS_EXECUTED`; `src/apr_core/pipeline.py` provenance ends at `PACKS_EXECUTED`; rendering is downstream in `src/apr_core/render/markdown.py`; contract tests lock policy processing states to `AUDIT_PROCESSING_STATES`.
- Exact files involved: `contracts/active/policy_layer.yaml`, `src/apr_core/pipeline.py`, `src/apr_core/render/markdown.py`, `docs/ARCHITECTURE.md`, `docs/EXECUTION_MODEL.md`
- Mitigation: Preserve the explicit audit-stage/render-stage boundary in policy, docs, and contract tests.
- Validation gate: Contract tests plus targeted provenance/replay tests.
- Rollback / invariant concerns: Rendering must stay downstream and non-canonical.

## HR-04 Benchmark Manifest Contract-Version Mismatch Risk

- Current-path or latent-seam: `current-path`
- Severity: `high`
- Likelihood: `medium`
- Impact: Manifest/schema drift can still obscure where parity is enforced, but benchmark validation now fails before a stale-contract manifest can run.
- Evidence: `src/apr_core/goldset/runner.py` enforces `_assert_manifest_contract_parity()` inside `validate_goldset_manifest()`; `tests/goldset/test_goldset_runner.py::test_goldset_manifest_must_match_active_contract_version` and `tests/regression/test_cli_smoke.py::test_validate_goldset_script_fails_on_contract_version_drift` prove both runner and script entrypoints reject mismatched `contract_version`.
- Exact files involved: `benchmarks/goldset_dev/manifest.yaml`, `benchmarks/goldset_holdout/manifest.yaml`, `benchmarks/goldset/schemas/manifest.schema.json`, `scripts/validate_goldset.py`, `src/apr_core/goldset/runner.py`
- Mitigation: Preserve the existing parity guard and script-level regression coverage, and keep repo/CI validation routing through `load_goldset_manifest()`.
- Validation gate: `python scripts/validate_goldset.py`; targeted `tests/goldset/test_goldset_runner.py`
- Rollback / invariant concerns: Keep benchmark manifests benchmark-only; do not turn them into runtime-loaded contracts.

## HR-05 Docs vs Runtime / Benchmark Reality Drift

- Current-path or latent-seam: `current-path`
- Severity: `medium`
- Likelihood: `medium`
- Impact: Authoritative docs are now guarded by automated lockstep checks, but generated or historical artifacts can still confuse operators if they are treated as authority.
- Evidence: The 2026-04-09 docs sweep reconciled `README.md`, `benchmarks/goldset/README.md`, `benchmarks/goldset/holdout/README.md`, and `docs/SPEC_IMPLEMENTATION_MATRIX.md` with `benchmarks/goldset_dev/manifest.yaml` and `benchmarks/goldset_holdout/manifest.yaml`; `tests/goldset/test_holdout_split_isolation.py` plus `scripts/validate_repo_lockstep.py` now fail closed if those authoritative docs drop the active manifest paths or reintroduce stale manifest locations.
- Exact files involved: `README.md`, `benchmarks/goldset/README.md`, `benchmarks/goldset/holdout/README.md`, `docs/SPEC_IMPLEMENTATION_MATRIX.md`, `docs/BENCHMARK_POLICY.md`, `benchmarks/goldset_dev/manifest.yaml`, `benchmarks/goldset_holdout/manifest.yaml`
- Mitigation: Preserve the corrected authoritative docs and keep the authoritative-doc lockstep assertions in repo lockstep validation.
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
- Impact: Residual risk is now mostly maintenance drift: future replay fields or namespace additions could land without synchronized tests/docs, but current benchmark artifacts already fail closed on the stable replay and taxonomy surfaces.
- Evidence: `src/apr_core/goldset/runner.py` now emits replay-critical summary and ledger fields including manifest path/hash, contract/policy/schema digests, runtime identity, repo state, prior-run linkage, governance, gates, and case outcomes; `_validate_summary()` and `_append_ledger_entry()` reject unknown error classes and governance reason codes before durable artifact emission; `tests/goldset/test_goldset_runner.py` now locks both replay-envelope and namespace-validation behavior.
- Exact files involved: `src/apr_core/goldset/runner.py`, `src/apr_core/goldset/governance/governance_router.py`, `benchmarks/goldset/schemas/summary.schema.json`, `benchmarks/goldset/schemas/ledger_entry.schema.json`
- Mitigation: Preserve the current replay-envelope and namespace-validator tests, and treat any additive failure/reason-code surface as a coordinated schema/docs/test change.
- Validation gate: Goldset runner tests, adversarial tests, ledger schema validation.
- Rollback / invariant concerns: Keep benchmark-only governance additive and non-gating for live runtime semantics.

## HR-08 Non-Atomic Canonical and Report Writes

- Current-path or latent-seam: `current-path`
- Severity: `medium`
- Likelihood: `medium`
- Impact: Residual risk is now localized to future new write paths bypassing the atomic helpers; the existing canonical/report persistence path already fails closed on replacement failure.
- Evidence: `src/apr_core/utils.py` uses `_atomic_write_text()` for `write_json()` and `write_text()` and `write_text_bundle()` for multi-file installs; `src/apr_core/cli.py` routes audit, render, defense, question, and bundled goldset outputs through those helpers; `tests/regression/test_atomic_writes.py` proves existing files remain intact when replacement fails.
- Exact files involved: `src/apr_core/utils.py`, `src/apr_core/cli.py`
- Mitigation: Preserve the current atomic helper layer, keep CLI call sites on those helpers, and add tests whenever new durable output paths are introduced.
- Validation gate: Tempdir atomic-write tests plus CLI smoke.
- Rollback / invariant concerns: Preserve local-only file outputs and existing path conventions.

## HR-09 Goldset Summary / Governance / Ledger Consistency Risk

- Current-path or latent-seam: `current-path`
- Severity: `medium`
- Likelihood: `medium`
- Impact: Without transactional sequencing, benchmark artifacts can disagree about whether a run was durably recorded even if each individual file write is atomic.
- Evidence: `src/apr_core/cli.py::cmd_goldset` now snapshots summary, governance-report, and ledger files before append and restores the old-good state if ledger append fails after the final summary/report bundle is installed; `tests/regression/test_atomic_writes.py::test_cmd_goldset_restores_previous_outputs_when_ledger_append_fails` proves that rollback path.
- Exact files involved: `src/apr_core/cli.py`, `src/apr_core/goldset/runner.py`, `src/apr_core/utils.py`, `benchmarks/goldset/schemas/ledger_entry.schema.json`, `tests/regression/test_atomic_writes.py`
- Mitigation: Preserve the current snapshot-and-restore sequencing in `cmd_goldset()` and extend the regression package whenever new bundled benchmark artifacts are introduced.
- Validation gate: Goldset validation, CLI smoke, and append-failure tempdir tests.
- Rollback / invariant concerns: Preserve current-forward ledger doctrine; do not backfill history.

## HR-10 Pack Path Normalization and Import-Boundary Weakness

- Current-path or latent-seam: `current-path`
- Severity: `high`
- Likelihood: `medium`
- Impact: Residual risk is now future seam regression rather than a current provenance hole: pack requests and manifest fingerprints are already canonicalized and recorded, but the import boundary still relies on temporary `sys.path` mutation and future pack-path changes could bypass the current guardrails.
- Evidence: `src/apr_core/packs/loader.py` canonicalizes and dedupes requested pack roots, records `manifest_path`, `resolved_repo_root`, and `manifest_sha256`, and `src/apr_core/pipeline.py` copies those into `provenance.loaded_pack_fingerprints`; `tests/regression/test_pack_loading.py` plus `tests/surface_lock/test_output_surfaces.py` lock both the pack-execution and provenance surfaces.
- Exact files involved: `src/apr_core/packs/loader.py`, `src/apr_core/packs/protocol.py`, `docs/PACK_INTERFACE.md`, pack fixture tests
- Mitigation: Preserve the current canonicalization and fingerprint surfaces, and treat any future import-boundary tightening as additive hardening rather than a semantic pack change.
- Validation gate: Pack regression tests, surface-lock tests, targeted unit tests around path handling.
- Rollback / invariant concerns: Packs must remain explicit path-based advisory extensions.

## HR-11 Pack Fatal-Gate Semantics Are Ambiguous

- Current-path or latent-seam: `current-path`
- Severity: `medium`
- Likelihood: `medium`
- Impact: Residual risk is now future doctrine drift rather than a live semantic gap: the runtime already records `fatal_gates` as advisory metadata only, but later docs or pack examples could still overstate their authority if the wording regresses.
- Evidence: `docs/PACK_INTERFACE.md` and `docs/CANONICAL_AUDIT_RECORD.md` now say `pack_results[*].fatal_gates` are advisory pack requests only; `src/apr_core/packs/loader.py::_normalize_fatal_gates()` constrains scopes to the schema-backed advisory enums and normalizes the payload; `_decision_from_states()` in `src/apr_core/pipeline.py` still does not treat them as core fatal overrides; `tests/regression/test_pack_loading.py::test_physics_pack_fatal_gates_remain_advisory_requests` proves a non-empty `fatal_gates` case leaves the recommendation unchanged.
- Exact files involved: `docs/PACK_INTERFACE.md`, `src/apr_core/packs/loader.py`, `src/apr_core/pipeline.py`, pack tests
- Mitigation: Preserve the current docs-and-tests wording that keeps pack gates explicitly advisory, and treat any future renaming as an additive compatibility change rather than a semantic pack expansion.
- Validation gate: Pack regression tests and docs lockstep checks.
- Rollback / invariant concerns: Packs must not own core recommendation semantics.

## HR-12 Provider / Adapter Admission Risk

- Current-path or latent-seam: `latent-seam`
- Severity: `high`
- Likelihood: `medium`
- Impact: Residual risk is now future governance drift rather than an unguarded dormant seam: provider/adapter packages remain inactive, but any later activation still needs to preserve the repo's deterministic local-first doctrine.
- Evidence: `src/apr_core/providers/protocol.py` and `src/apr_core/adapters/__init__.py` define dormant seams only; `docs/EXECUTION_MODEL.md` and `docs/MIGRATION_POLICY.md` now require explicit docs-and-tests admission before any provider/adapter activation; `tests/regression/test_surface_isolation.py` locks both the docs and the active-runtime absence proof.
- Exact files involved: `src/apr_core/providers/protocol.py`, `src/apr_core/providers/__init__.py`, `src/apr_core/adapters/__init__.py`, `docs/EXECUTION_MODEL.md`, `docs/MIGRATION_POLICY.md`
- Mitigation: Preserve the current admission-criteria wording and seam-inertness regressions, and treat any future provider/adapter activation as a deliberate architecture change rather than incremental convenience work.
- Validation gate: Targeted seam-inertness tests and docs lockstep checks.
- Rollback / invariant concerns: Do not activate providers/adapters as part of hardening.

## HR-13 Release / Install Truth Surface Duplication

- Current-path or latent-seam: `current-path`
- Severity: `medium`
- Likelihood: `medium`
- Impact: Version, package, and release-surface changes can become partially updated across packaging, scripts, docs, and tests.
- Evidence: Version authority exists in `setup.py`, manifest, and tests; release semantics live in `scripts/build_release.py`, `docs/RELEASE_POLICY.md`, CI, and `pyproject.toml`.
- Exact files involved: `pyproject.toml`, `setup.py`, `contracts/active/manifest.yaml`, `scripts/build_release.py`, `.github/workflows/ci.yml`, `docs/RELEASE_POLICY.md`, `tests/contract/test_contract_manifest.py`
- Mitigation: Preserve the release-surface lock tests and keep version/source relationships explicit in validation docs.
- Validation gate: Clean-tree release smoke plus contract validation.
- Rollback / invariant concerns: Preserve `apr-v2` package identity and `apr` CLI bootstrap path.
