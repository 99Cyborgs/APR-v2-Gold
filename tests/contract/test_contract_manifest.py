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

from jsonschema import Draft202012Validator

from apr_core.policy import (
    load_audit_input_schema,
    load_canonical_record_schema,
    load_contract_manifest,
    load_policy_layer,
)
from apr_core.classify.classification import ARTICLE_TYPES, CLAIM_TYPES, DOMAIN_MODULES, OUTLET_PROFILES
from apr_core.pipeline import AUDIT_PROCESSING_STATES
from apr_core.venue.routing import ROUTING_STATES


def test_active_contract_versions_are_locked():
    manifest = load_contract_manifest()
    policy = load_policy_layer()
    assert manifest["contract"]["version"] == "2.1.0"
    assert policy["policy_layer"]["version"] == "2.1.0"
    assert policy["policy_layer"]["compatibility"]["one_active_contract_only"] is True


def test_active_schemas_are_valid():
    Draft202012Validator.check_schema(load_audit_input_schema())
    Draft202012Validator.check_schema(load_canonical_record_schema())


def test_runtime_taxonomies_remain_in_lockstep_with_policy_layer():
    policy = load_policy_layer()["policy_layer"]

    assert policy["article_types"] == list(ARTICLE_TYPES)
    assert policy["claim_types"] == list(CLAIM_TYPES)
    assert policy["domain_modules"] == list(DOMAIN_MODULES)
    assert policy["outlet_profiles"] == list(OUTLET_PROFILES)
    assert policy["processing_states"] == list(AUDIT_PROCESSING_STATES)


def test_canonical_schema_closes_fixed_classification_and_routing_enums():
    schema = load_canonical_record_schema()
    classification = schema["properties"]["classification"]["properties"]
    provenance = schema["properties"]["provenance"]["properties"]
    venue = schema["properties"]["venue"]["properties"]

    assert classification["article_type"]["enum"] == list(ARTICLE_TYPES)
    assert classification["claim_type"]["enum"] == list(CLAIM_TYPES)
    assert classification["domain_module"]["enum"] == list(DOMAIN_MODULES)
    assert classification["outlet_profile"]["enum"] == list(OUTLET_PROFILES)
    assert venue["outlet_profile"]["enum"] == list(OUTLET_PROFILES)
    assert venue["routing_state"]["enum"] == list(ROUTING_STATES)
    assert provenance["processing_states_completed"]["items"]["enum"] == list(AUDIT_PROCESSING_STATES)
