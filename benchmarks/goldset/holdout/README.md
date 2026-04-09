# Holdout

APR v2 Gold keeps the `holdout` stratum explicit and active through `benchmarks/goldset_holdout/manifest.yaml`, alongside the default development lane in `benchmarks/goldset_dev/manifest.yaml`.

This directory is a compatibility placeholder only. It does not own executable holdout fixtures or manifest state.

Active blind-evaluation cases resolve through the holdout manifest into `fixtures/inputs/`, and development runs continue to exclude them by default.
