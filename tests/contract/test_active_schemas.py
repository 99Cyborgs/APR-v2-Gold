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

from jsonschema import Draft202012Validator, validate

from apr_core.policy import (
    load_defense_readiness_record_schema,
    load_pdf_annotation_manifest_schema,
    load_question_challenge_record_schema,
    load_question_registry,
    load_question_registry_schema,
)
from apr_core.classify.classification import ARTICLE_TYPES, CLAIM_TYPES, DOMAIN_MODULES, OUTLET_PROFILES
from apr_core.pipeline import run_audit
from apr_core.policy import load_audit_input_schema, load_canonical_record_schema
from apr_core.utils import read_json
from apr_core.venue.routing import ROUTING_STATES

def test_fixture_inputs_validate_against_active_schema():
    schema = load_audit_input_schema()
    for fixture in (ROOT / "fixtures" / "inputs").glob("*.json"):
        validate(instance=read_json(fixture), schema=schema)


def test_reviewable_fixture_emits_schema_valid_record():
    payload = read_json(ROOT / "fixtures" / "inputs" / "reviewable_sound_paper.json")
    record = run_audit(payload)
    validate(instance=record, schema=load_canonical_record_schema())


def test_canonical_schema_closes_runtime_classification_and_routing_vocabularies():
    schema = load_canonical_record_schema()
    classification = schema["properties"]["classification"]["properties"]
    venue = schema["properties"]["venue"]["properties"]

    assert classification["article_type"]["enum"] == list(ARTICLE_TYPES)
    assert classification["claim_type"]["enum"] == list(CLAIM_TYPES)
    assert classification["outlet_profile"]["enum"] == list(OUTLET_PROFILES)
    assert classification["domain_module"]["enum"] == list(DOMAIN_MODULES)
    assert venue["routing_state"]["enum"] == list(ROUTING_STATES)


def test_additive_contract_schemas_and_registry_validate():
    for schema in (
        load_defense_readiness_record_schema(),
        load_question_challenge_record_schema(),
        load_pdf_annotation_manifest_schema(),
        load_question_registry_schema(),
    ):
        Draft202012Validator.check_schema(schema)

    validate(instance=load_question_registry(), schema=load_question_registry_schema())
