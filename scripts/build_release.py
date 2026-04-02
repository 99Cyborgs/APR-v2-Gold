from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from apr_core.policy import load_contract_manifest  # noqa: E402
from apr_core.utils import git_output  # noqa: E402

EXCLUDED_DIRS = {".git", ".pytest_cache", "__pycache__", "dist", "build", "output", "reports", ".apr"}


def main() -> int:
    git_code, git_msg = git_output(["rev-parse", "--is-inside-work-tree"], cwd=ROOT)
    if git_code != 0:
        raise SystemExit("release build requires a git repository with a clean checkout")

    status_code, status_output = git_output(["status", "--porcelain"], cwd=ROOT)
    if status_code != 0 or status_output:
        raise SystemExit("release build requires a clean git worktree")

    version = load_contract_manifest()["contract"]["version"]
    dist_dir = ROOT / "dist"
    dist_dir.mkdir(exist_ok=True)
    target = dist_dir / f"apr-v2-{version}.zip"

    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in ROOT.rglob("*"):
            relative = path.relative_to(ROOT)
            if any(part in EXCLUDED_DIRS for part in relative.parts):
                continue
            if path.is_dir():
                continue
            archive.write(path, relative.as_posix())

    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
