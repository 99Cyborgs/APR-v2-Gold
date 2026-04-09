# Artifacts

Produce artifacts only when they are grounded in observed files, commands, and outputs.

## Architecture Summary

Minimum fields:

- authority order
- runtime, contract, renderer, benchmark, fixture, and advisory-pack surfaces
- deterministic flow summary
- unresolved path or command uncertainty

## Touched-File Impact Memo

Minimum fields:

- touched paths
- boundary class for each path cluster
- likely blast radius
- required validation by cluster
- stop conditions or explicit unknowns

## Validation Report

Minimum fields:

- commands actually run
- artifacts produced
- pass/fail by validation gate
- skipped validations and reason
- remaining risks

## Release-Readiness Report

Minimum fields:

- contract version and policy layer version observed
- git cleanliness status
- validation matrix status
- benchmark status
- release artifact status
- blockers and no-go conditions

## Advisory-Pack Scaffold Report

Minimum fields:

- target pack path
- `pack_id`, `display_name`, `supported_domains`, `advisory_only`
- files created
- explicit statement that core semantics remain unchanged
- validation commands required for explicit path loading and pack-result scoping

## Deterministic Run Receipt

Minimum fields:

- repo root
- exact command
- input fixture or manifest
- output artifact path
- contract and policy versions observed
- git status if relevant to interpretation
- pack paths, if any
- result summary

## Artifact Discipline

- Do not claim an artifact exists unless you observed the file or command output.
- Do not call rendered markdown or benchmark summaries the source of truth.
- If a required artifact was not produced, say so directly and record why.
