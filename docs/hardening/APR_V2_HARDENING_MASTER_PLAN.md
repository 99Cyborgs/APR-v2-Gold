# APR v2 Hardening Master Plan

## 1. Confirmed Repo Facts

- The reviewed working state is the GitHub branch `codex/full-worktree-publish`; it is ahead of default branch `main` by 4 commits and introduces benchmark-governance surfaces named in this mission.
- The installable package is `apr-v2`, and the supported primary CLI is `apr` via `src/apr_core_bootstrap.py`.
- The live deterministic runtime is `src/apr_core/`, and the only runtime-loaded contract surface is `contracts/active/`.
- `CanonicalAuditRecord` is the only durable runtime truth object; runtime output is schema-validated before return.
- The audit pipeline order is fixed in `src/apr_core/pipeline.py`: input schema validation, normalization, parsing, classification, reviewability, transparency, integrity, structural integrity, calibration, adversarial resilience, scientific-record assessment, venue routing, editorial first pass, rehabilitation planning, advisory pack execution, decision assembly, canonical-record emission.
- Renderers consume canonical output after the runtime decision path; markdown rendering is downstream formatting, not a second semantic engine.
- Packs are explicit path-based advisory extensions; pack execution occurs after core semantics, and pack outputs are normalized into `pack_execution` and `pack_results`.
- Gold-set governance is an active architecture surface. `src/apr_core/goldset/runner.py` validates manifests and schemas, runs dev or holdout evaluation, computes governance reports, and appends calibration-ledger rows.
- The benchmark harness currently uses `benchmarks/goldset_dev/manifest.yaml` for development and `benchmarks/goldset_holdout/manifest.yaml` for holdout. Both declare contract version `2.1.0`.
- The repo has active tests across `tests/contract/`, `tests/regression/`, `tests/goldset/`, `tests/surface_lock/`, and `tests/adversarial/`.
- Baseline validation passed on the reviewed branch for `scripts/validate_contract.py`, `scripts/validate_goldset.py`, and a targeted pytest suite spanning contract, goldset, CLI, and output-surface locks.
- The repo proves no active live provider, network, database, or queue runtime surface in `src/`, `scripts/`, `tests/`, or the active contract set. Providers and adapters exist only as dormant protocol/placeholders.

## 2. Current Architecture Model

### Control flow

1. `apr` enters through `src/apr_core_bootstrap.py`, which delegates to `src/apr_core/cli.py`.
2. `apr audit` and `apr review` call `run_audit()` in `src/apr_core/pipeline.py`.
3. `run_audit()` validates the input against `contracts/active/audit_input.schema.json`, loads the active manifest and policy layer, then executes the fixed semantic stages.
4. Core semantic stages produce `core_record`, after which explicit packs may contribute additive advisory results.
5. `_decision_from_states()` computes recommendation, confidence, and escalation from core states plus pack execution metadata.
6. `CanonicalAuditRecord` is assembled, provenance/rendering metadata are added, and the finished record is validated against `contracts/active/canonical_audit_record.schema.json`.
7. `apr render` validates a canonical record, then formats markdown from that record only.
8. `apr goldset` runs benchmark cases through the same runtime and layers benchmark-only governance, drift, and holdout masking on top of canonical outputs.

### Data flow

- Contract-bound input enters as `NormalizedManuscriptPackage`.
- Runtime transforms visible text surfaces into anchors, claim candidates, classifications, gates, route state, editorial simulation, and rehab plan.
- Canonical output holds the complete runtime truth, including pack execution visibility and downstream rendering hints.
- Benchmark evaluation consumes canonical outputs plus expected case surfaces from manifests, then emits summary JSON and optional JSONL ledger entries.

### Validation boundaries

- Input boundary: schema validation in `pipeline.py`.
- Output boundary: canonical-record schema validation in `pipeline.py`.
- Repo boundary: `scripts/validate_contract.py`, `scripts/validate_goldset.py`, `apr doctor`, and CI.
- Benchmark boundary: manifest, summary, and ledger schemas plus regression suites in `tests/goldset/` and `tests/adversarial/`.
- Output/renderer boundary: surface-lock tests in `tests/surface_lock/`.

### Canonical-output boundary

