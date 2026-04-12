# Architecture

APR v2 is a layered local pipeline built around one canonical audit kernel.

## Kernel Pipeline

1. `ingest` normalizes the manuscript package and grades input sufficiency.
2. `parse` extracts claim candidates, anchors, novelty candidates, and support objects.
3. `classify` infers article type, claim type, domain module, and outlet profile.
4. `reviewability`, `transparency`, `integrity`, `structural_integrity`, `claim_evidence_calibration`, `adversarial_resilience`, and `scientific_record` produce threshold assessments.
5. `venue` calibrates outlet routing only after the scientific-record threshold is known.
6. `rehabilitation` turns failure states into a ranked repair path.
7. `packs` load only by explicit path and remain advisory-only.
8. `render` consumes the canonical record and never mutates it.

`CanonicalAuditRecord` is the only durable runtime truth object. The active CLI and pipeline do not route through dormant provider or adapter seams unless they are explicitly admitted later.

## Sibling Artifact Layers

The Phase A/B extension adds sibling artifacts around the canonical kernel instead of expanding the kernel itself:

- `DefenseReadinessRecord`: adversarial, committee-facing strength/weakness/risk/mitigation view derived from the canonical record and optional manuscript package.
- `QuestionChallengeRecord`: typed, context-specific challenge questions derived from the canonical and defense records plus the offline registry.
- `PdfAnnotationManifest`: presentation-layer annotation manifest that links manuscript spans to strengths, weaknesses, risks, questions, and repair drilldowns.

These layers are governed by separate schemas, use `additionalProperties: false`, and are downstream-only. They do not redefine the canonical recommendation, venue routing, or escalation semantics.

## Benchmark Lanes

APR keeps benchmark governance inside the goldset harness:

- `benchmarks/goldset_dev/manifest.yaml` and `benchmarks/goldset_holdout/manifest.yaml` remain the main kernel regression lanes.
- `benchmarks/external_papers_dev/manifest.yaml` and `benchmarks/external_papers_holdout/manifest.yaml` add an external-paper dissection lane for offline calibration of claim recovery, novelty recovery, support-object recovery, risk-family recovery, question-family recovery, and anchor recovery.

The external-paper lane is additive:

- it stays offline by using fixtures and manifests rather than runtime retrieval
- it preserves development vs holdout separation
- it reports through the existing summary and ledger surfaces instead of inventing a disconnected evaluation subsystem

## Review Surface and PDF Limitations

`apr annotate-pdf` currently generates a deterministic text-facsimile viewer from the same annotation manifest used for the sibling artifact. If a source PDF path is supplied, it is recorded in the manifest and shown in the viewer, but the current MVP does not compute coordinate-true PDF overlays. The source PDF is never mutated.

## Deferrals

This architecture intentionally defers:

- full reviewer orchestration
- editorial production state machines
- copyediting, release, and post-publication operations
- OCR-dependent ingestion or annotation
- nondeterministic runtime services

See [docs/PHASE_AB_EXTENSION.md](PHASE_AB_EXTENSION.md) for the concise extension note and [docs/CANONICAL_AUDIT_RECORD.md](CANONICAL_AUDIT_RECORD.md) for the normative-kernel boundary.
