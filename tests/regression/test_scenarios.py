from pathlib import Path
import sys

import pytest

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

from apr_core.pipeline import run_audit
from apr_core.utils import read_json


@pytest.mark.parametrize(
    ("fixture", "path", "expected"),
    [
        ("abstract_only_fragment.json", "decision.recommendation", "NON_REVIEWABLE"),
        ("non_reviewable_speculative_paper.json", "scientific_record.status", "fatal_fail"),
        ("venue_mismatched_selective.json", "venue.routing_state", "retarget_specialist"),
        ("null_replication_case.json", "classification.claim_type", "replication_claim"),
        ("preprint_ready_only.json", "decision.recommendation", "PREPRINT_READY_NOT_JOURNAL_READY"),
        ("integrity_escalation.json", "integrity.status", "escalate"),
    ],
)
def test_scenario_expectations(fixture: str, path: str, expected: str):
    record = run_audit(read_json(ROOT / "fixtures" / "inputs" / fixture))
    current = record
    for part in path.split("."):
        current = current[part]
    assert current == expected
