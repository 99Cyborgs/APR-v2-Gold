# Pack Interface

Packs are external repos discovered by explicit path. They must expose `pack.yaml`, declare their supported domains, and provide a Python builder that returns a `PackSpec`.

APR v2 core guarantees:

- path-based discovery only
- explicit metadata capture in `pack_execution`
- explicit applicability reporting
- scoped advisory results under `pack_results`

Packs may:

- add signals
- add scoped fatal-gate requests
- request human escalation
- lower confidence indirectly through recorded uncertainty

Packs may not:

- redefine core scientific-record criteria
- rewrite outlet-profile semantics
- silently overwrite core recommendations
