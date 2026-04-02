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


def test_active_contract_versions_are_locked():
    manifest = load_contract_manifest()
    policy = load_policy_layer()
    assert manifest["contract"]["version"] == "2.0.0"
    assert policy["policy_layer"]["version"] == "2.0.0"
    assert policy["policy_layer"]["compatibility"]["one_active_contract_only"] is True


def test_active_schemas_are_valid():
    Draft202012Validator.check_schema(load_audit_input_schema())
    Draft202012Validator.check_schema(load_canonical_record_schema())
