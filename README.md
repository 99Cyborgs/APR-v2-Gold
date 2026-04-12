# APR v2 Gold

## Current State

- `APR v2 Gold` is a deterministic, contract-driven manuscript-audit engine packaged as `apr-v2` with the `apr` CLI.
- The active runtime lives in `src/apr_core/`, and the active contract and policy layer live in `contracts/active/`.
- `CanonicalAuditRecord` remains the only normative audit kernel. `apr audit` still emits that record, and downstream layers consume it without mutating its recommendation semantics.
- The CLI now supports repo/runtime validation (`apr doctor`), release readiness checks (`apr readiness`), audit execution (`apr audit`), markdown rendering (`apr render`), defense-readiness generation (`apr defense`), typed challenge-question generation (`apr questions`), text-facsimile review annotation output (`apr annotate-pdf`), benchmark execution (`apr goldset`), and advisory-pack inspection (`apr packs`).
- The benchmark harness now includes the core development and holdout manifests plus an additive external-paper calibration lane in `benchmarks/external_papers_dev/manifest.yaml` and `benchmarks/external_papers_holdout/manifest.yaml`.
- The primary kernel regression manifests remain `benchmarks/goldset_dev/manifest.yaml` and `benchmarks/goldset_holdout/manifest.yaml`.

## Goal

- Turn a normalized manuscript package into one canonical audit record.
- Keep the runtime offline, deterministic, and schema-governed.
- Add defense, challenge, and review visibility as sibling artifacts rather than silently broadening the canonical kernel into a publisher or reviewer OS.

## Canonical vs Derived

- `CanonicalAuditRecord` is the source of truth for audit semantics, gates, routing, recommendation, confidence, and escalation.
- `DefenseReadinessRecord`, `QuestionChallengeRecord`, and `PdfAnnotationManifest` are derived sibling artifacts. They are schema-validated, consume the canonical record, and never rewrite canonical recommendation meaning.
- The external-paper lane is benchmark-only. It calibrates dissection quality against offline fixtures and does not inject untracked heuristics into live audit decisions.

See also:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/CANONICAL_AUDIT_RECORD.md](docs/CANONICAL_AUDIT_RECORD.md)
- [docs/PHASE_AB_EXTENSION.md](docs/PHASE_AB_EXTENSION.md)
- [docs/QUESTION_REGISTRY_GUIDANCE.md](docs/QUESTION_REGISTRY_GUIDANCE.md)

## Core Commands

Canonical audit:

```bash
apr audit fixtures/inputs/reviewable_sound_paper.json --output out/canonical.json
apr render out/canonical.json --output out/report.md
```

Defense and challenge layers:

```bash
apr defense out/canonical.json \
  --manuscript-package fixtures/inputs/reviewable_sound_paper.json \
  --context journal_referee \
  --output out/defense.json

apr questions out/canonical.json \
  --manuscript-package fixtures/inputs/reviewable_sound_paper.json \
  --defense out/defense.json \
  --context journal_referee \
  --output out/questions.json
```

Single-view review surface:

```bash
apr annotate-pdf out/canonical.json \
  --manuscript-package fixtures/inputs/reviewable_sound_paper.json \
  --defense out/defense.json \
  --questions out/questions.json \
  --source-pdf path/to/manuscript.pdf \
  --output-dir out/review_surface
```

Current viewer behavior:

- The generated review surface is deterministic and static.
- It highlights strengths, weaknesses, risks, questions, and repair notes in one text-facsimile view.
- If `--source-pdf` is supplied, the manifest records the PDF path, but the current MVP does not compute PDF coordinates or mutate the PDF itself.

## External-Paper Calibration Lane

Development lane:

```bash
apr goldset --manifest benchmarks/external_papers_dev/manifest.yaml --no-ledger
```

Holdout lane:

```bash
apr goldset --manifest benchmarks/external_papers_holdout/manifest.yaml --holdout --no-ledger
```

The external-paper lane is additive and governed:

- it preserves development vs holdout separation
- it scores dissection recovery inside the goldset harness instead of through an untracked side channel
- it stays offline by using fixture/manifests rather than live paper retrieval
- it keeps packs advisory-only

See:

- [benchmarks/external_papers_dev/README.md](benchmarks/external_papers_dev/README.md)
- [benchmarks/external_papers_holdout/README.md](benchmarks/external_papers_holdout/README.md)
- [fixtures/external_papers/README.md](fixtures/external_papers/README.md)

## Provenance and Legal Constraints

- External-paper fixtures in `fixtures/external_papers/` are synthetic normalized packages authored for deterministic benchmark use.
- This patch does not commit copyrighted full-text papers as benchmark corpus material.
- New external-paper cases should prefer synthetic packages, public-domain text, or clearly licensed author-provided material, with provenance documented alongside the fixtures.

## Intentionally Deferred

- full reviewer orchestration
- editorial production or release state machines
- post-publication and portfolio layers
- OCR-dependent PDF processing
- nondeterministic model or network calls in normal execution
