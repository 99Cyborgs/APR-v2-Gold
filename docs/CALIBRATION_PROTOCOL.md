# Calibration Protocol

APR v2 separates implementation from calibration.

1. Freeze contract semantics.
2. Run the baseline gold-set.
3. Bucket mismatches by mechanism.
4. Change heuristics intentionally.
5. Re-run baseline and holdout partitions.
6. Document what improved and what regressed.

No README, report, or CLI text may imply stable editorial priors without benchmark evidence.
