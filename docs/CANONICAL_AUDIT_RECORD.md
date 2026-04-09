# Canonical Audit Record

`CanonicalAuditRecord` is the only source-of-truth runtime output. It carries:

- contract and policy versions
- manuscript metadata
- normalized input sufficiency
- parsing outputs and anchor index
- classification outputs
- reviewability, transparency, integrity, scientific-record, venue, and rehabilitation blocks
- pack execution metadata and pack results
- final recommendation, confidence, and escalation state
- provenance and rendering metadata

Every downstream consumer, including markdown rendering and gold-set evaluation, reads this object. No renderer is permitted to reinterpret or replace the semantic meaning of any canonical field.

The canonical provenance block is now intentionally replay-oriented and audit-bounded:

- `processing_states_completed` stops at `PACKS_EXECUTED`; rendering remains downstream-only.
- `normalized_input_sha256`, `contract_manifest_sha256`, `policy_layer_sha256`, and `canonical_schema_sha256` fingerprint the deterministic runtime contract that produced the record.
- `runtime_identity` names the bootstrap entrypoint, core runtime root, and active contract root.
- `loaded_pack_fingerprints` records resolved path and manifest identity for every admitted advisory pack.
