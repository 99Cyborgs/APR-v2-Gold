# Pack Interface

Packs are external repos discovered by explicit path. They must expose `pack.yaml`, declare their supported domains, and provide a Python builder that returns a `PackSpec`.

APR v2 core guarantees:

- path-based discovery only
- canonicalized and deduplicated resolved pack paths before load
- explicit metadata capture in `pack_execution`
- explicit applicability reporting
- scoped advisory results under `pack_results`

Packs may:

- add signals
- add scoped fatal-gate requests as advisory pack requests only
- request human escalation
- lower confidence indirectly through recorded uncertainty

Pack fatal-gate requests are recorded under `pack_results[*].fatal_gates` as advisory metadata only. They may justify warnings or human escalation, but they do not participate in core recommendation selection and they do not override APR's scientific-record or recommendation state machines.

Packs may not:

- redefine core scientific-record criteria
- rewrite outlet-profile semantics
- silently overwrite core recommendations
