# APR v2 Hardening Work Packages

## WP-01 Contract Taxonomy Lockstep Guard

- Phase: `Phase 1`
- Problem statement: Article, claim, outlet, domain, recommendation, and processing-state taxonomies are duplicated across policy, runtime, schema, benchmark code, and tests.
- Confirmed repo context: `contracts/active/policy_layer.yaml` carries taxonomies; `src/apr_core/classify/classification.py`, `src/apr_core/pipeline.py`, and `src/apr_core/goldset/runner.py` hard-code related state sets; `scripts/validate_contract.py` now validates ordered taxonomy parity across the fixed policy/runtime/schema namespaces.
- Exact files to inspect or modify later: `contracts/active/policy_layer.yaml`, `contracts/active/canonical_audit_record.schema.json`, `src/apr_core/classify/classification.py`, `src/apr_core/pipeline.py`, `src/apr_core/goldset/runner.py`, `scripts/validate_contract.py`, `tests/contract/test_contract_manifest.py`
- Why the work package exists: This is the lowest-risk path to fail closed on contract drift before broader hardening lands.
- Prerequisites: `none`
- Recommended PR batch order: `1`
- Acceptance criteria: Validation fails when fixed taxonomies diverge; no recommendation behavior changes; authoritative source order remains contract-first.
- Tests to add or update: `tests/contract/test_contract_manifest.py`; add a focused policy/runtime lockstep test under `tests/contract/`.
- Failure modes to watch: Accidentally importing benchmark-only enums into runtime policy; broad refactors that obscure authority order.
- Overreach risks: Replacing contract surfaces with generated Python constants instead of validating them.
- Invariant constraints: Keep `contracts/active/` authoritative; keep `CanonicalAuditRecord` canonical; keep benchmark semantics separate from live runtime.
- Done definition: Contract validation explicitly covers taxonomy parity and the docs name the lockstep rule.
- Confidence: `high`
- Blocked-by fields: `none`
- Enables fields: `WP-02`, `WP-03`, `WP-04`, `WP-05`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `scripts/validate_contract.py` already enforced policy/runtime/schema taxonomy parity for article, claim, domain, outlet, processing-state, and canonical recommendation surfaces; this pass tightened recommendation-state validation from set membership to ordered lockstep and `tests/contract/test_contract_manifest.py::test_runtime_taxonomies_remain_in_lockstep_with_policy_layer` now explicitly locks the recommendation namespace alongside the other policy/runtime taxonomies.

## WP-02 Canonical Schema Closure for Fixed Semantic Fields

- Phase: `Phase 1`
- Problem statement: The canonical schema is closed at the top level but still permits unconstrained strings for several fixed semantic fields.
- Confirmed repo context: `classification.article_type`, `classification.claim_type`, `classification.outlet_profile`, `classification.domain_module`, and `venue.routing_state` are fixed in runtime behavior but not fully constrained in `contracts/active/canonical_audit_record.schema.json`.
- Exact files to inspect or modify later: `contracts/active/canonical_audit_record.schema.json`, `src/apr_core/classify/classification.py`, `src/apr_core/venue/routing.py`, `docs/CANONICAL_AUDIT_RECORD.md`, `tests/contract/test_active_schemas.py`, `tests/surface_lock/test_output_surfaces.py`
- Why the work package exists: Schema-valid output should imply semantic namespace validity for fixed canonical fields.
- Prerequisites: `WP-01`
- Recommended PR batch order: `2`
- Acceptance criteria: Fixed semantic fields are enum-closed or otherwise fail closed; contract docs and surface-lock tests are updated intentionally.
- Tests to add or update: `tests/contract/test_active_schemas.py`, `tests/surface_lock/test_output_surfaces.py`, `tests/regression/test_minimal_pipeline.py`
- Failure modes to watch: Tightening a field whose runtime semantics are still intentionally open; breaking existing fixtures without coordinated updates.
- Overreach risks: Encoding benchmark-only or future-extension vocabularies into the runtime canonical schema.
- Invariant constraints: Additive migration only; no change to canonical record supremacy.
- Done definition: Canonical schema closure is explicit, validated, and reflected in docs/tests.
- Confidence: `high`
- Blocked-by fields: `WP-01`
- Enables fields: `WP-07`, `WP-10`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `contracts/active/canonical_audit_record.schema.json` already enum-closes `classification.article_type`, `classification.claim_type`, `classification.outlet_profile`, `classification.domain_module`, and `venue.routing_state`; `tests/contract/test_active_schemas.py::test_canonical_schema_closes_runtime_classification_and_routing_vocabularies` now locks those schema enums to the runtime vocabularies in `src/apr_core/classify/classification.py` and `src/apr_core/venue/routing.py`.

## WP-03 Processing-State and Renderer-Boundary Clarification

