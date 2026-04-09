# Development

- Install with `python -m pip install -e .[dev]`.
- Run the minimum pre-merge lockstep gate with `python scripts/validate_repo_lockstep.py`.
- Validate contracts with `python scripts/validate_contract.py`.
- Validate benchmark governance with `python scripts/validate_goldset.py`.
- Run tests with `python -m pytest`.
- Run the benchmark harness with `apr goldset --output output/goldset_summary.json`.
- Use `apr doctor` for runtime/repo wiring checks and `apr readiness` for clean-worktree release readiness.
- Inspect benchmark policy in `docs/BENCHMARK_POLICY.md` and case structure in `docs/GOLDSET_CASE_SCHEMA.md`.
- Use fixture inputs under `fixtures/inputs/` for reproducible local runs.
