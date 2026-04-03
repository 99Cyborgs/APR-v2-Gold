# Calibration Protocol

APR v2 separates implementation from calibration.

1. Freeze contract semantics.
2. Validate the goldset manifest with `python scripts/validate_goldset.py`.
3. Run `apr goldset` and inspect the machine-readable summary plus the calibration ledger.
4. Bucket misses by `error_class`, not only by case id.
5. Change heuristics intentionally.
6. Re-run the harness and compare `case_deltas`, recommendation transitions, decision consistency, and gate status.
7. Check the rolling regression governor and cross-case drift diagnostics before claiming improvement.
8. Do not treat `stress_gold` visibility as equivalent to `core_gold` authority.

No README, report, or CLI text may imply stable editorial priors without benchmark evidence.
