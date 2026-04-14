# APR v2 Hardening Phases

## Phase 1. Fail-Closed Contract and Canonical-Record Hardening

- Objective: Remove silent drift between the active contract, policy layer, canonical schema, and live runtime semantics without changing recommendation logic.
- Why this phase comes now: Every later hardening package depends on clear taxonomy authority and a stricter canonical contract boundary.
- Workstreams:
  - Add taxonomy lockstep validation across manifest, policy, runtime, and benchmark code.
  - Tighten canonical schema coverage for fixed semantic fields that are currently free strings.
  - Resolve audit-stage versus render-stage processing-state doctrine.
- Affected files and directories: `contracts/active/`, `src/apr_core/{pipeline.py,models.py,classify/,venue/,render/}`, `scripts/validate_contract.py`, `tests/contract/`, `tests/surface_lock/`, `docs/{CANONICAL_AUDIT_RECORD.md,CONTRACT_POLICY.md,ARCHITECTURE.md,EXECUTION_MODEL.md}`
- Preserved invariants:
  - `CanonicalAuditRecord` remains the only canonical runtime truth object.
  - `contracts/active/` remains the only runtime-loadable contract surface.
  - Renderers remain downstream consumers and do not redefine canonical meaning.
- Dependencies: None beyond the current reviewed branch state.
- Validation gates:
  - `python scripts/validate_contract.py`
  - `python -m pytest tests/contract tests/regression/test_minimal_pipeline.py tests/surface_lock/test_output_surfaces.py -q`
  - `apr doctor` on a clean worktree
- Rollback concerns: Schema closure will touch docs and surface-lock tests; any rollback must revert contract, docs, and test updates together.
- Estimated PR waves: 2 to 3 PRs across `WP-01` to `WP-03`
- Explicitly out of scope:
  - New recommendation states
  - Provider activation
  - Benchmark-governance redesign
- Counterpoint: Centralizing all taxonomies into Python constants would be faster than validating multiple surfaces.
- Resolution: Reject that approach; keep the active contract authoritative and add fail-closed parity checks instead.

## Phase 2. Validation, Regression, and Replay Hardening

- Objective: Make repo health, benchmark truth, and docs lockstep detectable through explicit validation surfaces before runtime drift ships.
- Why this phase comes now: Once the runtime contract surface is clearer, the next highest-value move is catching benchmark/docs divergence early.
- Workstreams:
  - Enforce benchmark manifest parity with the active contract version.
  - Unify validation expectations across scripts, CI, docs, and developer workflow.
  - Tighten holdout truthfulness and development-vs-holdout isolation checks.
- Affected files and directories: `benchmarks/goldset*/`, `benchmarks/goldset/schemas/`, `src/apr_core/goldset/runner.py`, `scripts/validate_goldset.py`, `.github/workflows/ci.yml`, `Makefile`, `tests/goldset/`, `tests/regression/`, `docs/{BENCHMARK_POLICY.md,GOLDSET_CASE_SCHEMA.md,SPEC_IMPLEMENTATION_MATRIX.md,DEVELOPMENT.md}`
- Preserved invariants:
  - Benchmark governance remains additive and separate from live runtime policy.
  - Holdout evaluation remains blind and isolated from development baselines.
  - Gold-set harness remains first-class architecture.
- Dependencies: Phase 1 taxonomy inventory is helpful for parity checks but benchmark manifest parity can start independently.
- Validation gates:
  - `python scripts/validate_goldset.py`
  - `python -m pytest tests/goldset tests/regression/test_cli_smoke.py tests/regression/test_surface_isolation.py -q`
  - `apr goldset --output <tmp-summary>`
  - `apr goldset --holdout --no-ledger --output <tmp-holdout-summary>`
- Rollback concerns: Keep benchmark-only validation failures from being misread as live runtime behavior changes.
- Estimated PR waves: 2 to 3 PRs across `WP-04` to `WP-06`
- Explicitly out of scope:
  - New benchmark strata
  - New holdout data acquisition
  - Changing live audit semantics through benchmark scoring
- Counterpoint: Benchmark validations are already strong enough; adding more could be duplicate ceremony.
- Resolution: Docs drift and manifest-version parity gaps prove current validations are not yet sufficient at the repo-truth layer.

