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
