# Gold-Set Protocol

The gold-set is the executable benchmark surface for APR v2.

- Each case declares expected labels.
- Cases are partitioned into `core_structural`, `venue_calibration`, `adversarial`, `pack_specific`, and `holdout`.
- The runner reports exact field mismatches rather than a single opaque pass/fail.
- Holdout structure exists even when holdout volume is still small.

Gold-set output is evidence about rule behavior, not proof of editorial calibration beyond the declared cases.
