from pathlib import Path
import copy
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))
existing = sys.modules.get("apr_core")
if existing and not str(getattr(existing, "__file__", "")).startswith(str(SRC)):
    for name in list(sys.modules):
        if name == "apr_core" or name.startswith("apr_core."):
            sys.modules.pop(name, None)

from apr_core.pipeline import run_audit  # noqa: E402
from apr_core.utils import read_json  # noqa: E402


def test_polished_invalid_fixture_triggers_structural_calibration_and_adversarial_blocks():
    record = run_audit(read_json(ROOT / "fixtures" / "inputs" / "holdout_polished_invalid_simulation.json"))

    assert record["structural_integrity"]["status"] == "non_reviewable"
    assert record["structural_integrity"]["research_spine_score_8"] <= 3
    assert record["claim_evidence_calibration"]["status"] == "fatal"
    assert record["claim_evidence_calibration"]["mismatch"] >= 3
    assert record["adversarial_resilience"]["status"] == "blocked"
    assert record["adversarial_resilience"]["flag_count"] >= 6
    assert record["scientific_record"]["status"] == "fatal_fail"
    assert record["decision"]["recommendation"] == "NON_REVIEWABLE"
    assert record["decision"]["confidence"] == "low"


def test_editorial_first_pass_probability_worsens_when_clarity_and_evidence_drop():
    base_payload = read_json(ROOT / "fixtures" / "inputs" / "reviewable_sound_paper.json")
    degraded_payload = copy.deepcopy(base_payload)
    degraded_payload["title"] = "A note on calibration"
    degraded_payload["abstract"] = "We discuss a possible calibration idea."
    degraded_payload["manuscript_text"] = "The manuscript outlines a possible idea without figures, tables, or comparator detail."
    degraded_payload["figures_and_captions"] = []
    degraded_payload["tables"] = []
    degraded_payload["references"] = []
    degraded_payload["data_availability"] = None
    degraded_payload["code_availability"] = None
    degraded_payload["materials_availability"] = None

    base_record = run_audit(base_payload)
    degraded_record = run_audit(degraded_payload)

    assert degraded_record["editorial_first_pass"]["editorial_first_pass_score_32"] < base_record["editorial_first_pass"]["editorial_first_pass_score_32"]
    assert degraded_record["editorial_first_pass"]["desk_reject_probability"] > base_record["editorial_first_pass"]["desk_reject_probability"]
    assert degraded_record["decision"]["confidence"] != "high"
