# Commands

## Command Discovery First

If command availability is uncertain, inspect these files before running anything else:

- `README.md`
- `pyproject.toml`
- `Makefile`
- `src/apr_core/cli.py`
- `tests/regression/test_cli_smoke.py`
- `scripts/validate_contract.py`
- `scripts/validate_goldset.py`

Observed in-repo command surfaces:

- `apr doctor`
- `apr audit`
- `apr review`
- `apr render`
- `apr goldset`
- `apr packs`
- `python scripts/validate_contract.py`
- `python scripts/validate_goldset.py`
- `python -m pytest`
- `python scripts/build_release.py`

No lint command was observed in the inspected repo surfaces.

## Preferred Execution Modes

### Installed CLI

Prefer this when `apr` resolves in the shell:

```powershell
apr doctor
apr audit fixtures/inputs/reviewable_sound_paper.json --output output/skill_runs/record.json
apr render output/skill_runs/record.json --output output/skill_runs/report.md
```

### Repo-Local Fallback

Use this when `apr` is not installed:

```powershell
$env:PYTHONPATH = (Resolve-Path "src").Path
python -m apr_core.cli doctor
python -m apr_core.cli audit fixtures/inputs/reviewable_sound_paper.json --output output/skill_runs/record.json
python -m apr_core.cli render output/skill_runs/record.json --output output/skill_runs/report.md
```

## Install / Test / Validate

```powershell
python -m pip install -e .[dev]
python -m pytest
python scripts/validate_contract.py
python scripts/validate_goldset.py
python scripts/build_release.py
```

## CLI Smoke and Audit

```powershell
apr doctor
apr audit fixtures/inputs/reviewable_sound_paper.json --output output/skill_runs/reviewable_sound_record.json
apr review fixtures/inputs/reviewable_sound_paper.json --profile nature_selective --output output/skill_runs/review_record.json
apr render output/skill_runs/reviewable_sound_record.json --output output/skill_runs/reviewable_sound_report.md
apr packs --pack-path fixtures/external_packs/apr-pack-physics --pack-path fixtures/external_packs/apr-pack-clinical
```

## Contract-Focused Validation

```powershell
python scripts/validate_contract.py
python -m pytest tests/contract/test_active_schemas.py tests/contract/test_contract_manifest.py
python -m pytest tests/surface_lock/test_output_surfaces.py
```

## Fixture and Pack Runs

```powershell
apr audit fixtures/inputs/theory_pack_case.json --pack-path fixtures/external_packs/apr-pack-physics --output output/skill_runs/theory_pack_record.json
apr audit fixtures/inputs/clinical_pack_readiness_case.json --pack-path fixtures/external_packs/apr-pack-clinical --output output/skill_runs/clinical_pack_record.json
apr packs --pack-path fixtures/external_packs/apr-pack-physics
apr packs --pack-path fixtures/external_packs/apr-pack-clinical
```

## Goldset Runs

Prefer the main subcommand surface and verify manifest location before overriding it.

```powershell
apr goldset --output output/skill_runs/goldset_summary.json
apr goldset --holdout --no-ledger --output output/skill_runs/holdout_summary.json
python scripts/validate_goldset.py --summary output/skill_runs/goldset_summary.json --ledger benchmarks/goldset/output/calibration_ledger.jsonl
```

If you must override the manifest explicitly, verify the current executable path first in `src/apr_core/cli.py`:

```powershell
apr goldset --manifest benchmarks/goldset_dev/manifest.yaml --output output/skill_runs/goldset_summary.json
apr goldset --manifest benchmarks/goldset_holdout/manifest.yaml --holdout --no-ledger --output output/skill_runs/holdout_summary.json
```

## Targeted Test Commands

```powershell
python -m pytest tests/regression/test_cli_smoke.py
python -m pytest tests/regression/test_pack_loading.py
python -m pytest tests/surface_lock/test_output_surfaces.py
python -m pytest tests/goldset/test_goldset_runner.py
```

## Release Readiness

```powershell
git status --short
python scripts/validate_contract.py
python scripts/validate_goldset.py
python -m pytest
apr goldset --output output/skill_runs/release_goldset_summary.json
python scripts/build_release.py
```

## Operational Notes

- `apr doctor` can fail with `{"status":"error","git_status":"dirty"}` on a dirty worktree. That is a repo-state signal, not necessarily a runtime defect.
- `scripts/validate_contract.py` and `scripts/validate_goldset.py` are repo-local validation entrypoints that do not require the CLI to be installed.
- Standardize on `apr <subcommand>` unless you are specifically validating wrapper entrypoints from `pyproject.toml`.
