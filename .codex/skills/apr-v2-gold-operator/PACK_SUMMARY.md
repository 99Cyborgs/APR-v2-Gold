# Skill Pack Summary

## What Was Created

This skill pack provides repo-local operational guidance for APR v2 Gold around:

- reconnaissance
- contract and schema review
- canonical-record validation
- CLI smoke execution
- render consistency checks
- goldset execution
- advisory-pack scaffolding
- release-readiness inspection
- change-impact mapping

Primary files:

- `SKILL.md`
- `BOUNDARIES.md`
- `WORKFLOWS.md`
- `CHECKLISTS.md`
- `COMMANDS.md`
- `PROMPTS.md`
- `VALIDATION.md`
- `ARTIFACTS.md`
- `OPERATOR_QUICKSTART.md`
- `session_bootstrap.md`

## Where It Lives

The pack lives at:

- `.codex/skills/apr-v2-gold-operator/`

This path was chosen because the repo did not already contain a Codex skill directory, and `.codex/skills/` is additive and repo-local without touching runtime, contract, benchmark, or fixture semantics.

## How to Use It

Start with `session_bootstrap.md`, then load `SKILL.md` and only the supporting file needed for the current task.

Example invocation:

`Use the repo-local skill at .codex/skills/apr-v2-gold-operator to inspect APR v2 Gold, preserve contract and canonical-record boundaries, and execute the requested workflow with validation receipts.`

## Repo Assumptions Still Requiring Verification

- Benchmark docs still mention `benchmarks/goldset/manifest.yaml`, but the current CLI defaults load `benchmarks/goldset_dev/manifest.yaml` and `benchmarks/goldset_holdout/manifest.yaml`.
- `apr doctor` is sensitive to git cleanliness, so a dirty worktree can produce a nonzero result even when runtime wiring is otherwise intact.
- Wrapper CLI entrypoints exist in `pyproject.toml`, but routine repo work should still standardize on the main `apr <subcommand>` interface unless alias coverage is the subject of the task.
