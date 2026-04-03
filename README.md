# APR v2 Gold

APR v2 Gold is the public repository foundation for APR v2, a deterministic manuscript-audit engine. It extracts a recoverable central claim, evaluates reviewability, evaluates scientific-record readiness, routes only after the scientific-record gate, and produces one canonical audit record that every renderer and harness consumes.

The public repository label is `APR v2 Gold`. The installable package remains `apr-v2`, and the supported CLI remains `apr`.

APR v2 is not a journal submission bot, reviewer assignment system, collaboration surface, or misconduct adjudicator. Domain-specific logic stays outside core semantics and is loaded only through advisory packs.

## Repo Boundary

- `src/apr_core/` contains the deterministic local runtime.
- `contracts/active/` contains the only loadable runtime contract.
- `benchmarks/goldset/` contains the benchmark harness manifest.
- `fixtures/external_packs/` contains a sample advisory pack scaffold for path-based loading.
- Generated reports, runtime output, release bundles, caches, and local state are excluded from git.

## Active Contract

- Canonical input schema: `contracts/active/audit_input.schema.json`
- Canonical output schema: `contracts/active/canonical_audit_record.schema.json`
- Active manifest: `contracts/active/manifest.yaml`
- Active policy layer: `contracts/active/policy_layer.yaml`

Renderers consume canonical records and may not redefine their meaning.

## CLI

Install in editable mode and use the `apr` command:

```bash
python -m pip install -e .[dev]
apr doctor
apr audit fixtures/inputs/reviewable_sound_paper.json --output output/reviewable_record.json
apr render output/reviewable_record.json --output output/reviewable_report.md
apr goldset --output output/goldset_summary.json
apr packs --pack-path fixtures/external_packs/apr-pack-physics
```

## Deterministic Flow

1. Normalize the manuscript package.
2. Extract claim candidates, anchors, and support objects.
3. Infer article type, claim type, domain module, and outlet profile.
4. Apply the reviewability gate.
5. Apply the scientific-record gate.
6. Route through venue logic only if the scientific-record gate allows it.
7. Build a ranked rehabilitation plan.
8. Execute explicitly requested advisory packs.
9. Emit a schema-valid `CanonicalAuditRecord`.
10. Render markdown from that canonical record only.

## Calibration Honesty

APR v2 ships with a real gold-set harness, but it does not claim calibrated editorial priors beyond the included fixtures. Benchmark output is explicit about what was tested, what matched expectations, and what remains holdout-only scaffolding.