- Phase: `Phase 1`
- Problem statement: Rendering is downstream of `run_audit()`, so canonical provenance and renderer-boundary docs must stay explicit about where audit processing stops.
- Confirmed repo context: `contracts/active/policy_layer.yaml` now stops at `PACKS_EXECUTED`; `src/apr_core/pipeline.py` provenance ends at `PACKS_EXECUTED`; `src/apr_core/render/markdown.py` is a separate formatter.
- Exact files to inspect or modify later: `contracts/active/policy_layer.yaml`, `src/apr_core/pipeline.py`, `src/apr_core/render/markdown.py`, `docs/{ARCHITECTURE.md,EXECUTION_MODEL.md,CANONICAL_AUDIT_RECORD.md}`, `tests/surface_lock/test_output_surfaces.py`
- Why the work package exists: Replay and provenance semantics must distinguish audit completion from downstream rendering.
- Prerequisites: `WP-01`
- Recommended PR batch order: `2`
- Acceptance criteria: Audit-stage and render-stage state semantics are explicit and consistent across policy, runtime, docs, and tests.
- Tests to add or update: Surface-lock tests and a targeted provenance-state test under `tests/regression/`.
- Failure modes to watch: Letting renderer activity mutate canonical provenance retroactively.
- Overreach risks: Creating a second source of truth in the renderer layer.
- Invariant constraints: Renderers remain downstream consumers only.
- Done definition: No remaining ambiguity about whether `RENDERED` belongs inside canonical audit provenance.
- Confidence: `medium`
- Blocked-by fields: `WP-01`
- Enables fields: `WP-07`, `WP-12`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `tests/contract/test_contract_manifest.py::test_runtime_taxonomies_remain_in_lockstep_with_policy_layer` and `::test_canonical_schema_closes_fixed_classification_and_routing_enums` now prove policy/runtime/schema alignment on processing states, while `docs/CANONICAL_AUDIT_RECORD.md`, `docs/ARCHITECTURE.md`, and `docs/EXECUTION_MODEL.md` all state that canonical provenance stops at `PACKS_EXECUTED` and rendering remains downstream-only.

## WP-04 Benchmark Manifest / Active Contract Parity Guard

- Phase: `Phase 2`
- Problem statement: Benchmark manifests match the active contract today only by convention.
- Confirmed repo context: Both benchmark manifests declare `contract_version: 2.1.0`, but `benchmarks/goldset/schemas/manifest.schema.json` types it only as string and `scripts/validate_goldset.py` does not compare it to `contracts/active/manifest.yaml`.
- Exact files to inspect or modify later: `benchmarks/goldset_dev/manifest.yaml`, `benchmarks/goldset_holdout/manifest.yaml`, `benchmarks/goldset/schemas/manifest.schema.json`, `scripts/validate_goldset.py`, `src/apr_core/goldset/runner.py`, `tests/goldset/test_goldset_runner.py`
- Why the work package exists: Benchmark governance must fail fast if it stops targeting the active runtime contract.
- Prerequisites: `none`
- Recommended PR batch order: `1`
- Acceptance criteria: Benchmark validation fails on manifest/active-contract mismatch; dev and holdout manifests remain aligned with the active contract; no live runtime behavior change.
- Tests to add or update: `tests/goldset/test_goldset_runner.py`; add a negative parity test under `tests/goldset/`.
- Failure modes to watch: Accidentally treating benchmark manifests as runtime-loadable contracts.
- Overreach risks: Coupling benchmark evolution too tightly to release cadence without clear docs.
- Invariant constraints: Benchmark surfaces remain benchmark-only; active contract remains the only runtime-loaded contract.
- Done definition: Goldset validation explicitly enforces contract-version parity.
- Confidence: `high`
- Blocked-by fields: `none`
- Enables fields: `WP-05`, `WP-06`, `WP-08`, `WP-16`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `src/apr_core/goldset/runner.py` enforces `_assert_manifest_contract_parity()` inside `validate_goldset_manifest()`; `tests/goldset/test_goldset_runner.py::test_goldset_manifest_must_match_active_contract_version` and `tests/regression/test_cli_smoke.py::test_validate_goldset_script_fails_on_contract_version_drift` now cover both the runner path and the `scripts/validate_goldset.py` entrypoint.

## WP-05 Unified Validation Matrix and Repo Lockstep Gate

