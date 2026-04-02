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
    record = run_audit(payload, pack_paths=[str(ROOT / "fixtures" / "external_packs" / "apr-pack-physics")])
    assert record["decision"]["recommendation"] == "PLAUSIBLE_SEND_OUT"
    assert record["pack_execution"]["loaded_packs"]
    assert record["pack_results"]
    assert record["pack_results"][0]["pack_id"] == "physics_pack"
    assert record["pack_results"][0]["advisory_only"] is True
