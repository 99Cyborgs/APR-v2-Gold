# APR Clinical Pack

This fixture pack demonstrates a second advisory-pack family under the APR v2 path-based pack contract.

- It applies only to `clinical_or_human_subjects`.
- It emits additive advisory signals and warnings.
- It can return `not_applicable` through APR's core pack normalization path.
- It does not rewrite core scientific-record or recommendation semantics.

The pack is intentionally narrow. It looks for a visible cohort surface, a declared endpoint surface, and a clinical safety or adverse-event surface.