- Phase: `Phase 2`
- Problem statement: Validation exists, but it is spread across scripts, CI steps, and tests, which allowed docs drift to survive.
- Confirmed repo context: `.github/workflows/ci.yml` runs contract validation, goldset validation, pytest, and CLI benchmark runs; `Makefile` and `docs/DEVELOPMENT.md` expose parts of this, but there is no single explicit lockstep matrix.
- Exact files to inspect or modify later: `.github/workflows/ci.yml`, `Makefile`, `docs/DEVELOPMENT.md`, `scripts/validate_contract.py`, `scripts/validate_goldset.py`, `tests/`, `docs/hardening/APR_V2_HARDENING_VALIDATION_MATRIX.md`
- Why the work package exists: Hardening execution needs one conservative validation contract rather than distributed assumptions.
- Prerequisites: `WP-01`, `WP-04`
- Recommended PR batch order: `3`
- Acceptance criteria: There is one explicit repo-level validation path documented and enforced; docs truth checks are part of that path.
- Tests to add or update: Add docs lockstep tests and CI assertions that call the new or updated unified validation entrypoint.
- Failure modes to watch: Creating a validation wrapper that is weaker than the current CI path.
- Overreach risks: Adding slow or redundant validation that duplicates existing jobs without new signal.
- Invariant constraints: Use the smallest sufficient gate first, then stronger gates only where impact warrants.
- Done definition: Developers can point to one authoritative validation matrix and one repo-level lockstep entrypoint.
- Confidence: `medium`
- Blocked-by fields: `WP-01`, `WP-04`
- Enables fields: `WP-16`, `WP-17`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `scripts/validate_repo_lockstep.py` is the repo-level lockstep entrypoint, it is wired into `.github/workflows/ci.yml`, `Makefile`, and `docs/DEVELOPMENT.md`, and `tests/regression/test_repo_lockstep.py::test_validate_repo_lockstep_script_passes` now proves the entrypoint succeeds end-to-end.

## WP-06 Holdout Truthfulness and Split-Isolation Hardening

- Phase: `Phase 2`
- Problem statement: The code and authoritative docs now agree that holdout is active, but that truth is not yet protected by an explicit lockstep gate and split-isolation package.
- Confirmed repo context: `benchmarks/goldset_holdout/manifest.yaml` has 3 active holdout cases; holdout-specific tests already exist in `tests/goldset/`; `run_goldset_manifest()` isolates holdout baselines; the authoritative docs were reconciled on 2026-04-09.
- Exact files to inspect or modify later: `benchmarks/goldset_holdout/manifest.yaml`, `benchmarks/goldset/README.md`, `docs/{BENCHMARK_POLICY.md,SPEC_IMPLEMENTATION_MATRIX.md,README.md}`, `tests/goldset/{test_holdout_leakage.py,test_holdout_split_isolation.py}`, `tests/regression/test_cli_smoke.py`
- Why the work package exists: Holdout governance must stay truthful and stable after the initial docs correction, especially before any later replay/provenance claims are trusted.
- Prerequisites: `WP-04`
- Recommended PR batch order: `3`
- Acceptance criteria: Holdout docs, manifests, and validation language all agree on active blind-holdout behavior; split isolation remains tested.
- Tests to add or update: Existing holdout leakage and split-isolation tests; targeted docs lockstep checks.
- Failure modes to watch: Accidentally exposing expected holdout surfaces while clarifying the docs.
- Overreach risks: Expanding holdout data or methodology instead of tightening truth surfaces.
- Invariant constraints: Holdout remains blind, isolated, and benchmark-only.
- Done definition: No remaining repo docs claim that holdout is absent when active holdout cases exist.
- Confidence: `high`
- Blocked-by fields: `WP-04`
- Enables fields: `WP-08`, `WP-16`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `tests/goldset/test_holdout_leakage.py`, `tests/goldset/test_holdout_split_isolation.py`, and `tests/regression/test_cli_smoke.py::test_goldset_holdout_eval_cli_smoke` now cover blind-holdout masking, development-vs-holdout history isolation, authoritative holdout-doc truth, and CLI-level holdout redaction behavior.

## WP-07 Canonical Provenance Fingerprint Expansion

- Phase: `Phase 3`
- Problem statement: Canonical provenance is too thin for reliable replay and audit reconstruction.
- Confirmed repo context: `src/apr_core/pipeline.py` now records deterministic provenance fingerprints including normalized-input, contract, policy, schema, runtime-identity, and loaded-pack metadata.
- Exact files to inspect or modify later: `src/apr_core/pipeline.py`, `src/apr_core/models.py`, `contracts/active/canonical_audit_record.schema.json`, `docs/CANONICAL_AUDIT_RECORD.md`, `tests/surface_lock/test_output_surfaces.py`, `tests/regression/test_minimal_pipeline.py`
- Why the work package exists: Hardening needs deterministic replay evidence attached to the canonical truth object itself.
- Prerequisites: `WP-02`, `WP-03`
- Recommended PR batch order: `4`
- Acceptance criteria: Canonical provenance includes deterministic replay fingerprints for local runtime surfaces without changing recommendation outcomes.
- Tests to add or update: Surface-lock tests, minimal-pipeline tests, and a provenance-focused regression test.
- Failure modes to watch: Adding non-deterministic or environment-dependent provenance fields.
- Overreach risks: Polluting the live runtime record with benchmark-only metadata.
- Invariant constraints: `CanonicalAuditRecord` remains the only runtime truth object; fields must stay local-first and deterministic.
- Done definition: A canonical record carries enough information to tie output back to normalized input and local runtime identity.
- Confidence: `medium`
- Blocked-by fields: `WP-02`, `WP-03`
- Enables fields: `WP-08`, `WP-10`, `WP-13`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `src/apr_core/pipeline.py` now emits `normalized_input_sha256`, `contract_manifest_sha256`, `policy_layer_sha256`, `canonical_schema_sha256`, `runtime_identity`, and `loaded_pack_fingerprints`; `tests/surface_lock/test_output_surfaces.py` and `tests/regression/test_trace_stability.py` both pass against that expanded canonical provenance surface.

