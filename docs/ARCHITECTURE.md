# Architecture

APR v2 is a layered local pipeline.

1. `ingest` normalizes the manuscript package and grades input sufficiency.
2. `parse` extracts claim candidates, anchors, and support objects.
3. `classify` infers article type, claim type, domain module, and outlet profile.
4. `reviewability`, `transparency`, `integrity`, and `scientific_record` produce threshold assessments.
5. `venue` converts scientific-record output into outlet-profile routing without redefining scientific validity.
6. `rehabilitation` turns failures or mismatches into a ranked corrective path.
7. `packs` loads optional external repos by explicit path and records advisory outputs.
8. `render` consumes the canonical record and never mutates it.

The only durable runtime truth object is `CanonicalAuditRecord`.
Provider and adapter seams remain dormant until explicitly admitted; the active CLI and pipeline do not route through `src/apr_core/providers/` or `src/apr_core/adapters/`.
