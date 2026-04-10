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

from apr_core.pipeline import run_audit  # noqa: E402
from apr_core.render import render_markdown_report  # noqa: E402
from apr_core.utils import read_json  # noqa: E402

EXPECTED_TOP_LEVEL_KEYS = [
    "contract_version",
    "policy_layer_version",
    "audit_mode",
    "metadata",
    "input_sufficiency",
    "parsing",
    "classification",
    "reviewability",
    "transparency",
    "integrity",
    "structural_integrity",
    "claim_evidence_calibration",
    "adversarial_resilience",
    "scientific_record",
    "venue",
    "editorial_first_pass",
    "rehabilitation",
    "pack_execution",
    "pack_results",
    "decision",
    "provenance",
    "rendering",
]
EXPECTED_DECISION_KEYS = [
    "recommendation",
    "confidence",
    "human_escalation_required",
    "editorial_forecast",
    "author_recommendation",
]
EXPECTED_TRANSPARENCY_KEYS = [
    "status",
    "data_pathway",
    "code_pathway",
    "materials_pathway",
    "missing_items",
    "evidence_anchors",
]
EXPECTED_PROVENANCE_KEYS = [
    "runtime_version",
    "generated_at_utc",
    "contract_version",
    "policy_layer_version",
    "processing_states_completed",
    "normalized_input_sha256",
    "contract_manifest_sha256",
    "policy_layer_sha256",
    "canonical_schema_sha256",
    "runtime_identity",
    "loaded_pack_fingerprints",
]
EXPECTED_RUNTIME_IDENTITY_KEYS = [
    "bootstrap_entrypoint",
    "core_runtime_root",
    "active_contract_root",
]
EXPECTED_CRITERIA_KEYS = [
    "problem_definition_and_claim_clarity",
    "structural_integrity",
    "methodological_legibility",
    "evidence_to_claim_alignment",
    "claim_evidence_calibration",
    "literature_positioning",
    "transparency_and_reporting_readiness",
    "integrity_and_policy_readiness",
    "adversarial_resilience",
]
EXPECTED_EDITORIAL_COMPONENT_KEYS = [
    "abstract_clarity",
    "intro_gap_definition",
    "first_hard_object_validity",
    "figure_support",
    "references_coverage",
]
EXPECTED_MARKDOWN_SECTIONS = [
    "## Central claim",
    "## Classification",
    "## Reviewability",
    "## Transparency",
    "## Integrity",
    "## Structural integrity",
    "## Claim-evidence calibration",
    "## Adversarial resilience",
    "## Scientific record",
    "## Venue routing",
    "## Editorial first pass",
    "## Rehabilitation",
    "## Packs",
]
CLINICAL_PACK_PATH = str(ROOT / "fixtures" / "external_packs" / "apr-pack-clinical")
SURFACE_CASES = [
    {
        "case_id": "clean_send_out",
        "fixture": "reviewable_sound_paper.json",
        "pack_paths": [],
        "expected_recommendation": "PLAUSIBLE_SEND_OUT",
        "expected_editorial_forecast": "PLAUSIBLE_SEND_OUT",
        "expected_author_recommendation": "PLAUSIBLE_SEND_OUT",
        "expected_record_status": "pass",
        "expected_pack_count": 0,
    },
    {
        "case_id": "repair_required",
        "fixture": "computational_simulation_revision_case.json",
        "pack_paths": [],
        "expected_recommendation": "REVISE_BEFORE_SUBMISSION",
        "expected_editorial_forecast": "REBUILD_REQUIRED",
        "expected_author_recommendation": "REVISE_BEFORE_SUBMISSION",
        "expected_record_status": "repairable_fail",
        "expected_pack_count": 0,
    },
    {
        "case_id": "non_reviewable",
        "fixture": "abstract_only_fragment.json",
        "pack_paths": [],
        "expected_recommendation": "NON_REVIEWABLE",
        "expected_editorial_forecast": "NON_REVIEWABLE",
        "expected_author_recommendation": "NON_REVIEWABLE",
        "expected_record_status": "fatal_fail",
        "expected_pack_count": 0,
    },
    {
        "case_id": "pack_applicable",
        "fixture": "clinical_pack_readiness_case.json",
        "pack_paths": [CLINICAL_PACK_PATH],
        "expected_recommendation": "PLAUSIBLE_SEND_OUT",
        "expected_editorial_forecast": "PLAUSIBLE_SEND_OUT",
        "expected_author_recommendation": "PLAUSIBLE_SEND_OUT",
        "expected_record_status": "pass",
        "expected_pack_count": 1,
    },
    {
        "case_id": "pack_not_applicable",
        "fixture": "reviewable_sound_paper.json",
        "pack_paths": [CLINICAL_PACK_PATH],
        "expected_recommendation": "PLAUSIBLE_SEND_OUT",
        "expected_editorial_forecast": "PLAUSIBLE_SEND_OUT",
        "expected_author_recommendation": "PLAUSIBLE_SEND_OUT",
        "expected_record_status": "pass",
        "expected_pack_count": 1,
    },
]