## WP-08 Benchmark Summary / Ledger Replay Envelope

- Phase: `Phase 3`
- Problem statement: Goldset outputs are rich, but replay metadata is still not a fully closed contract surface.
- Confirmed repo context: `src/apr_core/goldset/runner.py` already records manifest hash, governance, gates, and some git metadata; ledger schema validates these rows.
- Exact files to inspect or modify later: `src/apr_core/goldset/runner.py`, `benchmarks/goldset/schemas/{summary.schema.json,ledger_entry.schema.json}`, `scripts/validate_goldset.py`, `tests/goldset/test_goldset_runner.py`, `tests/goldset/test_holdout_split_isolation.py`
- Why the work package exists: Regression diagnosis should be reconstructable from durable benchmark artifacts without rereading code.
- Prerequisites: `WP-04`, `WP-07`
- Recommended PR batch order: `5`
- Acceptance criteria: Summary and ledger surfaces capture enough replay metadata to reconstruct run context, while public holdout outputs remain blinded.
- Tests to add or update: Goldset runner tests, holdout split-isolation tests, ledger schema validation tests.
- Failure modes to watch: Leaking holdout-sensitive details into public summaries.
- Overreach risks: Copying benchmark-only replay metadata into the canonical runtime record.
- Invariant constraints: Benchmark governance remains additive and separate from live runtime semantics.
- Done definition: A benchmark run can be replayed or compared using only manifest, summary, ledger, and source repo state.
- Confidence: `medium`
- Blocked-by fields: `WP-04`, `WP-07`
- Enables fields: `WP-09`, `WP-11`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `src/apr_core/goldset/runner.py` already emits `manifest_path`, `manifest_sha256`, active contract/policy/schema digests, `runtime_identity`, `repo_state`, `prior_run`, and `calibration_ledger` in the summary and mirrors the replay envelope into `build_goldset_ledger_entry()`; `tests/goldset/test_goldset_runner.py::test_goldset_summary_and_ledger_capture_replay_envelope` now locks that contract, while existing holdout redaction and split-isolation coverage continues to prove public holdout outputs stay blinded.

## WP-09 Failure-Class and Reason-Code Closure

- Phase: `Phase 3`
- Problem statement: Failure classes and governance reason codes behave like contracts but are spread across code, schemas, and tests as free strings.
- Confirmed repo context: `src/apr_core/goldset/runner.py` defines error-class maps and bins; `src/apr_core/goldset/governance/governance_router.py` exports reason codes; schemas carry related surfaces.
- Exact files to inspect or modify later: `src/apr_core/goldset/runner.py`, `src/apr_core/goldset/governance/governance_router.py`, `benchmarks/goldset/schemas/{summary.schema.json,ledger_entry.schema.json}`, `docs/BENCHMARK_POLICY.md`, `tests/adversarial/`, `tests/goldset/`
- Why the work package exists: Hardening claims about drift and governance are only as strong as the stability of the failure taxonomy they rely on.
- Prerequisites: `WP-08`
- Recommended PR batch order: `6`
- Acceptance criteria: Stable failure/reason-code namespaces are explicitly enumerated or otherwise validated across runtime, schemas, and docs.
- Tests to add or update: Goldset runner tests, adversarial matrix tests, metric-reporting tests, schema-contract tests.
- Failure modes to watch: Freezing experimental or optional reason codes too early.
- Overreach risks: Treating benchmark-only taxonomy closure as a live runtime contract change.
- Invariant constraints: Failure-taxonomy hardening must not alter live runtime recommendation semantics.
- Done definition: Benchmark failure classes and governance reason codes have an explicit, testable contract.
- Confidence: `medium`
- Blocked-by fields: `WP-08`
- Enables fields: `WP-11`, `WP-17`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `src/apr_core/goldset/runner.py` already centralizes `KNOWN_GOLDSET_ERROR_CLASSES` and `GOVERNANCE_REASON_CODES`, validates them through `_validate_summary()` and `_append_ledger_entry()`, and rejects unknown namespaces before durable artifact emission; `tests/goldset/test_goldset_runner.py::test_goldset_summary_rejects_unknown_failure_and_reason_namespaces` plus `::test_goldset_ledger_append_rejects_unknown_failure_and_reason_namespaces` now lock both summary and ledger enforcement, while `tests/adversarial/test_matrix.py` and `tests/adversarial/test_metric_reporting.py` continue to exercise the emitted governance-report surface.

