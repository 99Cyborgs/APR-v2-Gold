# Contract Policy

- `contracts/active/` contains the only runtime-loadable contract surface.
- `contracts/legacy/` is archival only.
- Contract version and policy-layer version are explicit and must match runtime expectations.
- Renderers consume canonical output and do not redefine it.
- Schema or policy edits require matching updates to docs, tests, and the gold-set harness.
