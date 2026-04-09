# Operator Quickstart

## 1. Cold-Start Reconnaissance

### Use when

You are opening APR v2 Gold with little or no prior context.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Start with session_bootstrap.md and inspect APR v2 Gold for a cold-start architecture summary. Read README.md, pyproject.toml, Makefile, src/apr_core/cli.py, src/apr_core/pipeline.py, contracts/active/*, docs/ARCHITECTURE.md, docs/CANONICAL_AUDIT_RECORD.md, benchmarks/, and fixtures/. Return Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, and an Architecture Summary artifact. Do not edit anything yet.`

### Expected artifacts

- architecture summary
- authority order note
- initial change-impact matrix seed

### Required validation

- confirm repo root
- verify active contract files exist
- verify CLI entrypoints from `pyproject.toml`

## 2. Contract Blast-Radius Review

### Use when

A change touches `contracts/active/*`, canonical schema, or policy.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Review the contract blast radius for these touched APR v2 Gold files: <paths>. Inspect contracts/active/*, impacted runtime consumers, and relevant tests. Return Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, and a Touched-File Impact Memo. State whether canonical record meaning, policy semantics, or renderer consumption would change.`

### Expected artifacts

- touched-file impact memo
- contract blast-radius note

### Required validation

- `python scripts/validate_contract.py`
- contract tests if edits are made

## 3. Fixture Audit and Render Receipt

### Use when

You need a deterministic end-to-end audit receipt on one fixture.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Run APR v2 Gold on fixture <fixture path> through audit and render. Emit a canonical record, render markdown only from that record, compare artifact integrity, and return Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, a Deterministic Run Receipt, and a Validation Report.`

### Expected artifacts

- canonical record
- rendered markdown
- deterministic run receipt

### Required validation

- `apr audit ... --output ...`
- `apr render ... --output ...`
- note any schema or render surface drift

## 4. CLI Smoke Pass

### Use when

CLI, packaging, or smoke paths may have changed.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Run an APR v2 Gold CLI smoke pass covering doctor, audit, review, render, goldset smoke, and pack inspection. Treat dirty-worktree doctor output as repo-state information rather than automatic runtime failure. Return Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, and a Validation Report with the commands actually run and the artifacts produced.`

### Expected artifacts

- validation report
- smoke output paths
- doctor interpretation note

### Required validation

- direct CLI commands
- `python -m pytest tests/regression/test_cli_smoke.py`

## 5. Goldset Execution Pass

### Use when

Runtime, benchmark, or canonical-output changes may affect the benchmark harness.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Run a governed APR v2 Gold goldset execution pass. Verify the executable manifest location before assuming it, validate benchmark schemas, produce a summary receipt, and report any gate failures or manifest-path ambiguity. Return Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, a Validation Report, and a Deterministic Run Receipt.`

### Expected artifacts

- goldset summary
- validation report
- manifest-path note

### Required validation

- `python scripts/validate_goldset.py`
- `apr goldset --output ...`
- optional holdout run only if requested

## 6. Renderer Consistency Review

### Use when

Renderer files or canonical output surfaces may have changed.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Review renderer consistency in APR v2 Gold. Confirm renderers consume canonical records without redefining meaning, run a fixture through audit and render, compare the emitted markdown against canonical fields, and report any section-order or field-mapping drift. Return Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, and a Validation Report.`

### Expected artifacts

- validation report
- renderer drift note

### Required validation

- audit plus render receipt
- `python -m pytest tests/surface_lock/test_output_surfaces.py`

## 7. Advisory Pack Scaffold Creation

### Use when

You need a new external advisory pack or fixture-pack scaffold.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Create a new APR v2 Gold advisory pack scaffold at <target path> using the existing external pack fixtures as references. Keep the pack advisory-only, explicit-path loaded, and outside core semantics. Return Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, and an Advisory-Pack Scaffold Report.`

### Expected artifacts

- scaffolded pack files
- advisory-pack scaffold report

### Required validation

- `apr packs --pack-path <target path>`
- one `apr audit ... --pack-path <target path>` receipt

## 8. Touched-File Impact Mapping

### Use when

You have a diff and need a governed review before editing or merging.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Map the change impact of these APR v2 Gold touched files: <paths>. Classify each path by boundary surface, explain the likely blast radius, identify doctrine-sensitive risks, and produce the smallest sufficient validation plan. Return findings first, then Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, and a Touched-File Impact Memo.`

### Expected artifacts

- touched-file impact memo
- validation plan

### Required validation

- inspect the actual diff
- map each path through `BOUNDARIES.md`

## 9. Release-Readiness Inspection

### Use when

You need a go or no-go view before packaging or publishing.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Perform a release-readiness inspection for APR v2 Gold. Verify clean-tree status, contract validity, canonical-record generation, renderer integrity, benchmark status, and release artifact buildability. Return Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, and a Release-Readiness Report with blockers, missing receipts, and commands actually run.`

### Expected artifacts

- release-readiness report
- build artifact path if created

### Required validation

- `git status --short`
- contract validation
- relevant tests
- goldset receipt
- `python scripts/build_release.py`

## 10. Determinism and Canonical-Record PR Review

### Use when

You need a review focused on APR doctrine rather than generic style commentary.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Review the current APR v2 Gold diff for determinism, one-canonical-record discipline, scientific-record gating before venue routing, renderer consumption integrity, contract-first development, and advisory-pack isolation. Return findings first with path references and resolution paths, then Confirmed Repo Facts, Inferences / Uncertainty, Risks, and Exact Validation Steps.`

### Expected artifacts

- review findings
- touched-file impact memo

### Required validation

- inspect actual diff
- run smallest sufficient tests for the touched surfaces