## WP-10 Atomic Canonical JSON and Markdown Writes

- Phase: `Phase 4`
- Problem statement: Direct writes can leave partial files if the process is interrupted mid-write.
- Confirmed repo context: `src/apr_core/utils.py` already routes canonical JSON and markdown persistence through `_atomic_write_text()` and `write_text_bundle()`; `src/apr_core/cli.py` uses those helpers for audit, render, defense, question, and bundled goldset output surfaces.
- Exact files to inspect or modify later: `src/apr_core/utils.py`, `src/apr_core/cli.py`, `tests/regression/test_cli_smoke.py`, targeted tempdir write-integrity tests under `tests/regression/`
- Why the work package exists: Canonical records and rendered reports are user-facing durable artifacts and should be all-or-nothing writes.
- Prerequisites: `WP-07`
- Recommended PR batch order: `7`
- Acceptance criteria: Canonical JSON and markdown writes are atomic on the supported local filesystem path model.
- Tests to add or update: CLI smoke tests plus targeted tempdir atomic-write tests.
- Failure modes to watch: Cross-platform rename semantics or leftover temp files on failure.
- Overreach risks: Introducing external locking or service-backed storage.
- Invariant constraints: Keep local filesystem output only; preserve current output path semantics.
- Done definition: Interrupted writes cannot leave truncated canonical or markdown artifacts at the target path.
- Confidence: `medium`
- Blocked-by fields: `WP-07`
- Enables fields: `WP-11`, `WP-12`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `src/apr_core/utils.py` already provided `_atomic_write_text()`, `write_json()`, `write_text()`, and `write_text_bundle()`; `tests/regression/test_atomic_writes.py` now proves JSON writes, markdown writes, and multi-file bundle writes preserve the previous on-disk state when replacement fails, and existing CLI smoke coverage continues to exercise the public audit/render/goldset write paths.

## WP-11 Crash-Safe Summary and Ledger Emission

- Phase: `Phase 4`
- Problem statement: Goldset summary JSON, governance report JSON, and JSONL ledger append are not emitted as a cohesive crash-safe unit.
- Confirmed repo context: `cmd_goldset()` now snapshots existing summary, governance-report, and ledger outputs, writes the final summary/report bundle once, and restores the old-good state if ledger append fails; `_append_ledger_entry()` still uses atomic JSONL replacement in `src/apr_core/goldset/runner.py`.
- Exact files to inspect or modify later: `src/apr_core/cli.py`, `src/apr_core/goldset/runner.py`, `src/apr_core/utils.py`, `tests/goldset/test_goldset_runner.py`, `tests/regression/test_cli_smoke.py`
- Why the work package exists: Benchmark governance artifacts should never be partially written or internally inconsistent after interruption.
- Prerequisites: `WP-08`, `WP-10`
- Recommended PR batch order: `8`
- Acceptance criteria: Summary, governance report, and ledger persistence have documented failure semantics and targeted tests; old-good state remains intact on write failure.
- Tests to add or update: Goldset runner tempdir tests, CLI smoke tests, ledger replay tests.
- Failure modes to watch: Appending a ledger row for a summary that was not durably written, or vice versa.
- Overreach risks: Over-engineering local writes into a transaction manager.
- Invariant constraints: Keep JSON summary plus JSONL ledger model; do not introduce databases or services.
- Done definition: Goldset output persistence is crash-safe and consistent at the repo’s local-first scale.
- Confidence: `medium`
- Blocked-by fields: `WP-08`, `WP-10`
- Enables fields: `WP-12`, `WP-17`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `src/apr_core/cli.py::cmd_goldset` now emits the final summary/governance bundle once, snapshots prior summary/governance/ledger contents before append, and restores those files if `append_goldset_ledger_entry()` fails; `tests/regression/test_atomic_writes.py::test_cmd_goldset_restores_previous_outputs_when_ledger_append_fails` locks the rollback path, while existing CLI smoke and `python scripts/validate_goldset.py` continue to validate the successful path.

## WP-12 Doctor / Readiness Split