- `CanonicalAuditRecord` is the only runtime truth object.
- `render/markdown.py` does not redefine field meaning.
- Gold-set evaluation reads canonical output fields and benchmark governance overlays; it does not feed benchmark-only scores back into runtime recommendation semantics.

### Extension boundaries

- Packs: explicit path, explicit manifest, normalized additive output, no core semantic overwrite.
- Providers/adapters: not active; only protocol/placeholder surfaces exist.
- Legacy contracts: archival only under `contracts/legacy/`.

### What is absent

- No proved live network providers.
- No proved databases, queues, or service runtimes.
- No proved cloud execution dependency for the core runtime.
- No proved runtime contract loading outside `contracts/active/`.

## 3. Strong Existing Patterns That Must Be Preserved

- Active-contract supremacy: runtime loads only `contracts/active/`.
- Canonical-record supremacy: downstream consumers read `CanonicalAuditRecord`; they do not replace it.
- Deterministic, local-first execution: no provider/service activation without explicit architectural admission.
- Scientific-record-before-venue ordering: venue mismatch is not scientific invalidity.
- Pack restraint: packs remain explicit, path-based, advisory, and non-owning of core recommendation semantics.
- Benchmark-as-architecture: manifests, schemas, ledgers, and governance reports are first-class, not optional utilities.
- Holdout isolation: holdout masking and separate ledger paths already exist and should be tightened, not removed.
- Release truthfulness: version comes from the active manifest and clean-tree policy is enforced at release build time.

## 4. Counterpoints

- Counterpoint: the fastest way to remove enum drift would be to move all taxonomy authority into Python constants and let docs/contracts follow code.  
  Resolution: reject that direction. Repo doctrine and runtime loader make the active contract authoritative, so hardening should add lockstep validation and schema closure rather than invert authority.
- Counterpoint: benchmark governance is already rich enough that it could become the de facto policy engine for live audits.  
  Resolution: reject that direction. `src/apr_core/goldset/runner.py` explicitly says benchmark surfaces must not widen the live decision contract. Hardening should preserve that separation.
- Counterpoint: provider/adapters could be activated to centralize some heuristics or replay metadata quickly.  
  Resolution: reject that direction. The repo currently proves only dormant seams. Hardening should add admission criteria and inertness checks, not activate non-local behavior.

## 5. Hardening Risk Register Summary

- `HR-01`: taxonomy drift across manifest, policy layer, schema, runtime, and benchmark code.
- `HR-02`: canonical schema under-specifies several semantic nested fields.
- `HR-03`: processing-state duplication leaves `RENDERED` inconsistent with canonical audit provenance.
- `HR-04`: benchmark manifests carry `contract_version` as a free string with no active-contract parity check.
- `HR-05`: docs lockstep risk remains, but the highest-signal authoritative drift on manifest paths and holdout status was corrected on 2026-04-09.
- `HR-06`: canonical provenance is too thin for strong replay and audit reconstruction.
- `HR-07`: goldset summary/ledger provenance is richer than runtime provenance but still lacks some replay fingerprints and closed failure taxonomies.
- `HR-08`: canonical JSON, markdown, summary JSON, governance report JSON, and JSONL ledger writes are not atomic.
- `HR-09`: pack path handling and import-root mutation are permissive relative to the repo’s conservative trust boundary.
- `HR-10`: pack fatal-gate semantics are documented as requests but runtime behavior leaves the semantics implicit.
- `HR-11`: dormant provider/adapter seams could be admitted later without explicit local-first/determinism gates.
- `HR-12`: release/install truth surfaces are duplicated across manifest, packaging, tests, docs, and scripts.
- `HR-13`: docs and tests are strong, but lockstep enforcement is spread across several entrypoints rather than one explicit hardening matrix.

See `APR_V2_HARDENING_RISK_REGISTER.md` for full detail.

## 6. Target Hardened Architecture

