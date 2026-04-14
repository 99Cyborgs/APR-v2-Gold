from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
while str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

EXTENSION_GOVERNANCE_DOC_SNIPPETS = {
    ROOT / "docs" / "EXECUTION_MODEL.md": [
        "APR v2 is deterministic and local-only.",
        "No external model provider is called in the initial build.",
        "Provider and adapter packages are reserved seams only and are not part of the active runtime path.",
        "No provider or adapter seam may enter the active runtime path without an explicit future change that updates doctrine docs, adds validation coverage, and preserves deterministic local-only execution.",
    ],
    ROOT / "docs" / "MIGRATION_POLICY.md": [
        "APR v2 does not silently inherit legacy APR layouts or contracts.",
        "Any future compatibility adapter must be explicit, versioned, and isolated under `contracts/legacy/` plus adapter code.",
        "No compatibility adapter is active in the current runtime path.",
        "Any future provider or adapter admission must be explicit in docs and tests before code activation; placeholder modules or dormant protocols do not count as runtime approval.",
    ],
    ROOT / "docs" / "PACK_INTERFACE.md": [
        "Packs are external repos discovered by explicit path.",
        "path-based discovery only",
        "add scoped fatal-gate requests as advisory pack requests only",
        "silently overwrite core recommendations",
    ],
    ROOT / "docs" / "REPO_CHARTER.md": [
        "One canonical contract surface is active at runtime.",
        "Domain rules are externalized to advisory packs.",
        "This repo does not host submission automation, collaboration tooling, CRM features, or domain-specific pack doctrine in core.",
    ],
}

from apr_core.goldset import load_goldset_ledger_entry_schema, load_goldset_summary_schema, run_goldset_manifest  # noqa: E402
from apr_core import cli as apr_cli  # noqa: E402
import apr_core.goldset.runner as goldset_runner  # noqa: E402
from apr_core.goldset.governance.surface_contract import (  # noqa: E402
    enforce_surface_exclusivity,
    validate_governance_schema_contract,
)


def test_surface_isolation_fails_fast_on_mixed_scoring_consumption():
    with pytest.raises(ValueError):
        enforce_surface_exclusivity(
            {
                "scoring": {
                    "scientific_score": {"total": 1.0},
                    "scientific_vector": {"claim_clarity": 1.0},
                },
                "export": {},
            },
            strict_surface_contract=True,
        )


def test_surface_isolation_fields_are_declared_in_summary_and_ledger_schemas():
    validate_governance_schema_contract(
        load_goldset_summary_schema(),
        load_goldset_ledger_entry_schema(),
    )


def test_surface_isolation_remains_additive_in_runtime_output():
    baseline = run_goldset_manifest(ROOT / "benchmarks" / "goldset_dev" / "manifest.yaml")
    strict = run_goldset_manifest(
        ROOT / "benchmarks" / "goldset_dev" / "manifest.yaml",
        strict_surface_contract=True,
    )

    baseline_case = next(case for case in baseline["cases"] if case["case_id"] == "reviewable_sound_paper")
    strict_case = next(case for case in strict["cases"] if case["case_id"] == "reviewable_sound_paper")

    assert "surface_contract" not in baseline_case
    assert strict_case["decision_recommendation"] == baseline_case["decision_recommendation"]
    assert strict_case["surface_contract"]["mixed_usage_violation"] is False


def test_provider_and_adapter_seams_remain_dormant_in_active_runtime():
    cli_source = Path(apr_cli.__file__).read_text(encoding="utf-8")
    runner_source = Path(goldset_runner.__file__).read_text(encoding="utf-8")

    assert "apr_core.providers" not in cli_source
    assert "apr_core.providers" not in runner_source
    assert "apr_core.adapters" not in cli_source
    assert "apr_core.adapters" not in runner_source


def test_extension_governance_docs_remain_in_lockstep_with_repo_boundary():
    for doc_path, required_snippets in EXTENSION_GOVERNANCE_DOC_SNIPPETS.items():
        content = doc_path.read_text(encoding="utf-8")
        for snippet in required_snippets:
            assert snippet in content, f"{doc_path.name} is missing required governance text: {snippet}"