- Phase: `Phase 4`
- Problem statement: Hardening docs and tests still described `apr doctor` as a mixed runtime/readiness failure path even though the CLI had already split the semantics.
- Confirmed repo context: `cmd_doctor()` returns `_doctor_report()` as-is and stays successful when `git_status` is `dirty`; `cmd_readiness()` reuses the same report but fail-closes with `reason=release_readiness_requires_clean_worktree` when the worktree is not clean.
- Exact files to inspect or modify later: `src/apr_core/cli.py`, `scripts/build_release.py`, `docs/{DEVELOPMENT.md,RELEASE_POLICY.md}`, `tests/regression/test_cli_smoke.py`
- Why the work package exists: Hardening should separate “runtime wiring is broken” from “release/readiness policy is not satisfied”.
- Prerequisites: `WP-10`, `WP-11`
- Recommended PR batch order: `9`
- Acceptance criteria: Runtime validation and release-readiness semantics are clearly distinguishable without weakening clean-tree release policy.
- Tests to add or update: CLI smoke tests plus direct command-level regressions around dirty-worktree doctor/readiness behavior.
- Failure modes to watch: Accidentally weakening release clean-tree enforcement or confusing existing operators.
- Overreach risks: Turning `doctor` into a full repository-management command.
- Invariant constraints: Release builds must still require clean-tree conditions where policy says they do.
- Done definition: Operator-facing docs and CLI behavior distinguish runtime health from release readiness.
- Confidence: `medium`
- Blocked-by fields: `WP-10`, `WP-11`
- Enables fields: `WP-17`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `src/apr_core/cli.py` already exposed the split through `cmd_doctor()` and `cmd_readiness()`; `tests/regression/test_cli_smoke.py::test_doctor_command_reports_dirty_git_without_failing` and `::test_readiness_command_rejects_dirty_git` now lock the distinction directly, while `docs/DEVELOPMENT.md` and `docs/RELEASE_POLICY.md` remain aligned with the implemented behavior.

## WP-13 Pack Path Canonicalization and Source Identity Capture

- Phase: `Phase 5`
- Problem statement: Pack loading is explicit but path normalization and provenance capture are looser than the repo’s trust boundary doctrine suggests.
- Confirmed repo context: `src/apr_core/packs/loader.py` accepts raw paths, resolves `pack.yaml`, mutates `sys.path`, and records pack metadata without canonical path or digest capture.
- Exact files to inspect or modify later: `src/apr_core/packs/loader.py`, `src/apr_core/packs/protocol.py`, `src/apr_core/pipeline.py`, `docs/PACK_INTERFACE.md`, `tests/regression/test_pack_loading.py`, fixture-pack smoke tests
- Superseding note (`2026-04-13`): the live loader already canonicalizes and dedupes requested pack roots through `_canonical_pack_request()` / `_canonical_requested_paths()`, records `manifest_path` and `manifest_sha256`, and `src/apr_core/pipeline.py` emits those identities under `provenance.loaded_pack_fingerprints`.
- Why the work package exists: Pack provenance and trust boundaries should be explicit enough to remain advisory and reproducible.
- Prerequisites: `WP-07`
- Recommended PR batch order: `10`
- Acceptance criteria: Pack requests are canonicalized, deduped, and their source identity is recorded deterministically; no recommendation semantics change.
- Tests to add or update: Pack-loading regression tests and targeted path-normalization tests.
- Failure modes to watch: Breaking current fixture-pack path conventions or relative-path ergonomics without a replacement.
- Overreach risks: Converting packs into installed-package discovery instead of path-based extension.
- Invariant constraints: Packs remain explicit path-based advisory extensions.
- Done definition: Pack load provenance is deterministic and path handling is conservative.
- Confidence: `medium`
- Blocked-by fields: `WP-07`
- Enables fields: `WP-14`, `WP-18`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `tests/regression/test_pack_loading.py::test_advisory_pack_loads_and_records_scoped_output` already locks canonicalized `requested_pack_paths`, resolved manifest paths, and `provenance.loaded_pack_fingerprints.resolved_repo_root`; `tests/surface_lock/test_output_surfaces.py` also locks pack fingerprint shape and `manifest_sha256` parity with `pack_execution.loaded_packs`.

## WP-14 Pack Advisory Semantics Clarification

