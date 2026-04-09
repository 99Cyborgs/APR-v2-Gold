# Checklists

## Pre-Edit Safety Review

- Confirm repo root and active authority files.
- Map touched paths to the boundary matrix.
- Check `git status --short` and note unrelated dirtiness.
- Identify the smallest sufficient validation gate before editing.
- Stop if contract intent or benchmark manifest location is unclear.

## Contract Edit Review

- Confirm why `contracts/active/*` must change.
- Check manifest version, policy version, and compatibility flags.
- Review downstream consumers in `src/apr_core/`.
- Re-run contract validation and targeted contract tests.
- Record blast radius and any required docs/test synchronization.

## Schema Edit Review

- List added, removed, or retyped fields.
- Check whether canonical record consumers or input producers break.
- Validate schemas and one representative emitted record.
- Verify renderer and benchmark consumers still read the intended surface.
- Stop if field meaning changed without explicit approval.

## Runtime Edit Review

- Identify the pipeline stage touched.
- Confirm scientific-record gating still precedes venue routing.
- Confirm pack logic remains advisory-only.
- Run targeted regression tests plus relevant smoke or surface-lock tests.
- Record changed fixture behavior explicitly.

## Benchmark Edit Review

- Identify whether the change affects schemas, manifests, runner logic, or docs.
- Verify manifest path assumptions before executing.
- Run `python scripts/validate_goldset.py`.
- Run at least one `apr goldset` receipt for affected surfaces.
- Stop if gate rules changed implicitly.

## Renderer Edit Review

- Confirm renderer consumes only canonical record fields.
- Check section ordering and required headings.
- Run render smoke plus `tests/surface_lock/test_output_surfaces.py`.
- Compare rendered statements against canonical values.
- Stop if renderer begins deriving semantics.

## Release Candidate Review

- Confirm clean worktree.
- Validate contract and goldset schemas.
- Run relevant tests and at least one benchmark pass.
- Build the release artifact and record the path.
- Stop if any validation lacks a receipt.

## Advisory Pack Review

- Confirm pack lives outside core semantics.
- Check `pack.yaml` metadata, `supported_domains`, and `advisory_only`.
- Verify explicit path loading with `apr packs --pack-path <pack_dir>`.
- Verify audit with `--pack-path` records scoped `pack_results`.
- Stop if the pack overwrites core recommendation meaning.
