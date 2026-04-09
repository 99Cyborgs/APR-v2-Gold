# Release Policy

Releases are built from the active manifest version and from a clean checkout only.

- `scripts/build_release.py` reads `contracts/active/manifest.yaml`.
- `apr doctor` validates runtime wiring but does not require a clean worktree.
- `apr readiness` and `scripts/build_release.py` enforce the clean-worktree release policy when git metadata is available.
- Runtime output, reports, and caches are excluded from release bundles.
- Contract changes require schema validation and test coverage before release packaging.
