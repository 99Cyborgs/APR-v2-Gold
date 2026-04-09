# Validation

Use the smallest sufficient gate first. Escalate only when the blast radius warrants it.

## Gated Validation Matrix

| Gate | Why it exists | Minimum validation | Stronger validation when impact is larger | Pass evidence | Stop on |
| --- | --- | --- | --- | --- | --- |
| Schema validity | Prove active contract files are structurally valid | `python scripts/validate_contract.py` | `python -m pytest tests/contract/test_active_schemas.py tests/contract/test_contract_manifest.py` | command exits 0 and schemas load | invalid schema, version mismatch, missing active file |
| Canonical record generation | Prove runtime still emits schema-valid canonical output | `apr audit fixtures/inputs/reviewable_sound_paper.json --output output/skill_runs/record.json` | add representative pack fixture runs and targeted regression tests | output JSON exists and downstream render accepts it | audit fails or output surface changes without intent |
| Renderer consumption integrity | Prove renderer consumes the canonical record without redefining meaning | `apr render output/skill_runs/record.json --output output/skill_runs/report.md` | `python -m pytest tests/surface_lock/test_output_surfaces.py tests/regression/test_cli_smoke.py` | rendered report exists and surface-lock tests pass | renderer derives new meaning, heading drift, field mismatch |
| Fixture run success | Prove representative fixtures still execute through the governed path | direct `apr audit` on affected fixtures | `python -m pytest tests/regression/test_scenarios.py tests/regression/test_pack_loading.py` | each requested fixture produces the expected artifact | fixture behavior unexplained or pack path fails |
| Benchmark / goldset stability | Prove benchmark schemas, runner, and governance outputs remain usable | `python scripts/validate_goldset.py` and `apr goldset --output output/skill_runs/goldset_summary.json` | validate summary and ledger with `python scripts/validate_goldset.py --summary ... --ledger ...`; add goldset tests | summary exists, validation passes, benchmark gate status is acceptable for the task | manifest ambiguity, gate failure, ledger invalid |
| No contract drift without explicit intent | Prevent silent schema/policy meaning changes | diff review of `contracts/active/*` plus contract validation | contract tests + impacted runtime/render tests + docs inspection | explicit blast-radius note and synchronized surfaces | contract meaning changed implicitly |
| No venue routing before scientific-record gate | Preserve core doctrine | inspect `src/apr_core/pipeline.py` when touched | `python -m pytest tests/surface_lock/test_output_surfaces.py tests/regression/test_scenarios.py` and representative blocking fixtures | scientific-record assessment still precedes `route_venue`, and blocked cases stay blocked | bypass path or reordered logic |
| No advisory-pack leakage into core semantics | Preserve optional external advisory logic | `apr packs --pack-path <pack_dir>` and one `apr audit ... --pack-path <pack_dir>` run | `python -m pytest tests/regression/test_pack_loading.py tests/surface_lock/test_output_surfaces.py` | pack loads explicitly and recommendation semantics remain core-owned | pack rewrites core decision meaning or auto-loads |

## Validation Order

1. Confirm repo root, authority files, and touched paths.
2. Run the narrowest contract or runtime validation that matches the touched surface.
3. Run a fixture-based audit receipt when runtime or schemas are in play.
4. Run renderer or pack validation only if those surfaces were touched or consumed.
5. Run goldset validation when canonical output, benchmark surfaces, or benchmark-governed behavior changed.
6. Run full `python -m pytest` only when change breadth justifies it.
7. Run `python scripts/build_release.py` only for release-readiness work and only on a clean worktree.

## Required Reporting

For every run, record:

- exact command
- cwd
- key input paths
- key output paths
- pass/fail result
- what was not validated and why

If `apr doctor` fails only because the git worktree is dirty, record that explicitly and do not overstate it as a runtime defect.
