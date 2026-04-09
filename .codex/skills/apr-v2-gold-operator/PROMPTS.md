# Prompts

Every prompt below requires the response to separate:

- `Confirmed Repo Facts`
- `Inferences / Uncertainty`
- `Risks`
- `Exact Validation Steps`

Do not collapse those sections.

## Inspect Repo and Summarize Architecture

### Use when

You need a cold-start orientation before proposing edits.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Inspect APR v2 Gold from the repo root. Read README.md, pyproject.toml, Makefile, docs/ARCHITECTURE.md, docs/CANONICAL_AUDIT_RECORD.md, src/apr_core/cli.py, src/apr_core/pipeline.py, contracts/active/manifest.yaml, and contracts/active/policy_layer.yaml. Summarize the architecture, authority order, deterministic flow, governed surfaces, and current command surfaces. Return sections for Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, and a short Architecture Summary artifact. Do not propose edits yet.`

## Validate Contract and Schema Implications of a Change

### Use when

Touched files include `contracts/active/*`, policy, canonical schema, or runtime consumers of those surfaces.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Review the contract and schema implications of this APR v2 Gold change: <describe change or touched files>. Inspect contracts/active/*, the impacted runtime consumers under src/apr_core/, and the relevant tests under tests/contract/ and tests/surface_lock/. Return Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, and a Contract Blast Radius artifact. Explicitly call out whether canonical record meaning, policy semantics, or renderer consumption surfaces would change.`

## Run a Fixture Through Audit and Render, Then Compare Artifact Integrity

### Use when

You need a deterministic receipt that the audit and renderer still agree.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Run a fixture-based audit and renderer integrity pass in APR v2 Gold using fixture <fixture path>. Produce a canonical record, render markdown from that record, compare the rendered claims against the canonical fields, and report any surface drift. Return Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, and a Deterministic Run Receipt plus Validation Report. Do not infer correctness from markdown alone; trace every claim back to the canonical record.`

## Create a New Advisory Pack Scaffold Without Polluting Core Semantics

### Use when

You need an external pack or fixture-pack scaffold.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Create a new advisory pack scaffold for APR v2 Gold at <target path> for supported domains <domains>. Use the existing external pack fixtures as references, keep the pack advisory-only, and do not move domain logic into src/apr_core/. Return Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, and an Advisory-Pack Scaffold Report. Include the exact files created, the pack metadata, and the validation commands required to prove explicit path loading and scoped pack_results behavior.`

## Review a PR for Determinism and Canonical-Record Discipline

### Use when

You need a code review focused on governed APR invariants.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Review the current APR v2 Gold diff for determinism, contract discipline, canonical-record discipline, renderer consumption integrity, scientific-record gating before venue routing, and advisory-pack isolation. Return findings first, then Confirmed Repo Facts, Inferences / Uncertainty, Risks, and Exact Validation Steps. For each finding, include the path, mechanism-level concern, blast radius, and the smallest sufficient resolution path.`

## Perform Release-Readiness Check for APR v2 Gold

### Use when

You need a governed go or no-go decision before packaging or publishing.

### Prompt

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator. Perform a release-readiness inspection for APR v2 Gold. Verify git cleanliness, contract validity, canonical-record generation, renderer integrity, benchmark stability, and release artifact buildability. Return Confirmed Repo Facts, Inferences / Uncertainty, Risks, Exact Validation Steps, and a Release-Readiness Report with blockers, missing receipts, and commands actually run. Do not substitute narrative confidence for validation receipts.`
