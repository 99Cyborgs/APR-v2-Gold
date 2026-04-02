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


def test_reviewable_sound_case_matches_expected_stable_fields():
    record = run_audit(read_json(ROOT / "fixtures" / "inputs" / "reviewable_sound_paper.json"))
    golden = read_json(ROOT / "tests" / "golden" / "reviewable_sound_expected.json")
    stable = {
        "contract_version": record["contract_version"],
        "classification": {
            "article_type": record["classification"]["article_type"],
            "claim_type": record["classification"]["claim_type"],
            "outlet_profile": record["classification"]["outlet_profile"],
            "domain_module": record["classification"]["domain_module"],
        },
        "reviewability": {"status": record["reviewability"]["status"]},
        "scientific_record": {"status": record["scientific_record"]["status"]},
        "decision": {"recommendation": record["decision"]["recommendation"]},
    }
    assert stable == golden


def test_reviewable_sound_case_emits_anchor_rich_record():
    record = run_audit(read_json(ROOT / "fixtures" / "inputs" / "reviewable_sound_paper.json"))
    assert record["parsing"]["central_claim_anchor"]
    assert record["parsing"]["decisive_support_object"]
    assert record["scientific_record"]["criteria"]["evidence_to_claim_alignment"]["evidence_anchors"]