- Phase: `Phase 5`
- Problem statement: Current docs and normalized output can be read as if pack `fatal_gates` have stronger authority than the runtime actually grants them.
- Confirmed repo context: Pack outputs include `fatal_gates`, but `_decision_from_states()` uses pack results for confidence/escalation context rather than core fatal overrides.
- Exact files to inspect or modify later: `docs/PACK_INTERFACE.md`, `src/apr_core/packs/loader.py`, `src/apr_core/pipeline.py`, `contracts/active/canonical_audit_record.schema.json`, `tests/regression/test_pack_loading.py`, `tests/surface_lock/test_output_surfaces.py`
- Why the work package exists: Pack restraint is a hard architectural invariant and needs sharper naming, documentation, and tests.
- Prerequisites: `WP-13`
- Recommended PR batch order: `11`
- Acceptance criteria: Pack gate and escalation language is unambiguous in docs, normalized output, and tests; packs remain advisory.
- Tests to add or update: Pack regression tests, output-surface locks, any pack-result schema tests.
- Failure modes to watch: Accidentally promoting pack fatal-gate requests into core recommendation ownership.
- Overreach risks: Renaming fields in ways that break pack compatibility without migration handling.
- Invariant constraints: Packs must not rewrite core recommendation semantics.
- Done definition: A new contributor cannot reasonably confuse pack requests with core decision authority after reading the docs and tests.
- Confidence: `medium`
- Blocked-by fields: `WP-13`
- Enables fields: `WP-18`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `src/apr_core/packs/loader.py::_normalize_fatal_gates()` now constrains pack gate scopes to the schema-backed advisory enums, `docs/PACK_INTERFACE.md` and `docs/CANONICAL_AUDIT_RECORD.md` say `pack_results[*].fatal_gates` are advisory pack requests only and do not participate in core recommendation selection, and `tests/regression/test_pack_loading.py::test_physics_pack_fatal_gates_remain_advisory_requests` locks the non-empty physics-pack `fatal_gates` case while proving the core recommendation remains unchanged.

## WP-15 Provider / Adapter Seam Quarantine and Admission Criteria

- Phase: `Phase 5`
- Problem statement: Dormant seams exist, but the repo does not yet enforce or test their inertness explicitly.
- Confirmed repo context: `src/apr_core/providers/protocol.py` defines a future provider protocol; `src/apr_core/adapters/__init__.py` explicitly says adapters are reserved and runtime is deterministic and local.
- Exact files to inspect or modify later: `src/apr_core/providers/{__init__.py,protocol.py}`, `src/apr_core/adapters/__init__.py`, `docs/{EXECUTION_MODEL.md,MIGRATION_POLICY.md}`, targeted seam tests under `tests/regression/`
- Why the work package exists: The highest-risk future seam is non-local provider or adapter activation without explicit admission criteria.
- Prerequisites: `none`
- Recommended PR batch order: `10`
- Acceptance criteria: Existing docs and tests prove providers and adapters are inert until an explicit admission process changes that fact.
- Tests to add or update: Targeted seam-inertness tests; import and CLI non-usage checks.
- Failure modes to watch: Accidentally wiring placeholders into CLI or pipeline paths while adding tests or docs.
- Overreach risks: Designing future provider APIs instead of constraining current dormant seams.
- Invariant constraints: Keep the runtime deterministic and local-first.
- Done definition: Provider and adapter seams are explicitly quarantined by docs and tests.
- Confidence: `high`
- Blocked-by fields: `none`
- Enables fields: `WP-18`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `docs/EXECUTION_MODEL.md` and `docs/MIGRATION_POLICY.md` now require any future provider/adapter admission to be explicit in doctrine docs and validation before code activation, and `tests/regression/test_surface_isolation.py::test_extension_governance_docs_remain_in_lockstep_with_repo_boundary` plus `::test_provider_and_adapter_seams_remain_dormant_in_active_runtime` lock both the admission text and the active-runtime absence proof.

## WP-16 Docs Truthfulness Sweep for Manifest and Holdout Surfaces

- Phase: `Phase 6`
- Problem statement: Public docs are stale on manifest location and holdout state even though the code and tests already moved forward.
- Confirmed repo context: `README.md`, `benchmarks/goldset/README.md`, and `docs/SPEC_IMPLEMENTATION_MATRIX.md` conflict with current active manifest layout and holdout status.
- Exact files to inspect or modify later: `README.md`, `benchmarks/goldset/README.md`, `benchmarks/goldset/holdout/README.md`, `docs/{SPEC_IMPLEMENTATION_MATRIX.md,BENCHMARK_POLICY.md,DEVELOPMENT.md}`, `benchmarks/goldset_dev/manifest.yaml`, `benchmarks/goldset_holdout/manifest.yaml`
- Why the work package exists: This is the safest high-signal PR because it corrects confirmed drift without touching runtime semantics.
- Prerequisites: `none`
- Recommended PR batch order: `1`
- Acceptance criteria: Public docs accurately describe benchmark manifests, holdout behavior, and authority order for benchmark docs.
- Tests to add or update: Add or extend docs lockstep tests.
- Failure modes to watch: Accidentally exposing holdout expectations while fixing terminology.
- Overreach risks: Slipping runtime or benchmark behavior changes into what should be a docs-truthfulness PR.
- Invariant constraints: Prefer documentation correction over runtime change where behavior is already coherent.
- Done definition: No reviewed public doc still points operators at removed manifest paths or inactive-holdout language.
- Confidence: `high`
- Blocked-by fields: `none`
- Enables fields: `WP-05`, `WP-06`, `WP-17`
- Execution status: `completed` on `2026-04-09`
- Execution evidence: Updated `README.md`, `benchmarks/goldset/README.md`, `benchmarks/goldset/holdout/README.md`, and `docs/SPEC_IMPLEMENTATION_MATRIX.md`; targeted stale-reference scan returned no remaining matches in those authoritative docs.

