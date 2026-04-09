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
        ("preprint_ready_only.json", "decision.recommendation", "REBUILD_BEFORE_SUBMISSION"),
        ("integrity_escalation.json", "integrity.status", "escalate"),
        ("aps_selective_letters_case.json", "decision.recommendation", "SUBMIT_WITH_CAUTION"),
        ("holdout_systematic_review_case.json", "classification.outlet_profile", "review_only_venue"),
        ("selective_null_result_case.json", "decision.recommendation", "RETARGET_SOUNDNESS_FIRST"),
        ("protocol_preprint_ready_case.json", "decision.recommendation", "PREPRINT_READY_NOT_JOURNAL_READY"),
        ("computational_simulation_revision_case.json", "decision.recommendation", "REVISE_BEFORE_SUBMISSION"),
        ("review_synthesis_case.json", "decision.recommendation", "PLAUSIBLE_SEND_OUT"),
        ("case_report_hardware_anomaly.json", "decision.recommendation", "PLAUSIBLE_SEND_OUT"),
        ("editorial_policy_note_case.json", "decision.recommendation", "REBUILD_BEFORE_SUBMISSION"),
        ("clinical_pack_readiness_case.json", "decision.recommendation", "PLAUSIBLE_SEND_OUT"),
    ],
)
def test_scenario_expectations(fixture: str, path: str, expected: str):
    record = run_audit(read_json(ROOT / "fixtures" / "inputs" / fixture))
    current = record
    for part in path.split("."):
        current = current[part]
    assert current == expected


def test_computational_simulation_revision_case_exercises_missing_code_pathway():
    record = run_audit(read_json(ROOT / "fixtures" / "inputs" / "computational_simulation_revision_case.json"))

    assert record["classification"]["domain_module"] == "computational_or_simulation"
    assert record["transparency"]["status"] == "missing"
    assert record["scientific_record"]["status"] == "repairable_fail"
    assert "transparency_or_reporting_incomplete" in record["scientific_record"]["repairable_failures"]
    assert record["decision"]["recommendation"] == "REVISE_BEFORE_SUBMISSION"


def test_review_synthesis_case_routes_through_review_only_venue():
    record = run_audit(read_json(ROOT / "fixtures" / "inputs" / "review_synthesis_case.json"))

    assert record["classification"]["article_type"] == "review"
    assert record["classification"]["domain_module"] == "review_synthesis"
    assert record["classification"]["outlet_profile"] == "review_only_venue"
    assert record["decision"]["recommendation"] == "PLAUSIBLE_SEND_OUT"


def test_editorial_policy_note_case_remains_assessable_but_requires_rebuild():
    record = run_audit(read_json(ROOT / "fixtures" / "inputs" / "editorial_policy_note_case.json"))

    assert record["classification"]["article_type"] == "editorial_or_opinion"
    assert record["reviewability"]["status"] == "pass"
    assert record["scientific_record"]["status"] == "repairable_fail"
    assert "structural_integrity_below_editorial_threshold" in record["scientific_record"]["repairable_failures"]
    assert record["decision"]["recommendation"] == "REBUILD_BEFORE_SUBMISSION"


def test_clinical_pack_case_routes_cleanly_without_pack_interference():
    payload = read_json(ROOT / "fixtures" / "inputs" / "clinical_pack_readiness_case.json")
    baseline = run_audit(payload)
    with_pack = run_audit(payload, pack_paths=[str(ROOT / "fixtures" / "external_packs" / "apr-pack-clinical")])

    assert baseline["classification"]["domain_module"] == "clinical_or_human_subjects"
    assert baseline["decision"]["recommendation"] == "PLAUSIBLE_SEND_OUT"
    assert with_pack["decision"]["recommendation"] == baseline["decision"]["recommendation"]
    assert with_pack["pack_execution"]["pack_load_failures"] == []
    assert with_pack["pack_results"][0]["pack_id"] == "clinical_pack"
    assert with_pack["pack_results"][0]["status"] == "pass"


def test_clinical_pack_returns_not_applicable_on_non_clinical_case():
    payload = read_json(ROOT / "fixtures" / "inputs" / "reviewable_sound_paper.json")
    baseline = run_audit(payload)
    with_pack = run_audit(payload, pack_paths=[str(ROOT / "fixtures" / "external_packs" / "apr-pack-clinical")])

    assert with_pack["decision"]["recommendation"] == baseline["decision"]["recommendation"] == "PLAUSIBLE_SEND_OUT"
    assert with_pack["pack_execution"]["pack_load_failures"] == []
    assert with_pack["pack_results"][0]["pack_id"] == "clinical_pack"
    assert with_pack["pack_results"][0]["applicability"] == "not_applicable"
    assert with_pack["pack_results"][0]["status"] == "not_applicable"
