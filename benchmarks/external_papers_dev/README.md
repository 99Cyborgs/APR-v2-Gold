# External Paper Calibration Lane

This manifest extends `apr goldset` with an offline external-paper dissection lane. It is a development calibration lane, not a replacement for the core goldset manifests.

Run it with:

```bash
apr goldset --manifest benchmarks/external_papers_dev/manifest.yaml --no-ledger
```

## What It Measures

Each case may declare an additive `expected_external` block for deterministic dissection scoring, including:

- central-claim recovery
- novelty-delta recovery
- first hard-object kind recovery
- decisive support-object kind recovery
- risk-family recovery
- question-family recovery
- strength and weakness anchor recovery

The runner reports these metrics through the normal goldset summary surface under `external_dissection_summary`.

## Governance Rules

- This lane stays inside the existing goldset harness.
- It preserves development vs holdout separation.
- It does not alter canonical recommendation semantics.
- It does not allow packs to mutate core decisions.
- It uses normalized fixtures rather than runtime network retrieval.

## Adding Cases

1. Add a normalized package under `fixtures/external_papers/`.
2. Add the case to this manifest with `split: dev`.
3. Keep `expected.external` or `expected.exact` surfaces scoped to deterministic fields.
4. Use `expected_external` only for benchmarked external dissection targets.
5. Keep legal provenance documented in [fixtures/external_papers/README.md](../../fixtures/external_papers/README.md).
