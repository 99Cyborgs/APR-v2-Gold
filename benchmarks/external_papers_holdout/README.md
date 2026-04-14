# External Paper Holdout Lane

This manifest keeps external-paper calibration separate from development tuning.

Run it with:

```bash
apr goldset --manifest benchmarks/external_papers_holdout/manifest.yaml --holdout --no-ledger
```

## Holdout Rules

- Cases in this manifest remain outside development tuning.
- The normal holdout masking path applies to recommendation and external-dissection surfaces.
- Public summaries expose only masked holdout placeholders rather than the hidden expectation content.

Use this lane to detect drift in external-paper dissection quality without letting development edits tune directly against the hidden cases.