## Phase 3. Provenance, Auditability, and Failure-Classification Hardening

- Objective: Make runtime and benchmark outputs materially easier to replay, compare, and audit without altering decision semantics.
- Why this phase comes now: Provenance fields should be designed after contract closure and before IO hardening locks the write path.
- Workstreams:
  - Expand canonical provenance with deterministic replay fingerprints.
  - Expand benchmark summary/ledger replay metadata and cross-run comparators.
  - Close stable failure-taxonomy and reason-code surfaces where they already behave like contracts.
- Affected files and directories: `src/apr_core/pipeline.py`, `contracts/active/canonical_audit_record.schema.json`, `src/apr_core/goldset/{runner.py,governance/}`, `benchmarks/goldset/schemas/{summary.schema.json,ledger_entry.schema.json}`, `tests/goldset/`, `tests/regression/{test_trace_stability.py,test_invariance_trace.py}`, `tests/adversarial/`, `docs/{CANONICAL_AUDIT_RECORD.md,BENCHMARK_POLICY.md}`
- Preserved invariants:
  - Recommendation logic and ordering remain unchanged.
  - Benchmark-only metadata stays out of live runtime semantics.
  - Provenance additions remain local deterministic surfaces only.
- Dependencies: Phase 1 schema closure; Phase 2 benchmark parity.
- Validation gates:
  - Contract validation
  - Goldset summary and ledger schema validation
  - Replay-focused pytest targets
  - Repeated-run comparison checks
- Rollback concerns: Provenance additions will cascade into schema, docs, surface locks, and replay tests.
- Estimated PR waves: 2 to 3 PRs across `WP-07` to `WP-09`
- Explicitly out of scope:
  - External telemetry or service-backed audit trails
  - Provider metadata
  - Non-local experiment tracking
- Counterpoint: Some replay metadata belongs only in the benchmark ledger, not in the canonical record.
- Resolution: Accept the distinction; phase output should split live provenance from benchmark-only replay metadata rather than flatten them together.

## Phase 4. Output, Artifact, and Local Runtime Resilience Hardening

- Objective: Make local file outputs and readiness surfaces resilient to interruption, partial writes, and operator ambiguity.
- Why this phase comes now: Output-path hardening should land after provenance fields settle, otherwise the write layer churns twice.
- Workstreams:
  - Add atomic write primitives for canonical JSON and markdown.
  - Make summary/governance-report/ledger persistence crash-safe.
  - Separate runtime health from release readiness where current CLI semantics blur them.
- Affected files and directories: `src/apr_core/utils.py`, `src/apr_core/cli.py`, `src/apr_core/goldset/runner.py`, `scripts/build_release.py`, `tests/regression/test_cli_smoke.py`, `tests/goldset/test_goldset_runner.py`, `docs/{DEVELOPMENT.md,RELEASE_POLICY.md}`
- Preserved invariants:
  - Local filesystem output remains the only persistence mode.
  - Release clean-tree policy remains intact unless intentionally split into a separate readiness check.
  - No services, databases, or daemons are introduced.
- Dependencies: Phase 3 provenance design for stable output payload shapes.
- Validation gates:
  - CLI smoke tests
  - Tempdir write-integrity tests
  - Goldset ledger append tests
  - Clean-tree `python scripts/build_release.py`
- Rollback concerns: Atomic-write helpers must remain cross-platform and not break current path conventions or output locations.
- Estimated PR waves: 2 to 3 PRs across `WP-10` to `WP-12`
- Execution note: `WP-10`, `WP-11`, and `WP-12` completed on `2026-04-13`; Phase 4 now has explicit tempdir rollback coverage for local writes plus command-level regressions that distinguish `apr doctor` runtime health from `apr readiness` clean-worktree policy.
- Explicitly out of scope:
  - Distributed locking
  - Queue-backed job management
  - Cloud artifact storage
- Counterpoint: Simple direct writes are acceptable for a local-first tool.
- Resolution: Local-first does not remove the need for crash safety, especially for canonical outputs and JSONL calibration history.

## Phase 5. Latent Seam Hardening for Packs, Adapters, and Providers

