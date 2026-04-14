# Migration Policy

APR v2 does not silently inherit legacy APR layouts or contracts.

- Legacy material is reference context only.
- Any future compatibility adapter must be explicit, versioned, and isolated under `contracts/legacy/` plus adapter code.
- No compatibility adapter is active in the current runtime path.
- Migration work must preserve the v2 canonical record semantics rather than contort v2 around older outputs.
- Any future provider or adapter admission must be explicit in docs and tests before code activation; placeholder modules or dormant protocols do not count as runtime approval.
