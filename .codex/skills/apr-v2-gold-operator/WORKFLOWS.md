# Workflows

If `apr` is not installed in the active shell, use the fallback commands in `COMMANDS.md`.

## A. Repo Reconnaissance

### When to use

Use at session start or before any nontrivial edit.

### Required inputs

- repo root
- optional touched paths

### Commands to run

- `Get-ChildItem -Force`
- `Get-Content -Raw README.md`
- `Get-Content -Raw pyproject.toml`
- `Get-Content -Raw src/apr_core/cli.py`
- `Get-ChildItem contracts/active`
- `Get-ChildItem benchmarks`
- `Get-ChildItem fixtures`

### Files to inspect

- `README.md`
- `pyproject.toml`
- `Makefile`
- `docs/ARCHITECTURE.md`
- `docs/CANONICAL_AUDIT_RECORD.md`
- `contracts/active/*`

### Expected outputs

- architecture summary
- authority order
- path-based change-impact seed

### Failure conditions

- repo root is ambiguous
- active contract files are missing
- CLI and docs disagree on critical paths

### Stop conditions

- unresolved conflict between docs and executable surfaces
- cannot identify the active runtime or active contract

### What not to infer

- do not infer benchmark manifest location from docs alone
- do not infer readiness from directory names alone

## B. Contract Integrity Audit

### When to use

Use before or after touching `contracts/active/*`, policy, or canonical schema consumers.

### Required inputs

- touched contract paths
- intended contract change, if any

### Commands to run

- `python scripts/validate_contract.py`
- `python -m pytest tests/contract/test_active_schemas.py tests/contract/test_contract_manifest.py`
- `Get-Content -Raw contracts/active/manifest.yaml`
- `Get-Content -Raw contracts/active/policy_layer.yaml`

### Files to inspect

- `contracts/active/audit_input.schema.json`
- `contracts/active/canonical_audit_record.schema.json`
- `contracts/active/manifest.yaml`
- `contracts/active/policy_layer.yaml`
- impacted runtime consumers under `src/apr_core/`

### Expected outputs

- contract blast-radius memo
- validation receipt
- explicit list of synchronized consumer surfaces

### Failure conditions

- schema invalid
- manifest and policy versions diverge
- fixture audit no longer produces schema-valid canonical output

### Stop conditions

- contract intent is implicit rather than explicit
- active contract count or compatibility semantics become unclear

### What not to infer

- do not assume a schema field is safe because tests are green
- do not assume docs stayed aligned unless checked

## C. Canonical Record Validation Pass

### When to use

Use after changing runtime, contract, or fixtures that can affect emitted canonical records.

### Required inputs

- at least one representative fixture path
- output directory for receipts

### Commands to run

- `apr audit fixtures/inputs/reviewable_sound_paper.json --output output/skill_runs/reviewable_sound_record.json`
- `apr render output/skill_runs/reviewable_sound_record.json --output output/skill_runs/reviewable_sound_report.md`
- `python -m pytest tests/surface_lock/test_output_surfaces.py`

### Files to inspect

- emitted canonical JSON
- rendered markdown
- `contracts/active/canonical_audit_record.schema.json`
- `src/apr_core/pipeline.py`
- `src/apr_core/render/markdown.py`

### Expected outputs

- canonical record receipt
- render receipt
- note on any changed top-level surfaces or section order

### Failure conditions

- `apr audit` fails
- `apr render` rejects the record
- output surface tests fail

### Stop conditions

- canonical record changes are present without explicit intent
- render behavior changes but canonical record diff is unexplained

### What not to infer

- do not infer renderer correctness from a visually plausible markdown file
- do not infer schema stability from one passing fixture

## D. CLI Smoke and Fixture Audit Run

### When to use

Use after CLI, packaging, fixture, or smoke-path changes.

### Required inputs

- repo-local output directory

### Commands to run

- `apr doctor`
- `apr audit fixtures/inputs/reviewable_sound_paper.json --output output/skill_runs/cli_record.json`
- `apr review fixtures/inputs/reviewable_sound_paper.json --profile nature_selective --output output/skill_runs/cli_review_record.json`
- `apr render output/skill_runs/cli_record.json --output output/skill_runs/cli_report.md`
- `apr packs --pack-path fixtures/external_packs/apr-pack-physics --pack-path fixtures/external_packs/apr-pack-clinical`
- `python -m pytest tests/regression/test_cli_smoke.py`

### Files to inspect

- `src/apr_core/cli.py`
- `pyproject.toml`
- emitted smoke artifacts under `output/skill_runs/`

### Expected outputs

- doctor output or dirty-tree explanation
- CLI smoke artifacts
- pack inspection report

### Failure conditions

- command wiring breaks
- profile override fails
- pack discovery fails

### Stop conditions

- `apr doctor` reports missing repo surfaces
- dirty worktree is the only failure and the task requires clean release validation

### What not to infer

- do not infer runtime breakage from a dirty-tree doctor failure alone
- do not infer installed CLI availability; verify it

## E. Goldset Execution Pass

### When to use

Use after runtime, benchmark, pack, or canonical-output changes that can affect benchmark summaries.

### Required inputs

- summary output path
- optional manifest override
- optional holdout intent

### Commands to run

- `python scripts/validate_goldset.py`
- `apr goldset --output output/skill_runs/goldset_summary.json`
- `python scripts/validate_goldset.py --summary output/skill_runs/goldset_summary.json --ledger benchmarks/goldset/output/calibration_ledger.jsonl`
- `apr goldset --holdout --no-ledger --output output/skill_runs/holdout_summary.json`

### Files to inspect

