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

from jsonschema import validate

from apr_core.pipeline import run_audit
from apr_core.policy import load_audit_input_schema, load_canonical_record_schema
from apr_core.utils import read_json

def test_fixture_inputs_validate_against_active_schema():
    schema = load_audit_input_schema()
    for fixture in (ROOT / "fixtures" / "inputs").glob("*.json"):
        validate(instance=read_json(fixture), schema=schema)


def test_reviewable_fixture_emits_schema_valid_record():
    payload = read_json(ROOT / "fixtures" / "inputs" / "reviewable_sound_paper.json")
    record = run_audit(payload)
    validate(instance=record, schema=load_canonical_record_schema())
