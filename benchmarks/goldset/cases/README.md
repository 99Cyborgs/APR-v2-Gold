# Case Location Note

APR v2 keeps executable case payloads in `fixtures/inputs/`.

The goldset manifest references those fixtures directly so there is one canonical payload inventory for:

- runtime examples
- regression tests
- benchmark execution

Case governance metadata lives in the benchmark manifests under `benchmarks/goldset_dev/` and `benchmarks/goldset_holdout/`, not in duplicated fixture copies.
