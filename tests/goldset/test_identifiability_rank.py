from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

from apr_core.goldset.governance.attribution_identifiability import build_counterfactual_summary  # noqa: E402


def test_identifiability_marks_rank_deficient_counterfactuals_as_degenerate():
    summary = build_counterfactual_summary(
        [
            {"feature": "x1", "delta_loss": 0.0, "delta_residual": 0.0},
            {"feature": "x2", "delta_loss": 0.0, "delta_residual": 0.0},
        ],
        stability=1.0,
    )

    assert summary["attribution_rank"] < 2
    assert summary["identifiability_status"] == "degenerate"
    assert summary["conditional_importance"] == {"x1": 0.0, "x2": 0.0}
