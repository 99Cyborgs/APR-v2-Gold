# Boundaries

## Operator Invariants

- One canonical audit record is the only semantic source for renderers.
- Renderers may transform presentation, not meaning.
- Contract changes require explicit blast-radius review.
- Domain logic must not silently migrate into core runtime.
- Benchmark or fixture convenience must not mutate normative semantics.
- Release readiness requires validation receipts, not narrative confidence.

## Surface Separation

| Surface | Authoritative paths | What belongs here | Allowed additive change | Prohibited drift |
| --- | --- | --- | --- | --- |
| Deterministic core runtime | `src/apr_core/**` | Ingest, parse, classify, gates, rehabilitation, pack execution, CLI logic | Bug fixes, explicit new logic with matching contract/tests, additive helper modules | Hidden policy changes, domain heuristics promoted without review, pack logic baked into core |
| Contract surface | `contracts/active/**` | Runtime-loadable schemas, manifest, policy layer | Explicit versioned contract edits with synchronized runtime/tests/docs | Silent field meaning changes, multi-active-contract behavior, unreviewed schema expansion |
| Renderer surface | `src/apr_core/render/**` | Presentation derived from canonical record | Additive formatting or sectioning that consumes existing canonical fields | Reinterpreting canonical meaning, deriving decisions outside the canonical record |
| Benchmark surface | `benchmarks/goldset/**`, `benchmarks/goldset_dev/**`, `benchmarks/goldset_holdout/**`, `src/apr_core/goldset/**` | Manifests, schemas, ledgers, governance rules, goldset execution | New cases, schema-aligned summary fields, ledger-safe diagnostics | Benchmark shortcuts that alter live semantics, undocumented gate changes |
| Fixture surface | `fixtures/**` | Normalized input fixtures and example external packs | New fixtures, additive test fixtures, scaffold packs for testing | Treating fixtures as governing policy, backfilling expected behavior without validation |
| Advisory-pack surface | `fixtures/external_packs/**`, `src/apr_core/packs/**`, `docs/PACK_INTERFACE.md` | Explicit path-loaded advisory packs and pack protocol | New external packs, clearer pack metadata, pack-specific tests | Core recommendation overwrite, pack auto-loading, domain logic migration into core |
| Local output / generated artifacts | `output/**`, `dist/**`, `benchmarks/goldset/output/**`, `.pytest_cache/**`, `__pycache__/**` | Receipts, summaries, rendered markdown, built archives, caches | Regenerate, inspect, delete if task requires | Treating generated output as authoritative source truth |

## Allowed Additive Change Rules

- Add repo-local Codex guidance under `.codex/`.
- Add fixtures or benchmark cases when they do not silently change pass criteria.
- Add advisory packs as explicit path-based repos or fixture scaffolds.
- Add renderer presentation polish only when canonical fields stay authoritative.
- Add tests and docs that tighten validation around existing doctrine.

## Prohibited Semantic Drift

- Reclassifying venue routing as a substitute for scientific-record gating.
- Making rendered markdown or benchmark summaries authoritative over the canonical record.
- Introducing advisory-pack behavior that silently rewrites core recommendation semantics.
- Adding contract fields or policy states without synchronized manifest, schema, runtime, docs, and tests.
- Treating benchmark convenience manifests or local outputs as normative doctrine.

## Domain Logic Placement

Domain-specific logic belongs in advisory packs unless intentionally promoted into core through explicit contract and policy review. If a change proposal is domain-specific, stop and ask whether it should remain external before touching `src/apr_core/`.

## Change Impact Matrix

| Path pattern | Impact class | Minimum review | Minimum validation | Stop if |
| --- | --- | --- | --- | --- |
| `contracts/active/*` | Contract blast radius | Inspect schema, policy, manifest, downstream consumers | `python scripts/validate_contract.py`, `python -m pytest tests/contract/test_active_schemas.py tests/contract/test_contract_manifest.py`, relevant runtime/render tests | Intent is unclear or versioning is unsynchronized |
| `src/apr_core/*` | Runtime semantics | Map touched modules to pipeline stage and doctrine | Relevant targeted tests plus contract validation; add `python -m pytest tests/regression/test_cli_smoke.py` for CLI-facing changes | Change would bypass scientific-record gate or canonical output discipline |
| `src/apr_core/render/*` | Presentation surface | Confirm canonical fields consumed and section ordering expectations | `python -m pytest tests/surface_lock/test_output_surfaces.py tests/regression/test_cli_smoke.py` | Renderer starts deriving new meaning |
| `benchmarks/goldset*/*` | Governance / benchmark | Inspect manifest paths, schemas, runner, docs | `python scripts/validate_goldset.py`, `apr goldset --output <summary>` or fallback CLI | Docs and executable manifests disagree and you cannot reconcile the run target |
| `fixtures/*` | Test/fixture surface | Confirm fixture role and affected tests | Relevant audit/render smoke plus scenario or goldset tests | Fixture is being used to imply doctrine rather than exercise it |
| `fixtures/external_packs/*` | Advisory-pack surface | Check pack metadata, supported domains, advisory-only rules | `apr packs --pack-path <pack_dir>`, fixture audit with `--pack-path`, relevant pack tests | Pack behavior leaks into core recommendation semantics |
| `pyproject.toml`, `setup.py`, `src/apr_core_bootstrap.py`, `Makefile` | Packaging / CLI entrypoints | Confirm public CLI surfaces and install flow stay stable | CLI smoke tests and the affected command directly | Public command names or entrypoints would change unintentionally |
