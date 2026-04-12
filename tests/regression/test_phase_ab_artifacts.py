from pathlib import Path
import sys

from jsonschema import validate

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

from apr_core.defense_readiness import build_defense_readiness_record
from apr_core.pdf_annotations import build_pdf_annotation_manifest
from apr_core.pdf_viewer import write_annotation_viewer
from apr_core.pipeline import run_audit
from apr_core.policy import (
    load_defense_readiness_record_schema,
    load_pdf_annotation_manifest_schema,
    load_question_challenge_record_schema,
)
from apr_core.question_generation import build_question_challenge_record
from apr_core.utils import read_json, stable_json_sha256


def test_phase_ab_artifacts_are_schema_valid_deterministic_and_renderable(tmp_path: Path):
    payload = read_json(ROOT / "fixtures" / "inputs" / "reviewable_sound_paper.json")
    canonical = run_audit(payload)

    defense = build_defense_readiness_record(canonical, payload=payload, context_type="journal_referee")
    questions = build_question_challenge_record(
        canonical,
        defense_record=defense,
        context_type="journal_referee",
    )
    manifest = build_pdf_annotation_manifest(
        canonical,
        payload=payload,
        defense_record=defense,
        question_record=questions,
        source_pdf_path="fixtures/inputs/reviewable_sound_paper.pdf",
        context_type="journal_referee",
    )

    validate(instance=defense, schema=load_defense_readiness_record_schema())
    validate(instance=questions, schema=load_question_challenge_record_schema())
    validate(instance=manifest, schema=load_pdf_annotation_manifest_schema())

    assert defense["artifact_type"] == "DefenseReadinessRecord"
    assert questions["artifact_type"] == "QuestionChallengeRecord"
    assert manifest["artifact_type"] == "PdfAnnotationManifest"
    assert manifest["viewer_mode"] == "text_facsimile_with_source_pdf"
    assert defense["source"]["canonical_record_sha256"] == stable_json_sha256(canonical)
    assert questions["source"]["defense_record_sha256"] == stable_json_sha256(defense)
    assert manifest["source"]["question_record_sha256"] == stable_json_sha256(questions)

    defense_again = build_defense_readiness_record(canonical, payload=payload, context_type="journal_referee")
    questions_again = build_question_challenge_record(
        canonical,
        defense_record=defense_again,
        context_type="journal_referee",
    )
    manifest_again = build_pdf_annotation_manifest(
        canonical,
        payload=payload,
        defense_record=defense_again,
        question_record=questions_again,
        source_pdf_path="fixtures/inputs/reviewable_sound_paper.pdf",
        context_type="journal_referee",
    )
    assert stable_json_sha256(defense) == stable_json_sha256(defense_again)
    assert stable_json_sha256(questions) == stable_json_sha256(questions_again)
    assert stable_json_sha256(manifest) == stable_json_sha256(manifest_again)

    written = write_annotation_viewer(tmp_path / "viewer", payload, manifest)
    html_path = Path(written["html_path"])
    manifest_path = Path(written["manifest_path"])
    html = html_path.read_text(encoding="utf-8")

    assert html_path.exists()
    assert manifest_path.exists()
    assert "APR Review Surface" not in html
    assert "Drilldowns" in html
    assert canonical["metadata"]["title"] in html
    assert "badge" in html


def test_defense_scores_and_question_contexts_are_deterministic():
    payload = read_json(ROOT / "fixtures" / "external_papers" / "external_methodology_weak_paper.json")
    canonical = run_audit(payload)
    defense = build_defense_readiness_record(canonical, payload=payload, context_type="journal_referee")

    risk_by_category = {risk["category"]: risk for risk in defense["risk_items"]}
    assert defense["overall_status"] == "not_ready"
    assert risk_by_category["reproducibility_risk"]["score"] == 100
    assert risk_by_category["reproducibility_risk"]["current_answerability"] == "missing"
    assert risk_by_category["defense_question_pressure_risk"]["score"] == 100
    assert risk_by_category["comparator_or_control_risk"]["score"] == 55
    assert risk_by_category["novelty_positioning_risk"]["score"] == 40

    journal_questions = build_question_challenge_record(
        canonical,
        defense_record=defense,
        context_type="journal_referee",
    )
    phd_questions = build_question_challenge_record(
        canonical,
        defense_record=build_defense_readiness_record(canonical, payload=payload, context_type="phd_defense_committee"),
        context_type="phd_defense_committee",
    )

    journal_categories = {question["category"] for question in journal_questions["questions"]}
    phd_categories = {question["category"] for question in phd_questions["questions"]}

    assert "controls_and_baselines" in journal_categories
    assert "contribution_future_work_and_next_experiment" not in journal_categories
    assert "contribution_future_work_and_next_experiment" in phd_categories
    assert all(question["challenge_id"].startswith("journal_referee:") for question in journal_questions["questions"])
    assert all(question["challenge_id"].startswith("phd_defense_committee:") for question in phd_questions["questions"])