| Current state | Weakness | Proposed addition | Change class | Exact affected files | Dependency order | Validation needed | Migration risk | When |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Policy, runtime, schema, and benchmark duplicate taxonomies | Silent drift can survive until a specific test trips | Add explicit lockstep validators and close schema enums where semantics are already fixed | Additive | `contracts/active/*`, `src/apr_core/{pipeline.py,classify/classification.py}`, `src/apr_core/goldset/runner.py`, `scripts/validate_contract.py` | First | Contract script + targeted pytest | Low if additive | Now |
| Canonical schema is closed at top level but loose in some nested semantics | Semantic strings can drift without contract failure | Tighten nested enums and closed object surfaces for classification, routing, provenance, and pack metadata | Additive schema hardening | `contracts/active/canonical_audit_record.schema.json`, docs, surface-lock tests | After taxonomy inventory | Contract tests + surface-lock tests | Medium because downstream snapshots must update intentionally | Now |
| Benchmark manifests match active contract today by convention only | Manifest/runtime mismatch can go undetected | Add active-contract parity checks for dev and holdout manifests and CI enforcement | Additive validation | `scripts/validate_goldset.py`, `src/apr_core/goldset/runner.py`, `benchmarks/goldset/schemas/manifest.schema.json` | Early | Goldset validation + targeted goldset tests | Low | Now |
| Canonical provenance only records time, versions, and stage list | Replay and audit reconstruction are incomplete | Add deterministic replay fingerprints and source digests without changing recommendation semantics | Additive schema/runtime change | `src/apr_core/pipeline.py`, canonical schema, docs, tests | After schema closure | Contract tests + replay tests + surface locks | Medium | Now |
| Goldset summary and ledger track governance well but not every replay surface | Regression evidence may be harder to reconstruct than necessary | Expand ledger/summary replay envelope and failure-class closures | Additive benchmark hardening | `src/apr_core/goldset/runner.py`, summary/ledger schemas, tests | After manifest parity | Goldset tests + ledger replay checks | Medium | Now |
| Output writes are direct file writes or direct JSONL append | Partial writes are possible on interruption | Add atomic write primitives and crash-safe ledger append strategy | Refactor-level local IO hardening | `src/apr_core/utils.py`, `src/apr_core/cli.py`, `src/apr_core/goldset/runner.py` | After provenance design | CLI smoke + tempdir tests | Low to medium | Now |
| Pack paths are raw strings and global import roots are mutated | Advisory seam is broader than necessary | Canonicalize paths, dedupe requests, capture pack fingerprints, and constrain import behavior | Additive trust-boundary hardening | `src/apr_core/packs/loader.py`, pack docs, pack tests | Independent | Regression pack tests + surface locks | Medium | Now |
| Pack docs mention fatal-gate requests but runtime treats them as additive metadata | Readers can over-interpret pack authority | Clarify/request semantics in docs, schema names, and decision-path tests without giving packs ownership of recommendations | Additive doctrine hardening | `docs/PACK_INTERFACE.md`, pack schema/runtime docs/tests, possibly normalized pack-result naming | After pack path hardening | Pack regression tests + docs lockstep | Low | Now |
| Provider and adapter seams are dormant but lightly defined | Future activation could violate determinism/local-first assumptions | Add explicit admission checklist, tests, and docs proving inertness until admitted | Additive guardrail | `src/apr_core/providers/*`, `src/apr_core/adapters/*`, docs, tests | Independent | Grep-based tests / targeted unit tests | Low | Later-now |
| Benchmark and README docs can drift from live manifests and holdout reality | Users can act on stale repo guidance | Correct authoritative docs, then add lockstep checks tied to manifests/tests | Additive docs hardening | `README.md`, `benchmarks/goldset/README.md`, `benchmarks/goldset/holdout/README.md`, `docs/SPEC_IMPLEMENTATION_MATRIX.md`, `docs/BENCHMARK_POLICY.md` | Earliest | Docs lockstep checks | Low | Now |
| Release/build truth is spread across manifest, packaging, scripts, and tests | Future release changes can become incoherent | Add explicit release-surface lock tests and docs alignment | Additive release hardening | `pyproject.toml`, `setup.py`, `scripts/build_release.py`, `docs/RELEASE_POLICY.md`, CI/tests | Late | Release smoke + clean-tree release check | Low | Later |

## 7. Phase-by-Phase Roadmap

