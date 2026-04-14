from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, validate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from apr_core.classify.classification import ARTICLE_TYPES, CLAIM_TYPES, DOMAIN_MODULES, OUTLET_PROFILES  # noqa: E402
from apr_core.goldset import load_goldset_ledger_entry_schema, load_goldset_summary_schema  # noqa: E402
from apr_core.goldset.governance.surface_contract import validate_governance_schema_contract  # noqa: E402
from apr_core.goldset.runner import RECOMMENDATION_ORDINALS  # noqa: E402
from apr_core.pipeline import AUDIT_PROCESSING_STATES, run_audit  # noqa: E402
from apr_core.policy import (  # noqa: E402
    load_audit_input_schema,
    load_canonical_record_schema,
    load_contract_manifest,
    load_policy_layer,
)
from apr_core.utils import read_json  # noqa: E402
from apr_core.venue.routing import ROUTING_STATES  # noqa: E402


def _schema_enum(schema: dict[str, Any], path: list[str]) -> list[str]:
    cursor: Any = schema
    for segment in path:
        cursor = cursor[segment]
    values = cursor.get("enum")
    if not isinstance(values, list):
        raise AssertionError(f"schema path {'.'.join(path)} does not declare an enum")
    return list(values)


def _assert_lockstep(name: str, expected: list[str] | tuple[str, ...], observed: list[str] | tuple[str, ...]) -> None:
    if list(expected) != list(observed):
        raise AssertionError(f"{name} drift:\nexpected={list(expected)}\nobserved={list(observed)}")


def main() -> int:
    manifest = load_contract_manifest()
    policy = load_policy_layer()
    canonical_schema = load_canonical_record_schema()
    summary_schema = load_goldset_summary_schema()
    ledger_schema = load_goldset_ledger_entry_schema()
    Draft202012Validator.check_schema(load_audit_input_schema())
    Draft202012Validator.check_schema(canonical_schema)
    Draft202012Validator.check_schema(summary_schema)
    Draft202012Validator.check_schema(ledger_schema)
    validate_governance_schema_contract(summary_schema, ledger_schema)

    assert manifest["contract"]["version"] == "2.1.0"
    assert policy["policy_layer"]["version"] == "2.1.0"
    assert policy["policy_layer"]["compatibility"]["one_active_contract_only"] is True
    assert "PREPRINT_READY_NOT_JOURNAL_READY" in policy["policy_layer"]["recommendation_states"]

    _assert_lockstep("policy.article_types/runtime", policy["policy_layer"]["article_types"], ARTICLE_TYPES)
    _assert_lockstep("policy.claim_types/runtime", policy["policy_layer"]["claim_types"], CLAIM_TYPES)
    _assert_lockstep("policy.domain_modules/runtime", policy["policy_layer"]["domain_modules"], DOMAIN_MODULES)
    _assert_lockstep("policy.outlet_profiles/runtime", policy["policy_layer"]["outlet_profiles"], OUTLET_PROFILES)
    _assert_lockstep("policy.processing_states/runtime", policy["policy_layer"]["processing_states"], AUDIT_PROCESSING_STATES)
    _assert_lockstep(
        "policy.recommendation_states/runtime",
        policy["policy_layer"]["recommendation_states"],
        list(RECOMMENDATION_ORDINALS),
    )
    _assert_lockstep(
        "canonical.classification.article_type",
        policy["policy_layer"]["article_types"],
        _schema_enum(canonical_schema, ["properties", "classification", "properties", "article_type"]),
    )
    _assert_lockstep(
        "canonical.classification.claim_type",
        policy["policy_layer"]["claim_types"],
        _schema_enum(canonical_schema, ["properties", "classification", "properties", "claim_type"]),
    )
    _assert_lockstep(
        "canonical.classification.domain_module",
        policy["policy_layer"]["domain_modules"],
        _schema_enum(canonical_schema, ["properties", "classification", "properties", "domain_module"]),
    )
    _assert_lockstep(
        "canonical.classification.outlet_profile",
        policy["policy_layer"]["outlet_profiles"],
        _schema_enum(canonical_schema, ["properties", "classification", "properties", "outlet_profile"]),
    )
    _assert_lockstep(
        "canonical.venue.outlet_profile",
        policy["policy_layer"]["outlet_profiles"],
        _schema_enum(canonical_schema, ["properties", "venue", "properties", "outlet_profile"]),
    )
    _assert_lockstep(
        "canonical.venue.routing_state",
        ROUTING_STATES,
        _schema_enum(canonical_schema, ["properties", "venue", "properties", "routing_state"]),
    )
    _assert_lockstep(
        "canonical.decision.recommendation",
        policy["policy_layer"]["recommendation_states"],
        _schema_enum(canonical_schema, ["$defs", "recommendation"]),
    )
    _assert_lockstep(
        "canonical.provenance.processing_states_completed",
        policy["policy_layer"]["processing_states"],
        _schema_enum(canonical_schema, ["properties", "provenance", "properties", "processing_states_completed", "items"]),
    )

    fixtures = sorted((ROOT / "fixtures" / "inputs").glob("*.json"))
    for fixture in fixtures:
        payload = read_json(fixture)
        validate(instance=payload, schema=load_audit_input_schema())

    reviewable_payload = read_json(ROOT / "fixtures" / "inputs" / "reviewable_sound_paper.json")
    reviewable_record = run_audit(reviewable_payload)
    validate(instance=reviewable_record, schema=canonical_schema)

    theory_payload = read_json(ROOT / "fixtures" / "inputs" / "theory_pack_case.json")
    theory_record = run_audit(
        theory_payload,
        pack_paths=[str(ROOT / "fixtures" / "external_packs" / "apr-pack-physics")],
    )
    validate(instance=theory_record, schema=canonical_schema)
    assert theory_record["pack_results"]

    print("contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
