from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from apr_core.utils import read_json  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/summarize_goldset.py <summary.json>")
    summary = read_json(sys.argv[1])
    print(f"total_cases={summary['total_cases']} passed={summary['passed']} failed={summary['failed']}")
    for partition, stats in summary["partitions"].items():
        print(f"{partition}: total={stats['total']} passed={stats['passed']} failed={stats['failed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
