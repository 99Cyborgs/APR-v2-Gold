from pathlib import Path
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

from apr_core.pipeline import run_audit
from apr_core.utils import read_json


def test_advisory_pack_loads_and_records_scoped_output():
    payload = read_json(ROOT / "fixtures" / "inputs" / "theory_pack_case.json")
    baseline = run_audit(payload)
    pack_root = ROOT / "fixtures" / "external_packs" / "apr-pack-physics"
    record = run_audit(payload, pack_paths=[str(pack_root), str(pack_root / "pack.yaml"), str(pack_root)])
    assert record["decision"]["recommendation"] == baseline["decision"]["recommendation"] == "REBUILD_BEFORE_SUBMISSION"
    assert record["pack_execution"]["loaded_packs"]
    assert record["pack_results"]
    assert record["pack_results"][0]["pack_id"] == "physics_pack"
    assert record["pack_results"][0]["advisory_only"] is True
    assert record["pack_execution"]["requested_pack_paths"] == [str(pack_root.resolve())]
    assert record["pack_execution"]["loaded_packs"][0]["manifest_path"] == str((pack_root / "pack.yaml").resolve())
    assert record["provenance"]["loaded_pack_fingerprints"][0]["resolved_repo_root"] == str(pack_root.resolve())


def test_physics_pack_fatal_gates_remain_advisory_requests():
    payload = read_json(ROOT / "fixtures" / "inputs" / "theory_pack_case.json")
    payload["title"] = "A Hamiltonian framework for driven qubit relaxation"
    payload["abstract"] = (
        "We propose a Hamiltonian framework for driven qubit relaxation and discuss its broader conceptual implications."
    )
    payload["manuscript_text"] = (
        "The manuscript outlines a Hamiltonian formulation for driven qubit relaxation and argues for a broader "
        "reinterpretation of the problem, but it does not present a concrete experimental readout or comparator."
    )
    payload["figures_and_captions"] = ["Figure 1. Conceptual schematic of the proposed framework."]
    payload["supplement_or_appendix"] = "Appendix A sketches the formal setup."

    baseline = run_audit(payload)
    record = run_audit(payload, pack_paths=[str(ROOT / "fixtures" / "external_packs" / "apr-pack-physics")])

    assert record["decision"]["recommendation"] == baseline["decision"]["recommendation"]
    assert record["pack_results"][0]["pack_id"] == "physics_pack"
    assert record["pack_results"][0]["advisory_only"] is True
    assert record["pack_results"][0]["status"] == "fail"
    assert record["pack_results"][0]["human_escalation_required"] is True
    assert len(record["pack_results"][0]["fatal_gates"]) == 1
    assert record["pack_results"][0]["fatal_gates"][0]["code"] == "missing_observable_or_discriminating_consequence"
    assert (
        record["pack_results"][0]["fatal_gates"][0]["reason"]
        == "theory/model manuscript lacks a visible observable anchor or discriminating consequence"
    )
    assert record["pack_results"][0]["fatal_gates"][0]["scope"] == "pack_specific_advisory"
    assert record["pack_results"][0]["fatal_gates"][0]["evidence_anchors"]


def test_clinical_pack_loads_and_preserves_core_recommendation():
    payload = read_json(ROOT / "fixtures" / "inputs" / "clinical_pack_readiness_case.json")
    baseline = run_audit(payload)
    record = run_audit(payload, pack_paths=[str(ROOT / "fixtures" / "external_packs" / "apr-pack-clinical")])

    assert baseline["decision"]["recommendation"] == "PLAUSIBLE_SEND_OUT"
    assert record["decision"]["recommendation"] == baseline["decision"]["recommendation"]
    assert record["pack_execution"]["pack_load_failures"] == []
    assert record["pack_results"][0]["pack_id"] == "clinical_pack"
    assert record["pack_results"][0]["advisory_only"] is True
    assert record["pack_results"][0]["status"] == "pass"
    assert record["pack_results"][0]["fatal_gates"] == []
    assert "clinical_endpoint_surface_visible" in record["pack_results"][0]["signals"]


def test_clinical_pack_normalizes_not_applicable_result():
    payload = read_json(ROOT / "fixtures" / "inputs" / "reviewable_sound_paper.json")
    baseline = run_audit(payload)
    record = run_audit(payload, pack_paths=[str(ROOT / "fixtures" / "external_packs" / "apr-pack-clinical")])

    assert record["decision"]["recommendation"] == baseline["decision"]["recommendation"]
    assert record["pack_execution"]["pack_load_failures"] == []
    assert record["pack_results"][0]["pack_id"] == "clinical_pack"
    assert record["pack_results"][0]["applicability"] == "not_applicable"
    assert record["pack_results"][0]["status"] == "not_applicable"