## WP-17 Release / Package Truthfulness and Lock Tests

- Phase: `Phase 6`
- Problem statement: Package identity, version source, CLI exposure, and release bundle truth live in several places and need explicit lockstep checks.
- Confirmed repo context: `pyproject.toml` names `apr-v2` and exposes multiple console scripts; `setup.py` reads version from the active manifest; `scripts/build_release.py` enforces clean-tree release builds.
- Exact files to inspect or modify later: `pyproject.toml`, `setup.py`, `scripts/build_release.py`, `.github/workflows/ci.yml`, `docs/{RELEASE_POLICY.md,DEVELOPMENT.md}`, targeted release tests under `tests/regression/`
- Why the work package exists: Hardening is incomplete if release/docs/package truth can drift after runtime and benchmark surfaces are locked.
- Prerequisites: `WP-05`, `WP-11`, `WP-12`, `WP-16`
- Recommended PR batch order: `12`
- Acceptance criteria: Version source, primary CLI identity, release exclusions, and clean-tree rules are covered by tests, docs, and CI and remain internally consistent.
- Tests to add or update: Release-surface tests, contract validation, clean-tree release smoke.
- Failure modes to watch: Breaking helper CLI scripts or making release tests impossible to run locally.
- Overreach risks: Treating helper console scripts as unsupported surfaces that must be removed when the repo still uses them.
- Invariant constraints: Preserve package `apr-v2`, primary CLI `apr`, and bootstrap entrypoint `src/apr_core_bootstrap.py`.
- Done definition: Release and package truth surfaces are explicitly tested and documented.
- Confidence: `medium`
- Blocked-by fields: `WP-05`, `WP-11`, `WP-12`, `WP-16`
- Enables fields: `WP-18`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `tests/regression/test_release_contract.py` now locks package identity, bootstrap entrypoint, manifest-sourced versioning, and release-bundle exclusions; `docs/RELEASE_POLICY.md` and `docs/DEVELOPMENT.md` already describe the same clean-tree release and readiness split.

## WP-18 Migration and Extension Governance Tightening

- Phase: `Phase 6`
- Problem statement: Existing migration and extension docs declare strong intent, but the repo lacks a fully tightened handoff story for future packs, adapters, and provider-like extensions.
- Confirmed repo context: `docs/MIGRATION_POLICY.md` rejects silent legacy inheritance; `docs/PACK_INTERFACE.md` defines pack restraint; provider and adapter seams are dormant placeholders.
- Exact files to inspect or modify later: `docs/{MIGRATION_POLICY.md,PACK_INTERFACE.md,EXECUTION_MODEL.md,REPO_CHARTER.md}`, `src/apr_core/packs/loader.py`, `src/apr_core/providers/`, `src/apr_core/adapters/`
- Why the work package exists: After the runtime and release surfaces are hardened, the repo still needs a clear conservative path for future extensions.
- Prerequisites: `WP-13`, `WP-14`, `WP-15`, `WP-17`
- Recommended PR batch order: `13`
- Acceptance criteria: Existing policy docs describe explicit admission rules for future extensions without enabling them prematurely.
- Tests to add or update: Docs lockstep tests and seam-inertness tests needed to keep future extensions dormant.
- Failure modes to watch: Turning planning doctrine into an implicit promise to support live providers or legacy adapters now.
- Overreach risks: Creating speculative infrastructure plans not proved by the current repo.
- Invariant constraints: No databases, queues, services, or live provider integrations unless the repo explicitly admits them in a later change.
- Done definition: Extension and migration doctrine is conservative, explicit, and aligned with the hardened repo boundary.
- Confidence: `medium`
- Blocked-by fields: `WP-13`, `WP-14`, `WP-15`, `WP-17`
- Enables fields: `none`
- Execution status: `completed` on `2026-04-13`
- Execution evidence: `tests/regression/test_surface_isolation.py::test_extension_governance_docs_remain_in_lockstep_with_repo_boundary` now locks the governing extension text in `docs/MIGRATION_POLICY.md`, `docs/PACK_INTERFACE.md`, `docs/EXECUTION_MODEL.md`, and `docs/REPO_CHARTER.md`; the existing seam-dormancy regression remains intact alongside those docs.