def _record(fixture: str, *, pack_paths: list[str] | None = None) -> dict:
    return run_audit(read_json(ROOT / "fixtures" / "inputs" / fixture), pack_paths=pack_paths or [])


@pytest.mark.parametrize("case", SURFACE_CASES, ids=[case["case_id"] for case in SURFACE_CASES])
def test_canonical_output_surfaces_are_present_typed_and_ordered(case: dict):
    record = _record(case["fixture"], pack_paths=case["pack_paths"])

    assert list(record.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert list(record["decision"].keys()) == EXPECTED_DECISION_KEYS
    assert list(record["transparency"].keys()) == EXPECTED_TRANSPARENCY_KEYS
    assert list(record["provenance"].keys()) == EXPECTED_PROVENANCE_KEYS
    assert list(record["provenance"]["runtime_identity"].keys()) == EXPECTED_RUNTIME_IDENTITY_KEYS
    assert list(record["scientific_record"]["criteria"].keys()) == EXPECTED_CRITERIA_KEYS
    assert list(record["editorial_first_pass"]["component_scores"].keys()) == EXPECTED_EDITORIAL_COMPONENT_KEYS

    assert isinstance(record["decision"]["editorial_forecast"], str)
    assert isinstance(record["decision"]["author_recommendation"], str)
    assert isinstance(record["scientific_record"]["criteria"]["adversarial_resilience"]["status"], str)
    assert isinstance(record["rehabilitation"]["one_publishable_unit"], str)
    assert isinstance(record["rehabilitation"]["development_track"], str)
    assert isinstance(record["rehabilitation"]["minimum_viable_evidence_package"], list)
    assert isinstance(record["rehabilitation"]["next_actions_ranked"], list)
    assert all(isinstance(item, str) for item in record["rehabilitation"]["next_actions_ranked"])
    assert isinstance(record["pack_execution"], dict)
    assert isinstance(record["pack_execution"]["requested_pack_paths"], list)
    assert isinstance(record["pack_execution"]["loaded_packs"], list)
    assert isinstance(record["pack_execution"]["pack_load_failures"], list)
    assert isinstance(record["pack_execution"]["any_pack_requested_human_escalation"], bool)
    assert isinstance(record["pack_results"], list)

    assert record["decision"]["recommendation"] == case["expected_recommendation"]
    assert record["decision"]["editorial_forecast"] == case["expected_editorial_forecast"]
    assert record["decision"]["author_recommendation"] == case["expected_author_recommendation"]
    assert record["scientific_record"]["status"] == case["expected_record_status"]
    assert len(record["pack_results"]) == case["expected_pack_count"]

    if case["case_id"] == "clean_send_out":
        assert record["rehabilitation"]["next_actions_ranked"] == [
            "Preserve current scope discipline and evidence-to-claim calibration.",
            "Keep transparency statements synchronized with the actual release surfaces.",
            "Retain the stated limitation boundary in the abstract and discussion.",
        ]
        assert record["pack_execution"]["requested_pack_paths"] == []
        assert record["pack_execution"]["loaded_packs"] == []
        assert record["pack_execution"]["pack_load_failures"] == []
        assert record["provenance"]["loaded_pack_fingerprints"] == []

    if case["case_id"] == "repair_required":
        assert record["decision"]["editorial_forecast"] == "REBUILD_REQUIRED"
        assert record["decision"]["author_recommendation"] == "REVISE_BEFORE_SUBMISSION"
        assert record["pack_results"] == []

    if case["case_id"] == "non_reviewable":
        assert record["decision"]["editorial_forecast"]
        assert record["decision"]["author_recommendation"]
        assert record["reviewability"]["status"] == "fail"
        assert record["pack_results"] == []

    if case["case_id"] == "pack_applicable":
        result = record["pack_results"][0]
        assert record["pack_execution"]["pack_load_failures"] == []
        loaded_pack = record["pack_execution"]["loaded_packs"][0]
        fingerprint = record["provenance"]["loaded_pack_fingerprints"][0]
        assert result["display_name"] == "APR Clinical Pack"
        assert result["pack_id"] == "clinical_pack"
        assert result["applicability"] == "applicable"
        assert result["status"] == "pass"
        assert Path(loaded_pack["resolved_repo_root"]).as_posix().endswith("fixtures/external_packs/apr-pack-clinical")
        assert Path(loaded_pack["manifest_path"]).as_posix().endswith("fixtures/external_packs/apr-pack-clinical/pack.yaml")
        assert fingerprint["pack_id"] == "clinical_pack"
        assert fingerprint["manifest_sha256"] == loaded_pack["manifest_sha256"]
        assert result["advisory_fields"]["clinical_readiness"]["endpoint_surface_visible"] is True

    if case["case_id"] == "pack_not_applicable":
        result = record["pack_results"][0]
        assert record["pack_execution"]["pack_load_failures"] == []
        assert result["display_name"] == "APR Clinical Pack"
        assert result["pack_id"] == "clinical_pack"
        assert result["applicability"] == "not_applicable"
        assert result["status"] == "not_applicable"
        assert result["warnings"] == [
            "domain_module 'methods_or_tools' is outside the supported domains for this pack"
        ]


@pytest.mark.parametrize("case", SURFACE_CASES, ids=[case["case_id"] for case in SURFACE_CASES])
def test_markdown_render_surface_sections_are_locked(case: dict):
    record = _record(case["fixture"], pack_paths=case["pack_paths"])
    rendered = render_markdown_report(record)

    headings = [line for line in rendered.splitlines() if line.startswith("## ")]
    assert headings == EXPECTED_MARKDOWN_SECTIONS
    assert f"**Recommendation:** {case['expected_recommendation']}" in rendered
    assert f"**Editorial forecast:** {case['expected_editorial_forecast']}" in rendered
    assert f"**Author recommendation:** {case['expected_author_recommendation']}" in rendered
    assert f"- Status: {case['expected_record_status']}" in rendered

    if case["case_id"] == "clean_send_out":
        assert "- Claim magnitude: 3" in rendered
        assert "- Evidence level: 5" in rendered
        assert "## Packs\n- none\n" in rendered

    if case["case_id"] == "repair_required":
        assert "- Routing state: blocked_by_scientific_record" in rendered
        assert "## Packs\n- none\n" in rendered

    if case["case_id"] == "non_reviewable":
        assert "- Routing state: blocked_by_scientific_record" in rendered
        assert "- Status: fail" in rendered
        assert "## Packs\n- none\n" in rendered

    if case["case_id"] == "pack_applicable":
        assert "- APR Clinical Pack (pass, applicable)" in rendered
        assert "## Packs" in rendered

    if case["case_id"] == "pack_not_applicable":
        assert "- APR Clinical Pack (not_applicable, not_applicable)" in rendered
        assert "## Packs" in rendered
