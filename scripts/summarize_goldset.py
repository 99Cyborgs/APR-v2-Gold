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
    print(
        " ".join(
            [
                f"evaluation_mode={summary.get('evaluation_mode', 'development')}",
                f"total_cases={summary['total_cases']}",
                f"passed={summary['passed']}",
                f"failed={summary['failed']}",
                f"scaffold={summary.get('scaffold_cases', 0)}",
                f"gate_status={summary.get('gates', {}).get('status', 'unknown')}",
                f"total_score={summary.get('decision_algebra', {}).get('total_score', 'unknown')}",
            ]
        )
    )
    decision_consistency = summary.get("decision_consistency", {})
    if decision_consistency:
        print(
            " ".join(
                [
                    f"decision_consistency={decision_consistency.get('consistency_rate', 'unknown')}",
                    f"exact={decision_consistency.get('exact_match_cases', 0)}",
                    f"band={decision_consistency.get('band_match_cases', 0)}",
                    f"mismatch={decision_consistency.get('mismatch_cases', 0)}",
                ]
            )
        )
    editorial_first_pass = summary.get("editorial_first_pass_score", {})
    if editorial_first_pass:
        print(
            " ".join(
                [
                    f"editorial_first_pass={editorial_first_pass.get('mean_total', 'unknown')}",
                    f"abstract={editorial_first_pass.get('mean_abstract_clarity', 'unknown')}",
                    f"novelty={editorial_first_pass.get('mean_novelty_explicitness', 'unknown')}",
                    f"evidence={editorial_first_pass.get('mean_evidence_visibility', 'unknown')}",
                ]
            )
        )
    if summary.get("error_class_counts"):
        print(f"error_classes={summary['error_class_counts']}")
    for stratum, stats in summary.get("strata", {}).items():
        print(
            f"stratum:{stratum}: total={stats['total']} passed={stats['passed']} failed={stats['failed']} scaffold={stats['scaffold']}"
        )
    for partition, stats in summary["partitions"].items():
        print(f"{partition}: total={stats['total']} passed={stats['passed']} failed={stats['failed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