- Objective: Narrow extension trust boundaries and formalize admission criteria without activating dormant seams.
- Why this phase comes now: Contract, provenance, and IO boundaries should already be stable before tightening external-extension seams.
- Workstreams:
  - Canonicalize pack paths and capture pack source identity cleanly.
  - Clarify advisory-only pack semantics for fatal-gate requests and escalation metadata.
  - Add explicit inertness/admission guardrails for providers and adapters.
- Affected files and directories: `src/apr_core/packs/`, `fixtures/external_packs/`, `src/apr_core/providers/`, `src/apr_core/adapters/`, `docs/{PACK_INTERFACE.md,EXECUTION_MODEL.md,MIGRATION_POLICY.md}`, `tests/regression/test_pack_loading.py`, `tests/regression/test_surface_isolation.py`
- Preserved invariants:
  - Packs remain advisory-only and path-based.
  - Packs do not own core recommendation semantics.
  - Provider and adapter seams remain inactive until formally admitted.
- Dependencies: Phase 1 contract closure; Phase 3 provenance design for pack fingerprints.
- Validation gates:
  - Pack regression tests
  - Surface-isolation tests
  - Targeted seam-inertness tests
  - Docs lockstep checks
- Rollback concerns: Changes to normalized pack output must remain additive and preserve current pack fixtures as compatibility examples.
- Estimated PR waves: 2 to 3 PRs across `WP-13` to `WP-15`
- Execution note: `WP-13`, `WP-14`, and `WP-15` completed on `2026-04-13`; pack paths/source fingerprints are canonicalized, pack `fatal_gates` are explicitly documented and regression-tested as advisory-only, and provider/adapter seams now require explicit docs-and-tests admission before any future activation.
- Explicitly out of scope:
  - New provider integrations
  - Pack marketplace or discovery service
  - Networked pack loading
- Counterpoint: The repo already keeps packs explicit, so more hardening may be unnecessary.
- Resolution: Raw path handling, `sys.path` mutation, and ambiguous pack gate naming show the current seam is disciplined but not yet fully hardened.

## Phase 6. Migration, Extension, and Release Readiness Hardening

- Objective: Align published docs, migration doctrine, packaging, and release checks with the hardened runtime and benchmark surfaces.
- Why this phase comes now: Docs and release truth should be finalized after the runtime, benchmark, provenance, and extension seams are stable.
- Workstreams:
  - Correct public docs to match actual manifest layout and holdout behavior.
  - Add release/package truth-surface lock tests.
  - Tighten migration and extension doctrine inside existing policy docs.
- Affected files and directories: `README.md`, `benchmarks/goldset/README.md`, `docs/{SPEC_IMPLEMENTATION_MATRIX.md,BENCHMARK_POLICY.md,DEVELOPMENT.md,RELEASE_POLICY.md,MIGRATION_POLICY.md,EXECUTION_MODEL.md,PACK_INTERFACE.md}`, `pyproject.toml`, `setup.py`, `scripts/build_release.py`, `.github/workflows/ci.yml`
- Preserved invariants:
  - Package remains `apr-v2`.
  - Supported primary CLI remains `apr`.
  - Active contract and canonical-record supremacy remain explicit.
- Dependencies: Earlier phases, especially validation/docs lockstep and seam hardening.
- Validation gates:
  - Docs lockstep tests
  - Contract and goldset validation scripts
  - Release smoke from a clean tree
  - CI parity check
- Rollback concerns: Public docs may temporarily describe mixed branch states if release-truth updates and runtime hardening are merged separately.
- Estimated PR waves: `WP-16` completed on `2026-04-09`; `WP-17` and `WP-18` completed on `2026-04-13`
- Explicitly out of scope:
  - Legacy runtime loading
  - Service deployment plans
  - New extension surfaces beyond the current repo boundary
- Counterpoint: Docs-only work can wait until all runtime hardening is finished.
- Resolution: Current repo-proven docs drift already changes operator understanding, so public truth surfaces need an explicit closing phase rather than opportunistic cleanup.
- Execution note: `WP-16` landed as a docs-only truthfulness sweep in `README.md`, `benchmarks/goldset/README.md`, `benchmarks/goldset/holdout/README.md`, and `docs/SPEC_IMPLEMENTATION_MATRIX.md`; `WP-17` landed via `tests/regression/test_release_contract.py` plus the existing release/readiness docs, and `WP-18` landed via the extension-governance lockstep coverage in `tests/regression/test_surface_isolation.py`.
