from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

from apr_core.goldset.attribution_identifiability import (  # noqa: E402
    compute_conditional_importance,
    compute_interaction_matrix,
    detect_non_identifiability,
)


def test_correlated_features_trigger_non_unique_identifiability():
    features = ["x1", "x2"]
    model = lambda row: row["x1"] + row["x2"] + 0.25 * row["x1"] * row["x2"]
    data = {"x1": 1.0, "x2": 1.0}

    conditional = compute_conditional_importance(features, model, data)
    interaction_matrix = compute_interaction_matrix(features, model)
    identifiability = detect_non_identifiability(
        {
            "conditional_importance": conditional,
            "interaction_matrix": interaction_matrix,
        }
    )

    assert conditional["x1"] == conditional["x2"]
    assert abs(interaction_matrix["x1"]["x2"]) > 0
    assert identifiability == "correlated"
