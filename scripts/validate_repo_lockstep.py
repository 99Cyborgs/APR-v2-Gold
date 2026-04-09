from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        raise SystemExit(completed.returncode)


def main() -> int:
    _run("scripts/validate_contract.py")
    _run("scripts/validate_goldset.py")
    _run("-m", "pytest", "tests/regression/test_cli_smoke.py", "tests/goldset/test_holdout_split_isolation.py", "-q")
    print("repo lockstep validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
