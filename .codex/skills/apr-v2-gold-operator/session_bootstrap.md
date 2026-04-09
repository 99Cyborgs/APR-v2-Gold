# Session Bootstrap

Use this file first on a cold APR v2 Gold session.

## Order

1. Read `README.md`.
2. Inspect the repo tree at the top level.
3. Inspect active contract files under `contracts/active/`.
4. Discover CLI entrypoints and package config from `pyproject.toml`, `setup.py`, `Makefile`, and `src/apr_core/cli.py`.
5. Discover tests under `tests/` and note the most relevant targeted suites.
6. Run `apr doctor` or the nearest health check if CLI availability or git cleanliness blocks it.
7. Only then propose edits.

## Minimum cold-start commands

```powershell
Get-ChildItem -Force
Get-Content -Raw README.md
Get-ChildItem contracts/active
Get-Content -Raw pyproject.toml
Get-Content -Raw src/apr_core/cli.py
Get-ChildItem tests
apr doctor
```

## Bootstrap stop rules

- Stop if the repo root is ambiguous.
- Stop if `contracts/active/` is missing or another contract surface looks loadable.
- Stop if docs and executable CLI surfaces disagree on a path you must rely on.
- Stop if the intended change would move advisory-pack logic into core semantics without explicit approval.

## Bootstrap notes

- `apr doctor` checks git cleanliness. On a dirty worktree, record that fact and continue with narrower validation if the task is not release readiness.
- In the current repo state, verify benchmark manifest location before assuming `benchmarks/goldset/manifest.yaml`; CLI defaults point at `benchmarks/goldset_dev/manifest.yaml` and `benchmarks/goldset_holdout/manifest.yaml`.
