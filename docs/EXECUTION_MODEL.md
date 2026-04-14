# Execution Model

APR v2 is deterministic and local-only.

- No network access is required for normal execution.
- No external model provider is called in the initial build.
- The pipeline order is fixed and documented in code and contract.
- Canonical audit provenance stops at `PACKS_EXECUTED`; rendering remains a downstream consumer step.
- Every decision surface includes anchors or explicit uncertainty when the visible evidence is thin.
- Packs execute after core rehabilitation planning and cannot rewrite core recommendation semantics.
- Provider and adapter packages are reserved seams only and are not part of the active runtime path.
- No provider or adapter seam may enter the active runtime path without an explicit future change that updates doctrine docs, adds validation coverage, and preserves deterministic local-only execution.
