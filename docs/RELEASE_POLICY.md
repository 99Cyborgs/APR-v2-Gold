# Release Policy

Releases are built from the active manifest version and from a clean checkout only.

- `scripts/build_release.py` reads `contracts/active/manifest.yaml`.
- Dirty worktrees are rejected when git metadata is available.
- Runtime output, reports, and caches are excluded from release bundles.
- Contract changes require schema validation and test coverage before release packaging.