- `benchmarks/goldset/README.md`
- `benchmarks/goldset/schemas/*`
- `benchmarks/goldset_dev/manifest.yaml`
- `benchmarks/goldset_holdout/manifest.yaml`
- `docs/BENCHMARK_POLICY.md`

### Expected outputs

- goldset summary
- governance report
- ledger validation receipt
- holdout summary when requested

### Failure conditions

- manifest load failure
- schema validation failure
- gate status fail

### Stop conditions

- you cannot identify which manifest is authoritative for the requested run
- holdout run would expose redacted expectation surfaces

### What not to infer

- do not infer dev and holdout manifests are interchangeable
- do not infer a green schema check means benchmark gates passed

## F. Advisory Pack Scaffold Creation

### When to use

Use when adding a new external pack or a repo-local fixture pack without changing core semantics.

### Required inputs

- target pack path
- supported domains
- minimal advisory objective

### Commands to run

- `Get-Content -Raw fixtures/external_packs/apr-pack-physics/pack.yaml`
- `Get-Content -Raw fixtures/external_packs/apr-pack-physics/src/apr_pack_physics/entry.py`
- `apr packs --pack-path <new_pack_dir>`
- `apr audit <fixture.json> --pack-path <new_pack_dir> --output output/skill_runs/<pack_record>.json`

### Files to inspect

- `docs/PACK_INTERFACE.md`
- `fixtures/external_packs/apr-pack-physics/**`
- `fixtures/external_packs/apr-pack-clinical/**`
- `src/apr_core/packs/**`

### Expected outputs

- scaffolded pack files
- pack inspection receipt
- one applicable or not-applicable audit receipt
- advisory-pack scaffold report

### Failure conditions

- pack metadata invalid
- pack cannot load by explicit path
- pack output leaks into core semantics

### Stop conditions

- requested logic belongs in core runtime rather than a pack
- pack requires auto-loading or silent recommendation overwrite

### What not to infer

- do not infer fixture-pack scaffolds are production-ready external repos
- do not infer pack advisories can redefine canonical field meaning

## G. Render Consistency Validation

### When to use

Use after touching renderer code, canonical schema fields, or markdown expectations.

### Required inputs

- canonical record fixture or generated record

### Commands to run

- `apr audit fixtures/inputs/reviewable_sound_paper.json --output output/skill_runs/render_record.json`
- `apr render output/skill_runs/render_record.json --output output/skill_runs/render_report.md`
- `python -m pytest tests/surface_lock/test_output_surfaces.py tests/regression/test_cli_smoke.py`

### Files to inspect

- `src/apr_core/render/markdown.py`
- `docs/CANONICAL_AUDIT_RECORD.md`
- emitted markdown

### Expected outputs

- render consistency note
- changed section or field mapping list, if any

### Failure conditions

- section order drift
- renderer consumes missing or renamed fields
- markdown summary contradicts canonical values

### Stop conditions

- renderer needs data that the canonical record does not expose
- presentation changes imply semantic reinterpretation

### What not to infer

- do not infer meaning from prose labels alone; trace back to canonical fields

## H. Release-Readiness Inspection

### When to use

Use before packaging, tagging, or declaring the repo ready for release.

### Required inputs

- clean worktree expectation
- output directory for receipts

### Commands to run

- `git status --short`
- `python scripts/validate_contract.py`
- `python scripts/validate_goldset.py`
- `python -m pytest`
- `apr goldset --output output/skill_runs/release_goldset_summary.json`
- `python scripts/build_release.py`

### Files to inspect

- `contracts/active/manifest.yaml`
- `CHANGELOG.md`
- `dist/` after build

### Expected outputs

- release-readiness report
- goldset summary receipt
- built archive path

### Failure conditions

- dirty worktree
- failed tests or failed benchmark gate
- release artifact missing

### Stop conditions

- clean-tree requirement is not satisfied
- contract version source is unclear

### What not to infer

- do not infer release readiness from passing unit tests alone
- do not infer build reproducibility without a clean-tree receipt

## I. Change-Impact Review for Touched Files

### When to use

Use before editing, during review, or after diff creation.

### Required inputs

- touched file list

### Commands to run

- `git status --short`
- `git diff --name-only`
- `git diff -- <path>`

### Files to inspect

- every touched file
- mapped neighbor surfaces from `BOUNDARIES.md`
- relevant tests and docs for each touched surface

### Expected outputs

- touched-file impact memo
- validation plan by path cluster
- explicit unknowns

### Failure conditions

- touched file cannot be mapped to a governed surface
- high-sensitivity edit lacks validation coverage

### Stop conditions

- contract or runtime intent is unclear
- diff suggests semantic drift without explicit approval

### What not to infer

- do not infer low risk from small line count
- do not infer docs-only change when public commands or schemas moved

## J. Safe Additive Extension Workflow

### When to use

Use when adding docs, tests, fixtures, outputs, or pack scaffolds without intending doctrine changes.

### Required inputs

- target path
- statement of additive intent

### Commands to run

- `git status --short`
- inspect the closest existing analog with `Get-Content -Raw <existing_file>`
- run the smallest affected validation from `VALIDATION.md`

### Files to inspect

- nearest analogous file
- path cluster from `BOUNDARIES.md`
- impacted tests or scripts

### Expected outputs

- additive-change memo
- validation receipt sized to the actual blast radius

### Failure conditions

- additive change requires contract or policy reinterpretation
- new file shadows an existing governed surface

### Stop conditions

- request would introduce hidden policy
- extension needs public CLI or contract changes that were not requested

### What not to infer

- do not infer additive safety from file location alone
- do not infer a new convenience layer is harmless if it duplicates governed logic
