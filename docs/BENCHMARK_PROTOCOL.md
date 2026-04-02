# Benchmark Protocol

The benchmark harness evaluates APR v2 against declared expectations.

- Input fixtures are immutable test assets.
- The manifest defines partitions, case metadata, expected labels, and optional pack paths.
- A case fails when any declared expected field mismatches or required non-empty fields are empty.
- Summaries are reported both globally and by partition so venue drift and pack drift are visible.