- Phase 1: close runtime contract drift first by locking taxonomies, canonical schema semantics, and processing-state doctrine.
- Phase 2: tighten validation and benchmark truth surfaces so repo health catches drift before runtime or docs diverge.
- Phase 3: expand provenance, replay, and failure-taxonomy fidelity without changing recommendation semantics.
- Phase 4: harden local file outputs, ledger persistence, and readiness checks against interruption and operator ambiguity.
- Phase 5: narrow pack/provider/adapter trust boundaries while keeping packs advisory and other seams dormant.
- Phase 6: finish with docs, release, migration, and extension governance so published repo truth matches actual runtime and validation behavior.

See `APR_V2_HARDENING_PHASES.md` for full phase detail.

## 8. Work Package Strategy

- Start with low-risk, high-clarity lockstep work that does not alter recommendations: docs truthfulness, benchmark-manifest parity, and contract taxonomy guards.
- Move next into schema closure and provenance additions, because those need coordinated updates to docs and surface-lock tests.
- Defer file-write resilience until after provenance fields settle so atomic-write surfaces do not churn twice.
- Keep pack hardening additive: narrow path/import behavior and clarify advisory semantics, but do not give packs control over core recommendation semantics.
- Leave provider/adapter seams inactive. Hardening there is about admission policy and proof of inertness, not activation.
- Treat release/migration work as the final wave after runtime, benchmark, and docs surfaces are in lockstep.

Recommended execution waves:
- Wave 1: `WP-16` completed on 2026-04-09; next execution order is `WP-04`, then `WP-01`
- Wave 2: `WP-02`, `WP-03`, `WP-05`, `WP-06`
- Wave 3: `WP-07`, `WP-08`, `WP-09`
- Wave 4: `WP-10`, `WP-11`, `WP-12`
- Wave 5: `WP-13`, `WP-14`, `WP-15`
- Wave 6: `WP-17`, `WP-18`

## 9. Validation Strategy

- Minimum sufficient gate for contract/canonical work:
  - `python scripts/validate_contract.py`
  - `python -m pytest tests/contract tests/regression/test_minimal_pipeline.py tests/surface_lock/test_output_surfaces.py -q`
- Minimum sufficient gate for benchmark/governance work:
  - `python scripts/validate_goldset.py`
  - `python -m pytest tests/goldset tests/regression/test_cli_smoke.py tests/regression/test_surface_isolation.py -q`
  - `apr goldset --output <tmp-summary>`
- Minimum sufficient gate for provenance/replay work:
  - replay-focused pytest targets in `tests/regression/test_trace_stability.py`, `tests/regression/test_invariance_trace.py`, and `tests/adversarial/`
  - ledger parse/append tests in `tests/goldset/test_goldset_runner.py`
- Minimum sufficient gate for IO/release work:
  - CLI smoke tests
  - tempdir atomic-write tests
  - clean-tree `python scripts/build_release.py`
- Minimum sufficient gate for docs truthfulness:
  - targeted docs lockstep tests
  - README/benchmark/doc references verified against active manifests and schemas
- Stronger pre-merge gate for any multi-surface package:
  - full `python -m pytest`
  - CI workflow parity
  - `apr doctor` from a clean worktree

## 10. Strategic Summary

APR v2 Gold already has strong architecture discipline: one active runtime contract, one canonical truth object, deterministic local execution, advisory-only packs, and a benchmark harness that already behaves like real governance infrastructure. The hardening program should preserve that shape, not redesign it.

The highest-value work is to remove silent drift channels between doctrine, schema, runtime, benchmark, and docs; make provenance and replay materially stronger; and harden local file outputs and extension seams without introducing services, databases, or non-local execution. The safest path is additive: tighten validation first, then extend provenance, then harden IO, then guard future seams and release surfaces.

## 11. Open Uncertainties

- The reviewed working branch is ahead of `main`. Promotion order back to default branch is a repo-management question, not an architecture blocker, but it affects where future hardening PRs should land first.
- The highest-signal authoritative docs now describe holdout as active and split-manifest based, but generated and historical surfaces can still carry stale strings and should not be treated as authority.
- Provenance hardening needs a precise choice about which replay fingerprints belong in `CanonicalAuditRecord` versus benchmark-only ledger surfaces.
- Pack “fatal-gate requests” need clearer naming so they remain advisory without being mistaken for core recommendation ownership.
- `apr doctor` currently mixes runtime validation with clean-tree readiness. The hardening plan treats that as a design choice to revisit, not an immediate bug.
