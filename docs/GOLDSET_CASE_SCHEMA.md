# Goldset Case Schema

APR v2 Goldset cases are declared in `benchmarks/goldset_dev/manifest.yaml` for development runs and `benchmarks/goldset_holdout/manifest.yaml` for blind holdout runs. Both manifests are validated by `benchmarks/goldset/schemas/manifest.schema.json`.

## Case Shape

```yaml
- case_id: reviewable_sound_paper
  split: dev
  stratum: core_gold
  partition: core_structural
  category: reviewable_baseline
  case_state: active
  gate_behavior: hard
  central_claim: We present a calibration routine for low-cost satellite thermal sensors and show that it reduces drift by 18% relative to the current baseline.
  claim_type: benchmark_claim
  input: reviewable_sound_paper.json
  pack_paths: []
  expected_decision:
    recommendation: PLAUSIBLE_SEND_OUT
    recommendation_band: viable_journal
    human_escalation_required: false
  expected:
    exact:
      parsing.central_claim: ...
      classification.article_type: ...
      classification.claim_type: ...
      classification.domain_module: ...
      classification.outlet_profile: ...
      reviewability.status: ...
      scientific_record.status: ...
      integrity.status: ...
      venue.routing_state: ...
      decision.recommendation: ...
      decision.human_escalation_required: ...
  required_nonempty_paths:
    - parsing.central_claim_anchor
  rationale: Why this case exists.
  tags:
    - routing
  ambiguity_class: none
```

## Required Governance Fields

- `case_id`: stable benchmark identifier.
- `split`: execution lane, currently `dev` or `holdout`.
- `stratum`: `core_gold`, `stress_gold`, or `holdout`.
- `partition`: mechanism-oriented grouping used in summaries.
- `category`: case-local analytic label.
- `case_state`: `active` or `scaffold`.
- `gate_behavior`: `hard`, `monitor`, or `exclude`.
- `central_claim`: APR v4-aligned alias for the benchmarked central claim expectation.
- `claim_type`: APR v4-aligned alias for the benchmarked claim-type expectation.
- `input`: fixture path relative to `case_root` for active cases.
- `expected_decision`: APR v4-aligned editorial primitive for expected recommendation state and escalation state.
- `rationale`: brief machine-adjacent human explanation for why the case exists.
- `tags`: analytic labels used by gate logic and summaries.
- `ambiguity_class`: explicit border-case marker when needed.

## Expected Output Surface

`expected.exact` is intentionally limited to stable canonical-record surfaces:

- `parsing.central_claim`
- `classification.article_type`
- `classification.claim_type`
- `classification.domain_module`
- `classification.outlet_profile`
- `reviewability.status`
- `scientific_record.status`
- `integrity.status`
- `venue.routing_state`
- `decision.recommendation`
- `decision.human_escalation_required`

Use `required_nonempty_paths` for anchor-bearing or pack-bearing surfaces that must exist but are not better expressed as exact scalar equality.

## Recommendation Bands

When exact recommendation equality is too rigid, `expected.recommendation_band` may be used instead of `decision.recommendation`.

Supported bands:

- `fatal_block`
- `non_reviewable`
- `repair_required`
- `viable_with_reroute`
- `preprint_only`
- `cautionary_viable`
- `viable_journal`

## Summary Output Extensions

Run summaries now emit additional editorial-engine surfaces:

- `decision_algebra`: weighted decision score totals, recommendation-loss totals, and forecast counts.
- `decision_consistency`: exact and band-level agreement between observed and expected decisions.
- `system_diagnostics`: category, stratum, and gate-behavior aggregates plus drift flags.
- `regression_governor`: rolling-ledger baseline comparison for fatal-error growth and new `core_gold` failure classes.
- `editorial_plausibility_flags`: per-case and aggregate plausibility signals derived from recommendation bias and mechanism-level error classes.

## Scaffold Cases

- Scaffold cases reserve future coverage but do not execute.
- Scaffold cases must use `case_state: scaffold` and `gate_behavior: exclude`.
- Scaffold cases are allowed only when the repo lacks a real untuned public fixture.
