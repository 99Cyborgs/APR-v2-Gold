# Phase A/B Extension Note

## Why the Canonical Kernel Stays Canonical

`CanonicalAuditRecord` remains the sole normative audit object because APR's deterministic kernel is the thing being benchmarked, validated, and governed. Audit gates, venue routing, recommendation semantics, confidence, and escalation continue to live there so `apr audit` stays stable and comparable over time.

## Why Defense, Questions, and Review Surfaces Are Siblings

Defense preparation, board-question generation, and manuscript annotation are downstream uses of audit truth, not replacements for it. They consume the canonical record and emit:

- `DefenseReadinessRecord`
- `QuestionChallengeRecord`
- `PdfAnnotationManifest`

Those artifacts are schema-bound, evidence-linked, and deterministic, but they are explicitly presentation or preparation layers. They do not write back into canonical fields, mutate recommendations, or use packs to alter core decisions.

The external-paper lane follows the same rule. It extends benchmark coverage for dissection quality inside `apr goldset`, but it remains an evaluation lane rather than a runtime heuristic side channel.

## What This Patch Intentionally Does Not Do

- full reviewer orchestration
- editorial workflow or production state machines
- post-publication surveillance
- portfolio or lab-level management layers
- OCR-dependent PDF overlay infrastructure
- live paper retrieval or nondeterministic model calls
