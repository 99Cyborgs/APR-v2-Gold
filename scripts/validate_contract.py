from __future__ import annotations

import sys
from pathlib import Path

from jsonschema import Draft202012Validator, validate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from apr_core.pipeline import run_audit  # noqa: E402
from apr_core.policy import (  # noqa: E402
    load_audit_input_schema,
    load_canonical_record_schema,
    load_contract_manifest,
    load_policy_layer,
)
from apr_core.utils import read_json  # noqa: E402


def main() -> int:
    manifest = load_contract_manifest()
    policy = load_policy_layer()
    Draft202012Validator.check_schema(load_audit_input_schema())
    Draft202012Validator.check_schema(load_canonical_record_schema())

    assert manifest["contract"]["version"] == "2.1.0"
    assert policy["policy_layer"]["version"] == "2.1.0"
    assert policy["policy_layer"]["compatibility"]["one_active_contract_only"] is True
    assert "PREPRINT_READY_NOT_JOURNAL_READY" in policy["policy_layer"]["recommendation_states"]

    fixtures = sorted((ROOT / "fixtures" / "inputs").glob("*.json"))
    for fixture in fixtures:
        payload = read_json(fixture)
        validate(instance=payload, schema=load_audit_input_schema())

    reviewable_payload = read_json(ROOT / "fixtures" / "inputs" / "reviewable_sound_paper.json")
    reviewable_record = run_audit(reviewable_payload)
    validate(instance=reviewable_record, schema=load_canonical_record_schema())

    theory_payload = read_json(ROOT / "fixtures" / "inputs" / "theory_pack_case.json")
    theory_record = run_audit(
        theory_payload,
        pack_paths=[str(ROOT / "fixtures" / "external_packs" / "apr-pack-physics")],
    )
    validate(instance=theory_record, schema=load_canonical_record_schema())
    assert theory_record["pack_results"]

    print("contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
