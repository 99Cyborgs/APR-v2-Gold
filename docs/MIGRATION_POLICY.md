# Migration Policy

APR v2 does not silently inherit legacy APR layouts or contracts.

- Legacy material is reference context only.
- Any future compatibility adapter must be explicit, versioned, and isolated under `contracts/legacy/` plus adapter code.
- Migration work must preserve the v2 canonical record semantics rather than contort v2 around older outputs.
