from __future__ import annotations

"""Benchmark governance, holdout masking, drift analysis, and ledger serialization.

This module governs APR's benchmark-only surfaces. Its scores, deltas, and
calibration exports are used to detect regression and audit drift, but they do
not widen the live manuscript decision contract. Public holdout output is
deliberately blinded so the benchmark can remain assessable without leaking case
specific answer keys back into development.
"""

import hashlib
import json
import os
import random
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, validate

from apr_core.goldset.governance import governance_router
from apr_core.goldset.governance import surface_contract as governance_surface_contract
from apr_core.pipeline import ACTIVE_CONTRACT_ROOT, BOOTSTRAP_ENTRYPOINT, CORE_RUNTIME_ROOT, run_audit
from apr_core.policy import load_canonical_record_schema, load_contract_manifest, load_policy_layer
from apr_core.utils import (
    append_jsonl_atomic,
    get_by_path,
    git_output,
    is_nonempty,
    read_json,
    repo_root,
    sha256_file,
    utc_now_iso,
)

DEFAULT_STRATA = [
    {
        "name": "core_gold",
        "description": "Authoritative hard-gate cases that define non-negotiable APR v2 behavior.",
        "default_gate_behavior": "hard",
        "include_in_regression_gate": True,
    },
    {
        "name": "stress_gold",
        "description": "Active calibration pressure cases that inform drift analysis without defining the full hard gate.",
        "default_gate_behavior": "monitor",
        "include_in_regression_gate": True,
    },
    {
        "name": "holdout",
        "description": "Reserved cases or scaffolds excluded from merge gates until real untuned fixtures exist.",
        "default_gate_behavior": "exclude",
        "include_in_regression_gate": False,
    },
]

LEGACY_PARTITION_TO_STRATUM = {
    "core_structural": "core_gold",
    "venue_calibration": "stress_gold",
    "adversarial": "stress_gold",
    "pack_specific": "stress_gold",
    "holdout": "holdout",
}

DEFAULT_LEDGER_RELATIVE_PATH = Path("benchmarks") / "goldset" / "output" / "calibration_ledger.jsonl"
DEFAULT_HOLDOUT_LEDGER_RELATIVE_PATH = Path("benchmarks") / "goldset" / "output" / "holdout_calibration_ledger.jsonl"
DEFAULT_LEDGER_BASELINE_WINDOW = 5
DEFAULT_REGRESSION_THRESHOLD = 0.10
RECOMMENDATION_BIAS_THRESHOLD_MULTIPLIER = 7.5
DEFAULT_FATAL_WEIGHT_SCALE = 1.0
DEFAULT_HOLDOUT_ERROR_COUNT_JITTER = 1
DEFAULT_HOLDOUT_LOSS_EPSILON = 0.2
HOLDOUT_MASKED_ERROR_CLASS = "masked_holdout_error"
DEFAULT_COUNTERFACTUAL_PERTURBATIONS = 7
DEFAULT_COUNTERFACTUAL_JITTER = 0.05

HOLDOUT_STRATUM = "holdout"
DEV_SPLIT = "dev"
HOLDOUT_SPLIT = "holdout"
DEVELOPMENT_EVALUATION_MODE = "development"
HOLDOUT_BLIND_EVALUATION_MODE = "holdout_blind"
GOVERNANCE_REASON_CODES = {
    "leakage_budget_exhausted",
    "leakage_rank_jitter_applied",
    "non_identifiable_attribution",
    "silent_drift_detected",
    governance_surface_contract.SURFACE_CONTRACT_MIXED_REASON,
}

EXPECTED_PATH_ERROR_CLASSES = {
    "parsing.central_claim": "wrong_central_claim",
    "classification.article_type": "wrong_article_type",
    "classification.claim_type": "wrong_claim_type",
    "classification.domain_module": "wrong_domain_module",
    "classification.outlet_profile": "wrong_outlet_profile",
    "reviewability.status": "wrong_reviewability_status",
    "scientific_record.status": "wrong_scientific_record_status",
    "venue.routing_state": "wrong_venue_routing_state",
    "decision.recommendation": "wrong_recommendation",
    "decision.human_escalation_required": "wrong_human_escalation_state",
    "integrity.status": "wrong_integrity_status",
}

OBSERVED_PATHS = [
    "parsing.central_claim",
    "classification.article_type",
    "classification.claim_type",
    "classification.domain_module",
    "classification.outlet_profile",
    "reviewability.status",
    "scientific_record.status",
    "integrity.status",
    "venue.routing_state",
    "decision.recommendation",
    "decision.human_escalation_required",
]

BLOCKING_RECOMMENDATIONS = {
    "NON_REVIEWABLE",
    "DO_NOT_SUBMIT",
    "REBUILD_BEFORE_SUBMISSION",
    "REVISE_BEFORE_SUBMISSION",
}
POSITIVE_RECOMMENDATION_BANDS = {"viable_with_reroute", "preprint_only", "cautionary_viable", "viable_journal"}
FATAL_ERROR_CLASSES = {"false_accept_on_fatal_case", "missed_fatal_gate"}
FATAL_OVERRIDE_ERROR_CLASSES = FATAL_ERROR_CLASSES | {"hallucinated_fatal_gate"}

ERROR_CLASS_SEVERITY_WEIGHTS = {
    "false_accept_on_fatal_case": 10,
    "missed_fatal_gate": 10,
    "hallucinated_fatal_gate": 9,
    "wrong_integrity_status": 8,
    "wrong_human_escalation_state": 8,
    "wrong_scientific_record_status": 7,
    "wrong_reviewability_status": 6,
    "false_desk_reject_on_viable_specialist_case": 6,
    "wrong_recommendation": 5,
    "missing_required_evidence_anchor": 5,
    "pack_behavior_failure": 5,
    "wrong_central_claim": 4,
    "wrong_claim_type": 4,
    "wrong_venue_routing_state": 4,
    "wrong_article_type": 3,
    "wrong_domain_module": 3,
    "wrong_outlet_profile": 2,
    "ambiguous_case_mismatch": 1,
    "underspecified_expectation": 1,
}

RECOMMENDATION_BAND_ORDINALS = {
    "fatal_block": 0,
    "non_reviewable": 1,
    "repair_required": 2,
    "viable_with_reroute": 4,
    "preprint_only": 5,
    "cautionary_viable": 6,
    "viable_journal": 7,
}

RECOMMENDATION_ORDINALS = {
    "DO_NOT_SUBMIT": 0,
    "NON_REVIEWABLE": 1,
    "REBUILD_BEFORE_SUBMISSION": 2,
    "REVISE_BEFORE_SUBMISSION": 3,
    "RETARGET_SPECIALIST": 4,
    "RETARGET_SOUNDNESS_FIRST": 4,
    "PREPRINT_READY_NOT_JOURNAL_READY": 5,
    "SUBMIT_WITH_CAUTION": 6,
    "PLAUSIBLE_SEND_OUT": 7,
}

RECOMMENDATION_LOSS_MATRIX = {
    "fatal_block": {
        "fatal_block": 0,
        "non_reviewable": 1,
        "repair_required": 6,
        "viable_with_reroute": 8,
        "preprint_only": 8,
        "cautionary_viable": 9,
        "viable_journal": 10,
    },
    "non_reviewable": {
        "fatal_block": 1,
        "non_reviewable": 0,
        "repair_required": 5,
        "viable_with_reroute": 7,
        "preprint_only": 7,
        "cautionary_viable": 8,
        "viable_journal": 9,
    },
    "repair_required": {
        "fatal_block": 2,
        "non_reviewable": 2,
        "repair_required": 0,
        "viable_with_reroute": 2,
        "preprint_only": 3,
        "cautionary_viable": 4,
        "viable_journal": 5,
    },
    "viable_with_reroute": {
        "fatal_block": 4,
        "non_reviewable": 4,
        "repair_required": 2,
        "viable_with_reroute": 0,
        "preprint_only": 1,
        "cautionary_viable": 2,
        "viable_journal": 3,
    },
    "preprint_only": {
        "fatal_block": 5,
        "non_reviewable": 5,
        "repair_required": 3,
        "viable_with_reroute": 2,
        "preprint_only": 0,
        "cautionary_viable": 1,
        "viable_journal": 2,
    },
    "cautionary_viable": {
        "fatal_block": 6,
        "non_reviewable": 6,
        "repair_required": 4,
        "viable_with_reroute": 3,
        "preprint_only": 2,
        "cautionary_viable": 0,
        "viable_journal": 1,
    },
    "viable_journal": {
        "fatal_block": 7,
        "non_reviewable": 7,
        "repair_required": 5,
        "viable_with_reroute": 3,
        "preprint_only": 2,
        "cautionary_viable": 1,
        "viable_journal": 0,
    },
}

EDITORIAL_FIRST_PASS_SENTENCE_MARKERS = (
    "we present",
    "we propose",
    "we introduce",
    "we derive",
    "we report",
    "we reanalyze",
    "we benchmark",
    "we describe",
    "we show",
)
EDITORIAL_FIRST_PASS_NOVELTY_MARKERS = (
    "new",
    "novel",
    "first",
    "independent",
    "replication",
    "benchmark",
    "baseline",
)
CODE_CHANGE_SURFACE_RULES = (
    ("src/apr_core/goldset/", "goldset_governor"),
    ("src/apr_core/packs/", "policy_pack"),
    ("src/apr_core/pipeline", "audit_pipeline"),
    ("src/apr_core/policy", "audit_pipeline"),
    ("benchmarks/goldset/", "benchmark_config"),
    ("fixtures/", "fixtures"),
    ("tests/", "test_only"),
)

SCIENTIFIC_SCORE_CRITERIA = {
    "evidence_alignment": "evidence_to_claim_alignment",
    "methodological_validity": "methodological_legibility",
    "reproducibility": "transparency_and_reporting_readiness",
    "falsifiability": "problem_definition_and_claim_clarity",
    "baseline_comparison": "literature_positioning",
}
SCIENTIFIC_WEIGHT_ALIASES = {
    "evidence_alignment": "evidence_alignment",
    "methodology": "methodological_validity",
    "methodological_validity": "methodological_validity",
    "reproducibility": "reproducibility",
    "falsifiability": "falsifiability",
    "baseline_comparison": "baseline_comparison",
}
NATIVE_SCIENTIFIC_VECTOR_KEYS = (
    "claim_clarity",
    "evidence_alignment",
    "falsifiability",
    "baseline_comparison",
    "methodological_legibility",
)
LEGACY_SCIENTIFIC_VECTOR_KEYS = (
    "evidence_alignment",
    "methodological_validity",
    "reproducibility",
    "falsifiability",
    "baseline_comparison",
    "total",
)
EDITORIAL_WEIGHT_ALIASES = {
    "clarity": "clarity",
    "novelty": "novelty_explicitness",
    "novelty_explicitness": "novelty_explicitness",
    "structure_quality": "structure_quality",
    "rhetorical_density": "rhetorical_density",
}
DEFAULT_EDITORIAL_PENALTY_WEIGHT = 0.0
DEFAULT_ENABLED_EDITORIAL_PENALTY_WEIGHT = 0.05
DEFAULT_LOSS_QUANTIZATION_PLACES = 2
DEFAULT_HOLDOUT_BLINDNESS_LEVEL = "strict"
EDITORIAL_PENALTY_MARGIN_RATIO = 0.1
LOSS_BAND_THRESHOLDS = {
    "low": 2.0,
    "medium": 5.0,
}
HOLDOUT_RECOMMENDATION_BINS = {
    "fatal_block": "blocked",
    "non_reviewable": "blocked",
    "repair_required": "repair_required",
    "viable_with_reroute": "conditional_accept",
    "preprint_only": "conditional_accept",
    "cautionary_viable": "accepted_band",
    "viable_journal": "accepted_band",
}
RHETORICAL_DENSITY_MARKERS = (
    "we present",
    "we propose",
    "we introduce",
    "we report",
    "new",
    "novel",
    "first",
)
EDITORIAL_ANOMALY_MARKERS = (
    "universal",
    "all orbital phenomena",
    "field-defining",
    "paradigm",
    "breakthrough",
    "transformative",
    "revolutionary",
    "unprecedented",
)
EDITORIAL_ANOMALY_THRESHOLDS = {
    "novelty_density": 0.03,
    "claim_to_evidence_ratio": 2.0,
    "rhetorical_intensity": 0.6,
}
FALSIFIABILITY_MARKERS = (
    "falsif",
    "validated",
    "validation",
    "compare",
    "compares",
    "relative to",
    "failure regime",
    "limited by",
    "should not be used",
    "uncertainty",
)
BASELINE_COMPARISON_MARKERS = (
    "baseline",
    "relative to",
    "compare",
    "compares",
    "versus",
    " vs ",
    "replication",
)
ERROR_CLASS_MAP = {
    "format_error": "structural",
    "schema_error": "structural",
    "reasoning_error": "semantic",
    "hallucination": "semantic",
    "pack_behavior_failure": "structural",
    "missing_required_evidence_anchor": "structural",
    "underspecified_expectation": "structural",
    "wrong_central_claim": "semantic",
    "wrong_claim_type": "semantic",
    "wrong_article_type": "semantic",
    "wrong_domain_module": "semantic",
    "wrong_outlet_profile": "semantic",
    "wrong_reviewability_status": "semantic",
    "wrong_scientific_record_status": "semantic",
    "wrong_recommendation": "semantic",
    "wrong_venue_routing_state": "semantic",
    "wrong_human_escalation_state": "semantic",
    "wrong_integrity_status": "semantic",
    "false_accept_on_fatal_case": "semantic",
    "missed_fatal_gate": "semantic",
    "hallucinated_fatal_gate": "semantic",
    "false_desk_reject_on_viable_specialist_case": "semantic",
    "ambiguous_case_mismatch": "semantic",
}
KNOWN_GOLDSET_ERROR_CLASSES = set(ERROR_CLASS_SEVERITY_WEIGHTS) | {HOLDOUT_MASKED_ERROR_CLASS}


class EditorialDriftError(RuntimeError):
    """Raised when editorial weighting changes decision-invariant public surfaces."""


@dataclass(slots=True)
class ScientificScore:
    evidence_alignment: float
    methodological_validity: float
    reproducibility: float
    falsifiability: float
    baseline_comparison: float

    def as_dict(self) -> dict[str, float]:
        return {key: _rounded(value) for key, value in asdict(self).items()}


@dataclass(slots=True)
class ScientificScoreVector:
    claim_clarity: float
    evidence_alignment: float
    falsifiability: float
    baseline_comparison: float
    methodological_legibility: float

    def as_dict(self) -> dict[str, float]:
        return {key: _rounded(value) for key, value in asdict(self).items()}


@dataclass(slots=True)
class EditorialScore:
    clarity: float
    novelty_explicitness: float
    structure_quality: float
    rhetorical_density: float

    def as_dict(self) -> dict[str, float]:
        return {key: _rounded(value) for key, value in asdict(self).items()}


def _goldset_root() -> Path:
    return repo_root() / "benchmarks" / "goldset"


def _schema_path(name: str) -> Path:
    return _goldset_root() / "schemas" / name


def _default_manifest() -> Path:
    return repo_root() / "benchmarks" / "goldset_dev" / "manifest.yaml"


def _default_holdout_manifest() -> Path:
    return repo_root() / "benchmarks" / "goldset_holdout" / "manifest.yaml"


def _active_contract_paths() -> dict[str, Path]:
    root = repo_root()
    return {
        "contract_manifest": root / "contracts" / "active" / "manifest.yaml",
        "policy_layer": root / "contracts" / "active" / "policy_layer.yaml",
        "canonical_schema": root / "contracts" / "active" / "canonical_audit_record.schema.json",
    }


def _runtime_identity() -> dict[str, str]:
    return {
        "bootstrap_entrypoint": BOOTSTRAP_ENTRYPOINT,
        "core_runtime_root": CORE_RUNTIME_ROOT,
        "active_contract_root": ACTIVE_CONTRACT_ROOT,
    }


def _runtime_contract_fingerprints() -> dict[str, str]:
    manifest = load_contract_manifest()
    policy = load_policy_layer()
    contract_paths = _active_contract_paths()
    return {
        "contract_version": manifest["contract"]["version"],
        "policy_layer_version": policy["policy_layer"]["version"],
        "contract_manifest_sha256": sha256_file(contract_paths["contract_manifest"]),
        "policy_layer_sha256": sha256_file(contract_paths["policy_layer"]),
        "canonical_schema_sha256": sha256_file(contract_paths["canonical_schema"]),
    }


def _assert_manifest_contract_parity(manifest: dict[str, Any], *, manifest_path: Path | None = None) -> None:
    active_version = _runtime_contract_fingerprints()["contract_version"]
    observed_version = str(manifest["contract_version"])
    if observed_version != active_version:
        source = str(manifest_path.resolve()) if manifest_path is not None else "goldset manifest"
        raise ValueError(
            f"{source} declares contract_version={observed_version}, but contracts/active/manifest.yaml is {active_version}"
        )


def default_calibration_ledger_path() -> Path:
    return repo_root() / DEFAULT_LEDGER_RELATIVE_PATH


def default_holdout_calibration_ledger_path() -> Path:
    return repo_root() / DEFAULT_HOLDOUT_LEDGER_RELATIVE_PATH


def default_goldset_governance_config() -> dict[str, Any]:
    regression_threshold = DEFAULT_REGRESSION_THRESHOLD
    return {
        "baseline_window": DEFAULT_LEDGER_BASELINE_WINDOW,
        "regression_threshold": regression_threshold,
        "fatal_weight_scale": DEFAULT_FATAL_WEIGHT_SCALE,
        "scientific_weights": {
            "evidence_alignment": 1.0,
            "methodology": 1.0,
            "reproducibility": 1.0,
            "falsifiability": 1.0,
            "baseline_comparison": 1.0,
        },
        "editorial_weights": {
            "clarity": 0.2,
            "novelty": 0.2,
            "structure_quality": 0.2,
            "rhetorical_density": 0.2,
        },
        "editorial_penalty_weight": DEFAULT_EDITORIAL_PENALTY_WEIGHT,
        "gating": {
            "use_editorial_for_decision": False,
        },
        "drift_thresholds": {
            "false_accept_rate": regression_threshold,
            "recommendation_bias": _rounded(regression_threshold * RECOMMENDATION_BIAS_THRESHOLD_MULTIPLIER),
        },
        "drift_intervention": {
            "enabled": True,
        },
        "holdout_noise": {
            "enabled": True,
            "error_count_jitter": DEFAULT_HOLDOUT_ERROR_COUNT_JITTER,
            "mask_recommendations": True,
            "loss_epsilon": DEFAULT_HOLDOUT_LOSS_EPSILON,
        },
        "holdout_blindness": {
            "level": DEFAULT_HOLDOUT_BLINDNESS_LEVEL,
            "recommendation_bins": True,
            "error_class_binning": True,
            "pass_fail_jitter": True,
        },
        "loss_quantization": {
            "enabled": False,
            "places": DEFAULT_LOSS_QUANTIZATION_PLACES,
        },
        "drift_counterfactuals": {
            "enabled": False,
            "perturbations": DEFAULT_COUNTERFACTUAL_PERTURBATIONS,
            "jitter": DEFAULT_COUNTERFACTUAL_JITTER,
        },
        "leakage_guard": {
            "enabled": False,
            "epsilon": 1.0,
            "budget_cap": 8,
        },
        "attribution_identifiability": {
            "enabled": False,
        },
        "invariance_trace": {
            "enabled": False,
        },
        "surface_contract": {
            "enabled": False,
        },
        "calibration": {
            "extended_export": False,
        },
        "planes": {
            "mode": "separate",
            "explicit_cli_flag": False,
        },
        "recommendation_loss_matrix": {
            source_band: dict(sorted(targets.items()))
            for source_band, targets in sorted(RECOMMENDATION_LOSS_MATRIX.items())
        },
        "editorial_first_pass": {
            "components": ["abstract_clarity", "novelty_explicitness", "evidence_visibility"],
            "max_component_scores": {
                "abstract_clarity": 4,
                "novelty_explicitness": 3,
                "evidence_visibility": 4,
            },
        },
    }


def _resolve_goldset_governance_config(
    *,
    baseline_window: int | None = None,
    regression_threshold: float | None = None,
    fatal_weight_scale: float | None = None,
    holdout_noise: bool | None = None,
    holdout_blindness_level: str | None = None,
    loss_quantization: bool | None = None,
    enable_editorial_weight: bool | None = None,
    separate_planes: bool | None = None,
    export_calibration_extended: bool | None = None,
    drift_intervention: bool | None = None,
    drift_counterfactuals: bool | None = None,
    leakage_guard: bool | None = None,
    attribution_identifiability: bool | None = None,
    invariance_trace: bool | None = None,
    strict_surface_contract: bool | None = None,
) -> dict[str, Any]:
    config = default_goldset_governance_config()
    # CLI overrides are constrained through one governance object so benchmark
    # diagnostics cannot bypass the same threshold and masking rules the summary
    # and ledger later report.
    if baseline_window is not None:
        if baseline_window < 0:
            raise ValueError("baseline_window must be >= 0")
        config["baseline_window"] = baseline_window
    if regression_threshold is not None:
        if regression_threshold < 0:
            raise ValueError("regression_threshold must be >= 0")
        config["regression_threshold"] = regression_threshold
        config["drift_thresholds"] = {
            "false_accept_rate": regression_threshold,
            "recommendation_bias": _rounded(regression_threshold * RECOMMENDATION_BIAS_THRESHOLD_MULTIPLIER),
        }
    if fatal_weight_scale is not None:
        if fatal_weight_scale <= 0:
            raise ValueError("fatal_weight_scale must be > 0")
        config["fatal_weight_scale"] = fatal_weight_scale
    if holdout_noise is not None:
        config["holdout_noise"] = {**config["holdout_noise"], "enabled": holdout_noise}
    if holdout_blindness_level is not None:
        if holdout_blindness_level not in {"strict", "moderate", "off"}:
            raise ValueError("holdout_blindness_level must be one of: strict, moderate, off")
        blindness = {
            "strict": {"level": "strict", "recommendation_bins": True, "error_class_binning": True, "pass_fail_jitter": True},
            "moderate": {"level": "moderate", "recommendation_bins": True, "error_class_binning": True, "pass_fail_jitter": False},
            "off": {"level": "off", "recommendation_bins": False, "error_class_binning": False, "pass_fail_jitter": False},
        }[holdout_blindness_level]
        config["holdout_blindness"] = blindness
        config["holdout_noise"] = {**config["holdout_noise"], "enabled": holdout_blindness_level != "off"}
    if loss_quantization is not None:
        config["loss_quantization"] = {**config["loss_quantization"], "enabled": loss_quantization}
    if enable_editorial_weight is not None:
        config["editorial_penalty_weight"] = (
            DEFAULT_ENABLED_EDITORIAL_PENALTY_WEIGHT if enable_editorial_weight else DEFAULT_EDITORIAL_PENALTY_WEIGHT
        )
    if separate_planes is not None:
        config["planes"] = {**config["planes"], "explicit_cli_flag": separate_planes}
    if export_calibration_extended is not None:
        config["calibration"] = {**config["calibration"], "extended_export": export_calibration_extended}
    if drift_intervention is not None:
        config["drift_intervention"] = {**config["drift_intervention"], "enabled": drift_intervention}
    if drift_counterfactuals is not None:
        config["drift_counterfactuals"] = {**config["drift_counterfactuals"], "enabled": drift_counterfactuals}
    if leakage_guard is not None:
        config["leakage_guard"] = {**config["leakage_guard"], "enabled": leakage_guard}
    if attribution_identifiability is not None:
        config["attribution_identifiability"] = {
            **config["attribution_identifiability"],
            "enabled": attribution_identifiability,
        }
    if invariance_trace is not None:
        config["invariance_trace"] = {**config["invariance_trace"], "enabled": invariance_trace}
    if strict_surface_contract is not None:
        config["surface_contract"] = {**config["surface_contract"], "enabled": strict_surface_contract}
    config["severity_weights"] = _effective_severity_weights(config["fatal_weight_scale"])
    return config


def _effective_severity_weights(fatal_weight_scale: float) -> dict[str, float]:
    scaled: dict[str, float] = {}
    for error_class, weight in ERROR_CLASS_SEVERITY_WEIGHTS.items():
        multiplier = fatal_weight_scale if error_class in FATAL_OVERRIDE_ERROR_CLASSES else 1.0
        scaled[error_class] = _rounded(weight * multiplier)
    return dict(sorted(scaled.items()))


def load_goldset_manifest_schema() -> dict[str, Any]:
    return read_json(_schema_path("manifest.schema.json"))


def load_goldset_summary_schema() -> dict[str, Any]:
    return read_json(_schema_path("summary.schema.json"))


def load_goldset_ledger_entry_schema() -> dict[str, Any]:
    return read_json(_schema_path("ledger_entry.schema.json"))


def _manifest_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _safe_get_by_path(data: Any, dotted_path: str) -> Any:
    try:
        return get_by_path(data, dotted_path)
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _rounded(value: float | int | None) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    rounded = round(value, 6)
    return int(rounded) if rounded.is_integer() else rounded


def _mean(values: list[float | int]) -> float | None:
    if not values:
        return None
    return _rounded(sum(values) / len(values))


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return float(_rounded(numerator / denominator))


def _canonicalize_weights(raw_weights: dict[str, float], aliases: dict[str, str]) -> dict[str, float]:
    canonical: dict[str, float] = {}
    for raw_key, weight in raw_weights.items():
        key = aliases.get(raw_key)
        if key is None:
            continue
        canonical[key] = float(weight)
    return canonical


def _weighted_total(components: dict[str, float], weights: dict[str, float]) -> float:
    if not components:
        return 0.0
    weighted_sum = 0.0
    total_weight = 0.0
    for key, value in components.items():
        weight = weights.get(key, 1.0)
        weighted_sum += value * weight
        total_weight += weight
    if total_weight <= 0:
        return 0.0
    return float(_rounded(weighted_sum / total_weight))


def _criterion_numeric_score(detail: dict[str, Any] | None) -> float:
    if not detail:
        return 0.0
    status = detail.get("status")
    severity = detail.get("severity")
    if status in {"pass", "not_assessable"}:
        return 1.0
    if status == "borderline":
        return {
            "major": 0.4,
            "moderate": 0.55,
            "minor": 0.7,
        }.get(severity, 0.5)
    if status == "fail":
        return {
            "fatal": 0.0,
            "major": 0.2,
            "moderate": 0.35,
            "minor": 0.5,
        }.get(severity, 0.2)
    return 0.0


def _clamp_unit_interval(value: float) -> float:
    return float(_rounded(min(1.0, max(0.0, value))))


def _marker_signal(text: str, markers: tuple[str, ...]) -> float:
    lowered = text.lower()
    return 1.0 if any(marker in lowered for marker in markers) else 0.0


def _scientific_score_vector(record: dict[str, Any], payload: dict[str, Any]) -> ScientificScoreVector:
    parsing = record.get("parsing", {})
    classification = record.get("classification", {})
    reviewability = record.get("reviewability", {})
    transparency = record.get("transparency", {})
    integrity = record.get("integrity", {})
    checks = reviewability.get("checks", {})
    combined_text = " ".join(
        [
            str(payload.get("title") or ""),
            str(payload.get("abstract") or ""),
            str(payload.get("manuscript_text") or ""),
        ]
    ).strip()
    claim_text = str(parsing.get("central_claim") or "")
    contradiction_flags = parsing.get("contradiction_flags") or []
    confidence = float(parsing.get("claim_extraction_confidence") or 0.0)
    support_richness = (
        int(bool(payload.get("figures_and_captions")))
        + int(bool(payload.get("tables")))
        + int(bool(payload.get("supplement_or_appendix")))
    )
    reference_count = len(payload.get("references") or [])
    claim_word_count = len(claim_text.split())
    manuscript_length = len(str(payload.get("manuscript_text") or ""))

    claim_clarity = _clamp_unit_interval(
        (0.45 * confidence)
        + (0.25 if checks.get("recoverable_central_claim") == "pass" else 0.0)
        + (0.2 if claim_word_count >= 8 else 0.1 if claim_word_count >= 4 else 0.0)
        + (0.1 if payload.get("abstract") else 0.0)
        - min(0.4, 0.2 * len(contradiction_flags))
    )
    evidence_alignment = _clamp_unit_interval(
        (0.4 if parsing.get("decisive_support_object") else 0.0)
        + (0.35 if checks.get("identifiable_support_object") == "pass" else 0.0)
        + (0.25 * min(1.0, support_richness / 2.0))
        - (0.5 if classification.get("article_claim_mismatch") else 0.0)
        - (
            0.2
            if classification.get("claim_type") in {"benchmark_claim", "empirical_claim", "replication_claim", "null_result_claim"}
            and support_richness < 2
            else 0.0
        )
    )
    falsifiability = _clamp_unit_interval(
        (0.25 * _marker_signal(combined_text, FALSIFIABILITY_MARKERS))
        + (0.25 if any(char.isdigit() for char in combined_text) or "%" in combined_text else 0.0)
        + (0.2 * _marker_signal(combined_text, BASELINE_COMPARISON_MARKERS))
        + (0.15 if any(flag in combined_text.lower() for flag in ("limit", "failure", "not be used")) else 0.0)
        + (0.15 if checks.get("assessable_method_model_or_protocol") == "pass" else 0.0)
        - (0.25 if integrity.get("status") == "escalate" else 0.0)
    )
    baseline_comparison = _clamp_unit_interval(
        (0.45 * min(1.0, reference_count / 3.0))
        + (0.4 * _marker_signal(combined_text, BASELINE_COMPARISON_MARKERS))
        + (
            0.15
            if classification.get("claim_type") in {"benchmark_claim", "replication_claim", "null_result_claim"}
            else 0.0
        )
    )
    methodological_legibility = _clamp_unit_interval(
        (0.45 if checks.get("assessable_method_model_or_protocol") == "pass" else 0.0)
        + (0.25 if parsing.get("first_hard_object") else 0.0)
        + (0.2 * min(1.0, manuscript_length / 350.0))
        + (0.05 if payload.get("supplement_or_appendix") else 0.0)
        + (0.05 if transparency.get("status") == "declared" else 0.0)
    )
    return ScientificScoreVector(
        claim_clarity=claim_clarity,
        evidence_alignment=evidence_alignment,
        falsifiability=falsifiability,
        baseline_comparison=baseline_comparison,
        methodological_legibility=methodological_legibility,
    )


def _empty_scientific_score_vector() -> dict[str, float]:
    return ScientificScoreVector(0.0, 0.0, 0.0, 0.0, 0.0).as_dict()


def _masked_scientific_score_vector() -> dict[str, Any]:
    return {key: None for key in NATIVE_SCIENTIFIC_VECTOR_KEYS}


def _masked_legacy_scientific_score_vector() -> dict[str, Any]:
    return {key: None for key in LEGACY_SCIENTIFIC_VECTOR_KEYS}


def _quantize_loss_output(value: float | int | None, governance: dict[str, Any]) -> float | int | None:
    if value is None or not governance["loss_quantization"]["enabled"]:
        return value
    places = int(governance["loss_quantization"].get("places", DEFAULT_LOSS_QUANTIZATION_PLACES))
    return _rounded(round(float(value), places))


def _loss_band(loss: float | int | None) -> str | None:
    if loss is None:
        return None
    if loss <= LOSS_BAND_THRESHOLDS["low"]:
        return "low"
    if loss <= LOSS_BAND_THRESHOLDS["medium"]:
        return "medium"
    return "high"


def _stable_seed(*parts: str) -> int:
    digest = hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def apply_holdout_noise(loss_value: float, epsilon: float, seed: int) -> float:
    if epsilon <= 0:
        return float(_rounded(loss_value))
    rng = random.Random(seed)
    return float(_rounded(loss_value + rng.uniform(-epsilon, epsilon)))


def _case_drift_features(case: dict[str, Any]) -> list[str]:
    features = [f"error_class:{error_class}" for error_class in sorted(set(case.get("error_classes", [])))]
    if case.get("recommendation_loss"):
        features.append("recommendation_loss")
    if case.get("editorial_penalty"):
        features.append("editorial_penalty")
    return features


def _counterfactual_delta_loss(case: dict[str, Any], feature: str, governance: dict[str, Any]) -> float:
    if feature.startswith("error_class:"):
        error_class = feature.split(":", 1)[1]
        return float(governance["severity_weights"].get(error_class, 1.0))
    if feature == "recommendation_loss":
        return float(case.get("recommendation_loss") or 0.0)
    if feature == "editorial_penalty":
        return float(case.get("editorial_penalty") or 0.0)
    return 0.0


def _counterfactual_for_feature(
    case: dict[str, Any],
    feature: str,
    governance: dict[str, Any],
    *,
    delta_loss: float | None = None,
) -> dict[str, Any]:
    total_loss = float(case.get("total_loss") or 0.0)
    decision_margin = float(case.get("boundary_margin") or 0.0)
    baseline_residual = max(0.0, total_loss - decision_margin)
    if delta_loss is None:
        delta_loss = _counterfactual_delta_loss(case, feature, governance)
    perturbed_total_loss = max(0.0, total_loss - delta_loss)
    perturbed_residual = max(0.0, perturbed_total_loss - decision_margin)
    return {
        "feature": feature,
        "delta_residual": float(_rounded(baseline_residual - perturbed_residual)),
        "delta_loss": float(_rounded(total_loss - perturbed_total_loss)),
    }


def _ranked_counterfactuals_from_inputs(
    case: dict[str, Any],
    governance: dict[str, Any],
    delta_inputs: dict[str, float],
) -> list[dict[str, Any]]:
    counterfactuals = [
        _counterfactual_for_feature(case, feature, governance, delta_loss=delta_loss)
        for feature, delta_loss in delta_inputs.items()
    ]
    return sorted(counterfactuals, key=lambda item: (-item["delta_residual"], -item["delta_loss"], item["feature"]))


def _perturb_counterfactual_inputs(
    delta_inputs: dict[str, float],
    *,
    case_id: str,
    iteration: int,
    magnitude: float,
) -> dict[str, float]:
    if not delta_inputs or magnitude <= 0:
        return delta_inputs
    rng = random.Random(_stable_seed(case_id, "counterfactual-perturbation", str(iteration)))
    correlated_error_shift = rng.uniform(-magnitude, magnitude)
    correlated_surface_shift = rng.uniform(-magnitude / 2.0, magnitude / 2.0)
    perturbed: dict[str, float] = {}
    for feature, base_value in delta_inputs.items():
        individual_shift = rng.uniform(-magnitude, magnitude)
        correlated_shift = correlated_error_shift if feature.startswith("error_class:") else correlated_surface_shift
        scale = max(0.0, 1.0 + correlated_shift + (individual_shift / 2.0))
        perturbed[feature] = float(_rounded(base_value * scale))
    return perturbed


def _kendall_tau_rank_overlap(left: list[str], right: list[str]) -> float:
    shared = [feature for feature in left if feature in right]
    if len(shared) < 2:
        return 1.0
    left_positions = {feature: index for index, feature in enumerate(left)}
    right_positions = {feature: index for index, feature in enumerate(right)}
    concordant = 0
    discordant = 0
    for index, first in enumerate(shared[:-1]):
        for second in shared[index + 1 :]:
            left_order = left_positions[first] - left_positions[second]
            right_order = right_positions[first] - right_positions[second]
            if left_order == 0 or right_order == 0:
                continue
            if (left_order > 0) == (right_order > 0):
                concordant += 1
            else:
                discordant += 1
    total_pairs = concordant + discordant
    if total_pairs == 0:
        return 1.0
    return float(_rounded((concordant - discordant) / total_pairs))


def compute_attribution_stability(rankings: list[list[str]]) -> float:
    if len(rankings) < 2:
        return 1.0
    pairwise_scores: list[float] = []
    for index, ranking in enumerate(rankings[:-1]):
        for other in rankings[index + 1 :]:
            pairwise_scores.append(_kendall_tau_rank_overlap(ranking, other))
    return float(_rounded(sum(pairwise_scores) / len(pairwise_scores))) if pairwise_scores else 1.0


def _counterfactual_analysis(case: dict[str, Any], governance: dict[str, Any]) -> dict[str, Any]:
    if not governance["drift_counterfactuals"]["enabled"]:
        return {"counterfactuals": [], "stability": None}

    features = _case_drift_features(case)
    if not features:
        return {"counterfactuals": [], "stability": 1.0}

    base_inputs = {feature: _counterfactual_delta_loss(case, feature, governance) for feature in features}
    perturbation_count = max(1, int(governance["drift_counterfactuals"].get("perturbations", DEFAULT_COUNTERFACTUAL_PERTURBATIONS)))
    jitter = float(governance["drift_counterfactuals"].get("jitter", DEFAULT_COUNTERFACTUAL_JITTER) or 0.0)

    rankings: list[list[str]] = []
    accumulated: dict[str, dict[str, float]] = {
        feature: {"delta_residual": 0.0, "delta_loss": 0.0} for feature in features
    }
    for iteration in range(perturbation_count):
        perturbed_inputs = _perturb_counterfactual_inputs(
            base_inputs,
            case_id=case["case_id"],
            iteration=iteration,
            magnitude=jitter,
        )
        ranked = _ranked_counterfactuals_from_inputs(case, governance, perturbed_inputs)
        rankings.append([item["feature"] for item in ranked])
        for item in ranked:
            bucket = accumulated[item["feature"]]
            bucket["delta_residual"] += item["delta_residual"]
            bucket["delta_loss"] += item["delta_loss"]

    counterfactuals = [
        {
            "feature": feature,
            "delta_residual": float(_rounded(values["delta_residual"] / perturbation_count)),
            "delta_loss": float(_rounded(values["delta_loss"] / perturbation_count)),
        }
        for feature, values in accumulated.items()
    ]
    counterfactuals.sort(key=lambda item: (-item["delta_residual"], -item["delta_loss"], item["feature"]))
    return {
        "counterfactuals": counterfactuals,
        "stability": compute_attribution_stability(rankings),
    }


def _case_counterfactuals(case: dict[str, Any], governance: dict[str, Any]) -> list[dict[str, Any]]:
    return _counterfactual_analysis(case, governance)["counterfactuals"]


def _loss_band_bounds(loss_band: str | None) -> tuple[float, float | None]:
    if loss_band == "low":
        return (0.0, LOSS_BAND_THRESHOLDS["low"])
    if loss_band == "medium":
        return (LOSS_BAND_THRESHOLDS["low"], LOSS_BAND_THRESHOLDS["medium"])
    if loss_band == "high":
        return (LOSS_BAND_THRESHOLDS["medium"], None)
    return (0.0, None)


def _clamp_to_loss_band(value: float, loss_band: str | None) -> float:
    lower, upper = _loss_band_bounds(loss_band)
    clamped = max(lower, value)
    if upper is not None:
        clamped = min(clamped, upper - 1e-6)
    return float(_rounded(clamped))


def _scientific_score(record: dict[str, Any]) -> ScientificScore:
    criteria = record.get("scientific_record", {}).get("criteria", {})
    return ScientificScore(
        evidence_alignment=_criterion_numeric_score(criteria.get(SCIENTIFIC_SCORE_CRITERIA["evidence_alignment"])),
        methodological_validity=_criterion_numeric_score(criteria.get(SCIENTIFIC_SCORE_CRITERIA["methodological_validity"])),
        reproducibility=_criterion_numeric_score(criteria.get(SCIENTIFIC_SCORE_CRITERIA["reproducibility"])),
        falsifiability=_criterion_numeric_score(criteria.get(SCIENTIFIC_SCORE_CRITERIA["falsifiability"])),
        baseline_comparison=_criterion_numeric_score(criteria.get(SCIENTIFIC_SCORE_CRITERIA["baseline_comparison"])),
    )


def _tokenize_text(text: str) -> list[str]:
    return [token for token in "".join(char.lower() if char.isalnum() else " " for char in text).split() if token]


def _marker_hits(text: str, markers: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(lowered.count(marker) for marker in markers)


def _bounded_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(_rounded(numerator / denominator))


def _build_editorial_score(payload: dict[str, Any], editorial_first_pass: dict[str, Any]) -> EditorialScore:
    abstract_clarity = editorial_first_pass.get("abstract_clarity") or 0
    novelty_explicitness = editorial_first_pass.get("novelty_explicitness") or 0
    evidence_visibility = editorial_first_pass.get("evidence_visibility") or 0
    combined_text = " ".join(
        [
            str(payload.get("title") or ""),
            str(payload.get("abstract") or ""),
            str(payload.get("manuscript_text") or ""),
        ]
    ).strip()
    word_count = max(len(_tokenize_text(combined_text)), 1)
    rhetorical_hits = _marker_hits(combined_text, RHETORICAL_DENSITY_MARKERS)
    rhetorical_density = min(1.0, rhetorical_hits / max(word_count / 30.0, 1.0))
    return EditorialScore(
        clarity=float(_rounded(abstract_clarity / 4.0)),
        novelty_explicitness=float(_rounded(novelty_explicitness / 3.0)),
        structure_quality=float(_rounded(evidence_visibility / 4.0)),
        rhetorical_density=float(_rounded(rhetorical_density)),
    )


def _editorial_quality_total(editorial_score: EditorialScore, editorial_weights: dict[str, float]) -> float:
    adjusted = {
        "clarity": editorial_score.clarity,
        "novelty_explicitness": editorial_score.novelty_explicitness,
        "structure_quality": editorial_score.structure_quality,
        "rhetorical_density": 1.0 - editorial_score.rhetorical_density,
    }
    return _weighted_total(adjusted, editorial_weights)


def _decision_boundary_margin(recommendation: str | None) -> float:
    band = _recommendation_band(recommendation)
    if band is None:
        return 1.0
    ordinal = RECOMMENDATION_BAND_ORDINALS.get(band)
    if ordinal is None:
        return 1.0
    adjacent = [
        abs(ordinal - other)
        for other in RECOMMENDATION_BAND_ORDINALS.values()
        if other != ordinal
    ]
    return float(_rounded(min(adjacent) if adjacent else 1.0))


def _editorial_penalty(
    editorial_score: EditorialScore,
    governance: dict[str, Any],
    *,
    boundary_margin: float,
) -> float:
    weight = float(governance.get("editorial_penalty_weight", DEFAULT_EDITORIAL_PENALTY_WEIGHT) or 0.0)
    if weight <= 0:
        return 0.0
    editorial_weights = _canonicalize_weights(governance["editorial_weights"], EDITORIAL_WEIGHT_ALIASES)
    misalignment = 1.0 - _editorial_quality_total(editorial_score, editorial_weights)
    raw_penalty = max(0.0, weight * misalignment)
    max_penalty = boundary_margin * EDITORIAL_PENALTY_MARGIN_RATIO
    if max_penalty <= 0:
        return 0.0
    return float(_rounded(min(raw_penalty, max_penalty * 0.999999)))


def _editorial_anomalies(payload: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    combined_text = " ".join(
        [
            str(payload.get("title") or ""),
            str(payload.get("abstract") or ""),
            str(payload.get("manuscript_text") or ""),
        ]
    ).strip()
    word_count = max(len(_tokenize_text(combined_text)), 1)
    novelty_hits = _marker_hits(combined_text, EDITORIAL_FIRST_PASS_NOVELTY_MARKERS)
    rhetorical_hits = _marker_hits(combined_text, EDITORIAL_ANOMALY_MARKERS)
    claim_count = len(record.get("parsing", {}).get("claim_candidates") or [])
    evidence_count = (
        len(payload.get("figures_and_captions") or [])
        + len(payload.get("tables") or [])
        + len(payload.get("references") or [])
    )
    novelty_density = _bounded_ratio(novelty_hits, word_count)
    claim_to_evidence_ratio = _bounded_ratio(claim_count, max(evidence_count, 1))
    rhetorical_intensity = min(1.0, rhetorical_hits / max(word_count / 15.0, 1.0))
    triggered: list[str] = []
    if novelty_density > EDITORIAL_ANOMALY_THRESHOLDS["novelty_density"]:
        triggered.append("novelty_density")
    if claim_to_evidence_ratio > EDITORIAL_ANOMALY_THRESHOLDS["claim_to_evidence_ratio"]:
        triggered.append("claim_to_evidence_ratio")
    if rhetorical_intensity > EDITORIAL_ANOMALY_THRESHOLDS["rhetorical_intensity"]:
        triggered.append("rhetorical_intensity")
    return {
        "novelty_density": float(_rounded(novelty_density)),
        "claim_to_evidence_ratio": float(_rounded(claim_to_evidence_ratio)),
        "rhetorical_intensity": float(_rounded(rhetorical_intensity)),
        "triggered": triggered,
    }


def _error_class_bin(error_class: str) -> str:
    if error_class in FATAL_OVERRIDE_ERROR_CLASSES or error_class == "wrong_integrity_status":
        return "fatal_or_integrity"
    if error_class in {
        "wrong_scientific_record_status",
        "wrong_reviewability_status",
        "missing_required_evidence_anchor",
        "wrong_central_claim",
        "wrong_claim_type",
        "wrong_article_type",
        "wrong_domain_module",
        "wrong_outlet_profile",
    }:
        return "scientific_plane"
    if error_class in {
        "wrong_recommendation",
        "wrong_venue_routing_state",
        "wrong_human_escalation_state",
        "false_desk_reject_on_viable_specialist_case",
    }:
        return "decision_surface"
    return "masked_holdout_error"


def _error_class_group(error_class: str) -> str:
    mapped = ERROR_CLASS_MAP.get(error_class)
    if mapped:
        return mapped
    return "structural" if _error_class_bin(error_class) == "fatal_or_integrity" else "semantic"


def _holdout_pass_fail_state(case_id: str, manifest_sha256: str) -> str:
    digest = hashlib.sha256(f"{manifest_sha256}:{case_id}:holdout-pass-fail-v1".encode("utf-8")).hexdigest()
    return "pass" if int(digest[:2], 16) % 2 == 0 else "fail"


def _recommendation_band(recommendation: str | None) -> str | None:
    mapping = {
        "DO_NOT_SUBMIT": "fatal_block",
        "NON_REVIEWABLE": "non_reviewable",
        "REBUILD_BEFORE_SUBMISSION": "repair_required",
        "REVISE_BEFORE_SUBMISSION": "repair_required",
        "RETARGET_SPECIALIST": "viable_with_reroute",
        "RETARGET_SOUNDNESS_FIRST": "viable_with_reroute",
        "PREPRINT_READY_NOT_JOURNAL_READY": "preprint_only",
        "SUBMIT_WITH_CAUTION": "cautionary_viable",
        "PLAUSIBLE_SEND_OUT": "viable_journal",
    }
    return mapping.get(recommendation)


def _recommendation_ordinal(recommendation: str | None, recommendation_band: str | None = None) -> int | None:
    if recommendation in RECOMMENDATION_ORDINALS:
        return RECOMMENDATION_ORDINALS[recommendation]
    if recommendation_band in RECOMMENDATION_BAND_ORDINALS:
        return RECOMMENDATION_BAND_ORDINALS[recommendation_band]
    return None


def _default_strata() -> list[dict[str, Any]]:
    return [dict(stratum) for stratum in DEFAULT_STRATA]


def _normalize_expected_decision(raw_case: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    exact = dict(expected.get("exact") or {})
    raw_expected = dict(raw_case.get("expected_decision") or {})
    recommendation = exact.get("decision.recommendation", raw_expected.get("recommendation"))
    recommendation_band = expected.get("recommendation_band")
    if recommendation_band is None and recommendation is not None:
        recommendation_band = _recommendation_band(recommendation)
    if recommendation_band is None:
        recommendation_band = raw_expected.get("recommendation_band")
    human_escalation_required = exact.get(
        "decision.human_escalation_required",
        raw_expected.get("human_escalation_required"),
    )
    return {
        "recommendation": recommendation,
        "recommendation_band": recommendation_band,
        "human_escalation_required": human_escalation_required,
    }


def _normalize_legacy_manifest(raw_manifest: dict[str, Any]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for partition in raw_manifest.get("partitions", []):
        partition_name = partition["name"]
        stratum_name = LEGACY_PARTITION_TO_STRATUM.get(partition_name, "stress_gold")
        for case in partition.get("cases", []):
            expected_exact = dict(case.get("expected", {}) or {})
            cases.append(
                {
                    "case_id": case["case_id"],
                    "split": HOLDOUT_SPLIT if stratum_name == HOLDOUT_STRATUM else DEV_SPLIT,
                    "stratum": stratum_name,
                    "partition": partition_name,
                    "category": partition_name,
                    "case_state": "active",
                    "input": case.get("input"),
                    "pack_paths": case.get("pack_paths", []),
                    "expected": {"exact": expected_exact},
                    "required_nonempty_paths": case.get("required_nonempty_paths", []),
                    "rationale": partition.get("description", ""),
                    "tags": [],
                    "ambiguity_class": "none",
                    "central_claim": case.get("central_claim", expected_exact.get("parsing.central_claim")),
                    "claim_type": case.get("claim_type", expected_exact.get("classification.claim_type")),
                    "expected_decision": case.get("expected_decision"),
                }
            )

    return {
        "manifest_version": raw_manifest.get("manifest_version", "legacy"),
        "contract_version": raw_manifest["contract_version"],
        "case_root": raw_manifest["case_root"],
        "strata": raw_manifest.get("strata") or _default_strata(),
        "cases": cases,
    }


def _normalize_manifest(raw_manifest: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_legacy_manifest(raw_manifest) if "partitions" in raw_manifest else dict(raw_manifest)
    normalized["strata"] = normalized.get("strata") or _default_strata()

    strata_by_name = {stratum["name"]: stratum for stratum in normalized["strata"]}
    cases: list[dict[str, Any]] = []
    for raw_case in normalized.get("cases", []):
        stratum_name = raw_case["stratum"]
        stratum = strata_by_name[stratum_name]
        expected = dict(raw_case.get("expected") or {})
        exact = dict(expected.get("exact") or {})
        expected_decision = _normalize_expected_decision(raw_case, expected)

        case: dict[str, Any] = {
            "case_id": raw_case["case_id"],
            "split": raw_case.get("split", HOLDOUT_SPLIT if stratum_name == HOLDOUT_STRATUM else DEV_SPLIT),
            "stratum": stratum_name,
            "partition": raw_case["partition"],
            "category": raw_case.get("category", raw_case["partition"]),
            "case_state": raw_case.get("case_state", "active"),
            "gate_behavior": raw_case.get("gate_behavior", stratum["default_gate_behavior"]),
            "pack_paths": _dedupe_preserve_order(list(raw_case.get("pack_paths") or [])),
            "required_nonempty_paths": list(raw_case.get("required_nonempty_paths") or []),
            "rationale": raw_case.get("rationale", ""),
            "tags": _dedupe_preserve_order(list(raw_case.get("tags") or [])),
            "ambiguity_class": raw_case.get("ambiguity_class", "none"),
            "central_claim": raw_case.get("central_claim", exact.get("parsing.central_claim")),
            "claim_type": raw_case.get("claim_type", exact.get("classification.claim_type")),
            "expected_decision": expected_decision,
            "expected": {"exact": exact},
        }
        if "input" in raw_case:
            case["input"] = raw_case.get("input")
        if "recommendation_band" in expected:
            case["expected"]["recommendation_band"] = expected["recommendation_band"]
        cases.append(case)

    normalized["cases"] = cases
    return normalized


def _normalize_manifest_runtime_paths(manifest: dict[str, Any], *, manifest_file: Path) -> dict[str, Any]:
    normalized = dict(manifest)
    normalized["cases"] = []
    for case in manifest.get("cases", []):
        updated_case = dict(case)
        updated_case["pack_paths"] = [_resolve_case_pack_path(manifest_file, path) for path in case.get("pack_paths", [])]
        normalized["cases"].append(updated_case)
    return normalized


def validate_goldset_manifest(manifest: dict[str, Any], *, manifest_path: Path | None = None) -> None:
    schema = load_goldset_manifest_schema()
    Draft202012Validator.check_schema(schema)
    validate(instance=manifest, schema=schema)
    _assert_manifest_contract_parity(manifest, manifest_path=manifest_path)

    errors: list[str] = []
    seen_case_ids: set[str] = set()
    strata_by_name: dict[str, dict[str, Any]] = {}
    for stratum in manifest["strata"]:
        name = stratum["name"]
        if name in strata_by_name:
            errors.append(f"duplicate stratum name: {name}")
        strata_by_name[name] = stratum

    for case in manifest["cases"]:
        case_id = case["case_id"]
        if case_id in seen_case_ids:
            errors.append(f"duplicate case_id: {case_id}")
        seen_case_ids.add(case_id)

        if case["stratum"] not in strata_by_name:
            errors.append(f"case {case_id} references undefined stratum {case['stratum']}")
        if case["split"] not in {DEV_SPLIT, HOLDOUT_SPLIT}:
            errors.append(f"case {case_id} has unsupported split {case['split']}")

        has_expectation = bool(case["expected"].get("exact")) or bool(case["expected"].get("recommendation_band"))
        has_required_paths = bool(case.get("required_nonempty_paths"))
        if case["case_state"] == "active":
            if not case.get("input"):
                errors.append(f"active case {case_id} is missing input")
            if not has_expectation and not has_required_paths:
                errors.append(f"active case {case_id} has no expectation surface")
        elif case["case_state"] == "scaffold":
            if case["gate_behavior"] != "exclude":
                errors.append(f"scaffold case {case_id} must use gate_behavior=exclude")
        else:
            errors.append(f"case {case_id} has unsupported case_state {case['case_state']}")

        if case["expected"].get("recommendation_band") and case["expected"]["exact"].get("decision.recommendation"):
            errors.append(f"case {case_id} mixes exact recommendation and recommendation_band")

        expected_exact = case["expected"]["exact"]
        if case.get("central_claim") and expected_exact.get("parsing.central_claim"):
            if case["central_claim"] != expected_exact["parsing.central_claim"]:
                errors.append(f"case {case_id} central_claim conflicts with expected parsing.central_claim")

        if case.get("claim_type") and expected_exact.get("classification.claim_type"):
            if case["claim_type"] != expected_exact["classification.claim_type"]:
                errors.append(f"case {case_id} claim_type conflicts with expected classification.claim_type")

        expected_decision = case.get("expected_decision") or {}
        expected_recommendation = expected_decision.get("recommendation")
        expected_band = expected_decision.get("recommendation_band")
        expected_human = expected_decision.get("human_escalation_required")

        if expected_recommendation and expected_exact.get("decision.recommendation"):
            if expected_recommendation != expected_exact["decision.recommendation"]:
                errors.append(f"case {case_id} expected_decision.recommendation conflicts with expected decision.recommendation")

        if expected_band and case["expected"].get("recommendation_band"):
            if expected_band != case["expected"]["recommendation_band"]:
                errors.append(f"case {case_id} expected_decision.recommendation_band conflicts with expected.recommendation_band")

        if expected_human is not None and expected_exact.get("decision.human_escalation_required") is not None:
            if expected_human != expected_exact["decision.human_escalation_required"]:
                errors.append(
                    f"case {case_id} expected_decision.human_escalation_required conflicts with expected decision.human_escalation_required"
                )

        if expected_recommendation and expected_band:
            derived_band = _recommendation_band(expected_recommendation)
            if derived_band and expected_band != derived_band:
                errors.append(
                    f"case {case_id} expected_decision mixes incompatible recommendation {expected_recommendation} and band {expected_band}"
                )

    if errors:
        raise ValueError("\n".join(errors))


def load_goldset_manifest(manifest_path: str | Path | None = None) -> dict[str, Any]:
    manifest_file = Path(manifest_path) if manifest_path else _default_manifest()
    raw_manifest = yaml.safe_load(manifest_file.read_text(encoding="utf-8")) or {}
    normalized = _normalize_manifest(raw_manifest)
    validate_goldset_manifest(normalized, manifest_path=manifest_file)
    return _normalize_manifest_runtime_paths(normalized, manifest_file=manifest_file)


def load_holdout_cases(manifest_path: str | Path | None = None) -> list[dict[str, Any]]:
    manifest = load_goldset_manifest(manifest_path or _default_holdout_manifest())
    return [dict(case) for case in manifest["cases"] if case["split"] == HOLDOUT_SPLIT]


def _current_operator_identifier() -> str | None:
    return os.environ.get("GITHUB_ACTOR") or os.environ.get("USER") or os.environ.get("USERNAME")


def _current_git_metadata() -> dict[str, Any]:
    root = repo_root()
    in_repo_code, _ = git_output(["rev-parse", "--is-inside-work-tree"], cwd=root)
    if in_repo_code != 0:
        return {"commit_sha": None, "git_dirty": None}

    sha_code, sha_output = git_output(["rev-parse", "HEAD"], cwd=root)
    dirty_code, dirty_output = git_output(["status", "--porcelain"], cwd=root)
    return {
        "commit_sha": sha_output if sha_code == 0 else None,
        "git_dirty": bool(dirty_output) if dirty_code == 0 else None,
    }


def _new_stats() -> dict[str, int]:
    return {"total": 0, "passed": 0, "failed": 0, "scaffold": 0}


def _summarize_observed_surface(record: dict[str, Any]) -> dict[str, Any]:
    return {path: _safe_get_by_path(record, path) for path in OBSERVED_PATHS}


def _classify_missing_path(dotted_path: str) -> str:
    if dotted_path.startswith("pack_execution.") or dotted_path.startswith("pack_results"):
        return "pack_behavior_failure"
    return "missing_required_evidence_anchor"


def _expected_case_is_blocking(case: dict[str, Any]) -> bool:
    expected = case["expected"]["exact"]
    recommendation = expected.get("decision.recommendation")
    return (
        expected.get("reviewability.status") == "fail"
        or expected.get("scientific_record.status") == "fatal_fail"
        or expected.get("integrity.status") == "escalate"
        or recommendation in {"NON_REVIEWABLE", "DO_NOT_SUBMIT"}
    )


def _actual_case_is_fatal(observed: dict[str, Any]) -> bool:
    recommendation = observed["decision.recommendation"]
    return (
        observed["scientific_record.status"] == "fatal_fail"
        or observed["integrity.status"] == "escalate"
        or recommendation == "DO_NOT_SUBMIT"
    )


def _case_expects_specialist_viability(case: dict[str, Any]) -> bool:
    return "specialist_viable" in case["tags"] or case["expected"]["exact"].get("decision.recommendation") == "RETARGET_SPECIALIST"


def _base_error_class_for_mismatch(case: dict[str, Any], dotted_path: str) -> str | None:
    if dotted_path == "scientific_record.status":
        expected = case["expected"]["exact"].get(dotted_path)
        if expected == "fatal_fail":
            return "missed_fatal_gate"
    if dotted_path == "integrity.status":
        expected = case["expected"]["exact"].get(dotted_path)
        if expected == "escalate":
            return "missed_fatal_gate"
    return EXPECTED_PATH_ERROR_CLASSES.get(dotted_path)


def _contextual_error_classes(
    case: dict[str, Any],
    observed: dict[str, Any],
    mismatches: list[dict[str, Any]],
    missing_required_paths: list[str],
    record: dict[str, Any],
) -> list[str]:
    classes = {item["error_class"] for item in mismatches if item.get("error_class")}
    classes.update(_classify_missing_path(path) for path in missing_required_paths)

    if case["pack_paths"] and (record["pack_execution"]["pack_load_failures"] or not record["pack_results"]):
        classes.add("pack_behavior_failure")

    recommendation = observed["decision.recommendation"]
    recommendation_band = _recommendation_band(recommendation)
    if _expected_case_is_blocking(case):
        if recommendation_band in POSITIVE_RECOMMENDATION_BANDS:
            classes.add("false_accept_on_fatal_case")
        if recommendation not in BLOCKING_RECOMMENDATIONS:
            classes.add("missed_fatal_gate")

    if not _expected_case_is_blocking(case) and _actual_case_is_fatal(observed):
        classes.add("hallucinated_fatal_gate")

    if _case_expects_specialist_viability(case) and recommendation in BLOCKING_RECOMMENDATIONS:
        classes.add("false_desk_reject_on_viable_specialist_case")

    if case["ambiguity_class"] != "none" and (mismatches or missing_required_paths):
        classes.add("ambiguous_case_mismatch")

    if (mismatches or missing_required_paths) and not classes:
        classes.add("underspecified_expectation")

    return sorted(classes)


def _compare_exact_expectations(case: dict[str, Any], record: dict[str, Any]) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    for dotted_path, expected_value in case["expected"]["exact"].items():
        actual_value = _safe_get_by_path(record, dotted_path)
        if actual_value != expected_value:
            mismatches.append(
                {
                    "path": dotted_path,
                    "comparison": "exact",
                    "expected": expected_value,
                    "actual": actual_value,
                    "error_class": _base_error_class_for_mismatch(case, dotted_path),
                }
            )

    recommendation_band = case["expected"].get("recommendation_band")
    if recommendation_band:
        actual_recommendation = _safe_get_by_path(record, "decision.recommendation")
        actual_band = _recommendation_band(actual_recommendation)
        if actual_band != recommendation_band:
            mismatches.append(
                {
                    "path": "decision.recommendation",
                    "comparison": "band",
                    "expected": recommendation_band,
                    "actual": actual_recommendation,
                    "actual_band": actual_band,
                    "error_class": "wrong_recommendation",
                }
            )

    return mismatches


def _missing_required_paths(case: dict[str, Any], record: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for dotted_path in case.get("required_nonempty_paths", []):
        actual_value = _safe_get_by_path(record, dotted_path)
        if not is_nonempty(actual_value):
            missing.append(dotted_path)
    return missing


def _decision_consistency_status(expected_decision: dict[str, Any], actual_recommendation: str | None) -> str:
    if actual_recommendation is None:
        return "unavailable"
    expected_recommendation = expected_decision.get("recommendation")
    expected_band = expected_decision.get("recommendation_band") or _recommendation_band(expected_recommendation)
    actual_band = _recommendation_band(actual_recommendation)
    if expected_recommendation and actual_recommendation == expected_recommendation:
        return "exact_match"
    if expected_band and actual_band == expected_band:
        return "band_match"
    if expected_recommendation or expected_band:
        return "mismatch"
    return "unavailable"


def _empty_editorial_first_pass() -> dict[str, Any]:
    return {
        "abstract_clarity": None,
        "novelty_explicitness": None,
        "evidence_visibility": None,
        "total": None,
    }


def _build_editorial_first_pass(payload: dict[str, Any]) -> dict[str, int]:
    abstract = str(payload.get("abstract") or "")
    manuscript_text = str(payload.get("manuscript_text") or "")
    abstract_lower = abstract.lower()
    combined_text = f"{abstract} {manuscript_text}".lower()

    abstract_clarity = 0
    if abstract.strip():
        abstract_clarity += 1
        if len(abstract.split()) >= 20:
            abstract_clarity += 1
        if any(marker in abstract_lower for marker in EDITORIAL_FIRST_PASS_SENTENCE_MARKERS):
            abstract_clarity += 1
        if any(char.isdigit() for char in abstract) or "%" in abstract or "relative to" in abstract_lower:
            abstract_clarity += 1

    novelty_explicitness = 0
    if combined_text.strip():
        if any(marker in combined_text for marker in EDITORIAL_FIRST_PASS_SENTENCE_MARKERS):
            novelty_explicitness += 1
        if any(marker in combined_text for marker in EDITORIAL_FIRST_PASS_NOVELTY_MARKERS):
            novelty_explicitness += 1
        if any(token in combined_text for token in ("improves", "reduces", "outperforms", "compares", "replication workflow")):
            novelty_explicitness += 1

    evidence_visibility = 0
    if payload.get("figures_and_captions"):
        evidence_visibility += 1
    if payload.get("tables"):
        evidence_visibility += 1
    if payload.get("references"):
        evidence_visibility += 1
    if any(is_nonempty(payload.get(field)) for field in ("data_availability", "code_availability", "materials_availability")):
        evidence_visibility += 1

    return {
        "abstract_clarity": abstract_clarity,
        "novelty_explicitness": novelty_explicitness,
        "evidence_visibility": evidence_visibility,
        "total": abstract_clarity + novelty_explicitness + evidence_visibility,
    }


def _decision_score(error_classes: list[str], severity_weights: dict[str, float]) -> float:
    counts = Counter(error_classes)
    return _rounded(sum(severity_weights.get(error_class, 1) * count for error_class, count in counts.items()))


def _recommendation_bias(expected_decision: dict[str, Any], actual_recommendation: str | None) -> int | None:
    expected_recommendation = expected_decision.get("recommendation")
    expected_band = expected_decision.get("recommendation_band") or _recommendation_band(expected_recommendation)
    expected_ordinal = _recommendation_ordinal(expected_recommendation, expected_band)
    actual_ordinal = _recommendation_ordinal(actual_recommendation, _recommendation_band(actual_recommendation))
    if expected_ordinal is None or actual_ordinal is None:
        return None
    return actual_ordinal - expected_ordinal


def _recommendation_loss(
    expected_decision: dict[str, Any],
    actual_recommendation: str | None,
    loss_matrix: dict[str, dict[str, int]],
) -> int:
    expected_recommendation = expected_decision.get("recommendation")
    expected_band = expected_decision.get("recommendation_band") or _recommendation_band(expected_recommendation)
    actual_band = _recommendation_band(actual_recommendation)
    if expected_band is None or actual_band is None:
        return 0
    return loss_matrix.get(expected_band, {}).get(actual_band, 0)


def _forecast_from_total_score(
    total_score: float,
    *,
    expected_band: str | None,
    actual_band: str | None,
    fatal_override: bool,
) -> str | None:
    if fatal_override:
        return expected_band if expected_band in {"fatal_block", "non_reviewable"} else "fatal_block"
    if total_score == 0:
        return expected_band or actual_band or "cautionary_viable"
    if expected_band in {"fatal_block", "non_reviewable"}:
        return expected_band
    if total_score <= 2:
        if expected_band in {"viable_with_reroute", "preprint_only", "cautionary_viable", "viable_journal"}:
            return expected_band
        return "cautionary_viable"
    if total_score <= 4:
        return "preprint_only"
    if total_score <= 7:
        return "repair_required"
    return "fatal_block"


def _author_recommendation_for_forecast(forecast: str | None, expected_decision: dict[str, Any]) -> str | None:
    expected_recommendation = expected_decision.get("recommendation")
    if forecast == "fatal_block":
        return expected_recommendation if _recommendation_band(expected_recommendation) == "fatal_block" else "DO_NOT_SUBMIT"
    if forecast == "non_reviewable":
        return expected_recommendation if expected_recommendation == "NON_REVIEWABLE" else "NON_REVIEWABLE"
    if forecast == "repair_required":
        if expected_recommendation in {"REBUILD_BEFORE_SUBMISSION", "REVISE_BEFORE_SUBMISSION"}:
            return expected_recommendation
        return "REVISE_BEFORE_SUBMISSION"
    if forecast == "viable_with_reroute":
        if expected_recommendation in {"RETARGET_SPECIALIST", "RETARGET_SOUNDNESS_FIRST"}:
            return expected_recommendation
        return "RETARGET_SPECIALIST"
    if forecast == "preprint_only":
        return (
            expected_recommendation
            if expected_recommendation == "PREPRINT_READY_NOT_JOURNAL_READY"
            else "PREPRINT_READY_NOT_JOURNAL_READY"
        )
    if forecast == "cautionary_viable":
        return expected_recommendation if expected_recommendation == "SUBMIT_WITH_CAUTION" else "SUBMIT_WITH_CAUTION"
    if forecast == "viable_journal":
        return expected_recommendation if expected_recommendation == "PLAUSIBLE_SEND_OUT" else "PLAUSIBLE_SEND_OUT"
    return expected_recommendation


def _editorial_plausibility_flags(
    case: dict[str, Any],
    error_classes: list[str],
    recommendation_bias: int | None,
    recommendation_loss: int,
    fatal_override: bool,
    consistency_status: str,
) -> list[str]:
    flags: set[str] = set()
    if fatal_override:
        flags.add("fatal_override")
    if recommendation_bias is not None:
        if recommendation_bias > 0:
            flags.add("permissive_bias")
        elif recommendation_bias < 0:
            flags.add("conservative_bias")
    if recommendation_loss >= 3:
        flags.add("high_recommendation_loss")
    if {"wrong_central_claim", "wrong_claim_type"}.intersection(error_classes):
        flags.add("claim_frame_mismatch")
    if "pack_behavior_failure" in error_classes:
        flags.add("pack_instability")
    if case["ambiguity_class"] != "none" and consistency_status == "mismatch":
        flags.add("borderline_case_mismatch")
    if consistency_status == "mismatch":
        flags.add("decision_inconsistency")
    return sorted(flags)


def _build_case_decision_metrics(
    case: dict[str, Any],
    record: dict[str, Any],
    payload: dict[str, Any],
    observed: dict[str, Any],
    error_classes: list[str],
    governance: dict[str, Any],
    editorial_first_pass: dict[str, Any],
    case_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    case_history = case_history or []
    actual_recommendation = observed.get("decision.recommendation")
    expected_decision = case["expected_decision"]
    expected_band = expected_decision.get("recommendation_band") or _recommendation_band(expected_decision.get("recommendation"))
    actual_band = _recommendation_band(actual_recommendation)
    scientific_weights = _canonicalize_weights(governance["scientific_weights"], SCIENTIFIC_WEIGHT_ALIASES)
    editorial_weights = _canonicalize_weights(governance["editorial_weights"], EDITORIAL_WEIGHT_ALIASES)
    scientific_score = _scientific_score(record)
    legacy_scientific_score = scientific_score.as_dict()
    scientific_score_total = _weighted_total(legacy_scientific_score, scientific_weights)
    scientific_score_vector = _scientific_score_vector(record, payload).as_dict()
    legacy_scientific_score_vector = {**legacy_scientific_score, "total": scientific_score_total}
    editorial_score = _build_editorial_score(payload, editorial_first_pass)
    editorial_score_vector = editorial_score.as_dict()
    editorial_score_total = _editorial_quality_total(editorial_score, editorial_weights)
    raw_decision_score = _decision_score(error_classes, governance["severity_weights"])
    recommendation_bias = _recommendation_bias(expected_decision, actual_recommendation)
    raw_recommendation_loss = _recommendation_loss(expected_decision, actual_recommendation, governance["recommendation_loss_matrix"])
    raw_scientific_loss = _rounded(raw_decision_score + raw_recommendation_loss)
    fatal_override = bool(FATAL_OVERRIDE_ERROR_CLASSES.intersection(error_classes))
    decision_margin = _decision_boundary_margin(actual_recommendation)
    raw_editorial_penalty = _editorial_penalty(editorial_score, governance, boundary_margin=decision_margin)
    if raw_editorial_penalty > 0:
        assert raw_editorial_penalty < decision_margin, "editorial penalty must remain non-gating"
    raw_total_score = _rounded(raw_scientific_loss + raw_editorial_penalty)
    decision_consistency_status = _decision_consistency_status(expected_decision, actual_recommendation)
    editorial_forecast = _forecast_from_total_score(
        raw_total_score,
        expected_band=expected_band,
        actual_band=actual_band,
        fatal_override=fatal_override,
    )
    author_recommendation = _author_recommendation_for_forecast(editorial_forecast, expected_decision)
    editorial_flags = _editorial_plausibility_flags(
        case,
        error_classes,
        recommendation_bias,
        raw_recommendation_loss,
        fatal_override,
        decision_consistency_status,
    )
    editorial_anomalies = _editorial_anomalies(payload, record)
    if editorial_anomalies["triggered"]:
        editorial_flags = sorted({*editorial_flags, "editorial_anomaly_detected"})
    exported_decision_score = _quantize_loss_output(raw_decision_score, governance)
    exported_recommendation_loss = _quantize_loss_output(raw_recommendation_loss, governance)
    exported_scientific_loss = _quantize_loss_output(raw_scientific_loss, governance)
    exported_editorial_penalty = _quantize_loss_output(raw_editorial_penalty, governance)
    exported_total_score = _quantize_loss_output(raw_total_score, governance)
    loss_band = _loss_band(exported_scientific_loss)
    scientific_surface_bundle = governance_surface_contract.build_scientific_surface_bundle(
        legacy_surface=legacy_scientific_score_vector,
        native_surface=scientific_score_vector,
    )
    case_metrics = {
        "scientific_score": legacy_scientific_score_vector,
        **scientific_surface_bundle,
        "editorial_score": {**editorial_score_vector, "total": editorial_score_total},
        "scientific_recommendation": actual_recommendation,
        "scientific_recommendation_band": actual_band,
        "decision_confidence": record.get("decision", {}).get("confidence"),
        "scientific_loss": exported_scientific_loss,
        "editorial_penalty": exported_editorial_penalty,
        "total_loss": exported_total_score,
        "boundary_margin": decision_margin,
        "decision_score": exported_decision_score,
        "recommendation_bias": recommendation_bias,
        "recommendation_loss": exported_recommendation_loss,
        "loss_band": loss_band,
        "total_score": exported_total_score,
        "editorial_forecast": editorial_forecast,
        "author_recommendation": author_recommendation,
        "fatal_override": fatal_override,
        "decision_consistency_status": decision_consistency_status,
        "editorial_plausibility_flags": editorial_flags,
        "editorial_anomalies": editorial_anomalies,
    }
    counterfactual_analysis = _counterfactual_analysis({**case_metrics, "case_id": case["case_id"], "error_classes": error_classes}, governance)
    counterfactuals = counterfactual_analysis["counterfactuals"]
    case_metrics["drift_counterfactual"] = counterfactuals[0] if counterfactuals else None
    case_metrics["drift_counterfactuals"] = counterfactuals
    case_metrics["drift_counterfactual_stability"] = counterfactual_analysis["stability"]
    surface_contract = governance_router.validate_scoring_surface_contract(
        legacy_scientific_score_vector,
        scientific_score_vector,
        governance,
        payload_input=payload,
    )
    if surface_contract is not None:
        case_metrics["surface_contract"] = surface_contract
    return case_metrics


def _holdout_runtime_guard(case: dict[str, Any], evaluation_mode: str) -> None:
    if case["split"] == HOLDOUT_SPLIT and evaluation_mode != HOLDOUT_BLIND_EVALUATION_MODE:
        raise RuntimeError(
            f"holdout case {case['case_id']} may not execute in development mode; use holdout_eval to run blind holdout evaluation"
        )
    if case["split"] != HOLDOUT_SPLIT and evaluation_mode == HOLDOUT_BLIND_EVALUATION_MODE:
        raise RuntimeError(f"non-holdout case {case['case_id']} may not execute in holdout blind evaluation mode")


def _resolve_case_pack_path(manifest_file: Path, raw_path: str) -> str:
    pack_path = Path(raw_path).expanduser()
    if pack_path.is_absolute():
        return str(pack_path.resolve())
    manifest_relative = (manifest_file.parent / pack_path).resolve()
    if manifest_relative.exists():
        return str(manifest_relative)
    repo_relative = (repo_root() / pack_path).resolve()
    if repo_relative.exists():
        return str(repo_relative)
    return str(manifest_relative)


def _redact_holdout_result(result: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(result)
    redacted["central_claim"] = None
    redacted["claim_type"] = None
    redacted["expected"] = {"exact": {}}
    redacted["expected_decision"] = {
        "recommendation": None,
        "recommendation_band": None,
        "human_escalation_required": None,
    }
    redacted["mismatches"] = [{**mismatch, "expected": None} for mismatch in result["mismatches"]]
    redacted["scientific_recommendation"] = None
    redacted["scientific_recommendation_band"] = None
    redacted["decision_confidence"] = None
    redacted["scientific_score"] = {
        "evidence_alignment": None,
        "methodological_validity": None,
        "reproducibility": None,
        "falsifiability": None,
        "baseline_comparison": None,
        "total": None,
    }
    redacted.update(
        governance_surface_contract.build_scientific_surface_bundle(
            legacy_surface=_masked_legacy_scientific_score_vector(),
            native_surface=_masked_scientific_score_vector(),
        )
    )
    redacted["editorial_score"] = {
        "clarity": None,
        "novelty_explicitness": None,
        "structure_quality": None,
        "rhetorical_density": None,
        "total": None,
    }
    redacted["scientific_loss"] = None
    redacted["editorial_penalty"] = None
    redacted["total_loss"] = None
    redacted["boundary_margin"] = None
    redacted["decision_score"] = None
    redacted["recommendation_bias"] = None
    redacted["recommendation_loss"] = None
    redacted["loss_band"] = result.get("loss_band")
    redacted["total_score"] = None
    redacted["editorial_forecast"] = None
    redacted["author_recommendation"] = None
    redacted["decision_consistency_status"] = "masked_holdout"
    redacted["drift_counterfactual"] = None
    redacted["drift_counterfactuals"] = []
    redacted["drift_counterfactual_stability"] = None
    redacted["editorial_plausibility_flags"] = []
    redacted["editorial_anomalies"] = {
        "novelty_density": None,
        "claim_to_evidence_ratio": None,
        "rhetorical_intensity": None,
        "triggered": [],
    }
    if "leakage_guard" in redacted:
        redacted["leakage_guard"] = {
            "rank_jitter_applied": bool(redacted["leakage_guard"].get("rank_jitter_applied")),
            "noise_scale": None,
            "query_budget": redacted["leakage_guard"].get("query_budget", 0),
            "epsilon_budget": None,
            "budget_used": redacted["leakage_guard"].get("budget_used", 0),
            "governance_version": redacted["leakage_guard"].get("governance_version"),
        }
    if "counterfactual_extended" in redacted:
        redacted["counterfactual_extended"] = {
            "stability": None,
            "identifiability": redacted["counterfactual_extended"].get("identifiability"),
            "identifiability_status": redacted["counterfactual_extended"].get("identifiability_status"),
            "interaction_strength": None,
            "conditional_importance": {},
            "interaction_matrix": {},
            "attribution_rank": 0,
        }
    if "invariance_trace" in redacted:
        redacted["invariance_trace"] = {
            "trace_hash": None,
            "drift_detected": bool(redacted["invariance_trace"].get("drift_detected")),
            "drift_score": None,
        }
    redacted["expected_redacted"] = True
    return redacted


def _holdout_noise_delta(case_id: str, manifest_sha256: str, jitter: int) -> int:
    if jitter <= 0:
        return 0
    digest = hashlib.sha256(f"{manifest_sha256}:{case_id}:holdout-noise-v1".encode("utf-8")).hexdigest()
    return (int(digest[:4], 16) % (jitter * 2 + 1)) - jitter


def _obfuscate_holdout_result(
    result: dict[str, Any],
    *,
    manifest_sha256: str,
    governance: dict[str, Any],
) -> dict[str, Any]:
    obfuscated = _redact_holdout_result(result)
    blindness = governance["holdout_blindness"]
    noise_config = governance["holdout_noise"]
    jitter = noise_config["error_count_jitter"]
    noisy_count = max(0, len(result["error_classes"]) + _holdout_noise_delta(result["case_id"], manifest_sha256, jitter))
    obfuscated["error_classes"] = [HOLDOUT_MASKED_ERROR_CLASS] * noisy_count
    if blindness["error_class_binning"]:
        binned_counts: Counter[str] = Counter(_error_class_bin(error_class) for error_class in result["error_classes"])
        obfuscated["error_class_bins"] = dict(sorted(binned_counts.items()))
        grouped_counts: Counter[str] = Counter(_error_class_group(error_class) for error_class in result["error_classes"])
        obfuscated["error_class_groups"] = dict(sorted(grouped_counts.items()))
    else:
        obfuscated["error_class_bins"] = {}
        obfuscated["error_class_groups"] = {}
    if blindness["recommendation_bins"]:
        actual_band = _recommendation_band(result["decision_recommendation"])
        obfuscated["recommendation_bin"] = HOLDOUT_RECOMMENDATION_BINS.get(actual_band)
    else:
        obfuscated["recommendation_bin"] = None
    if blindness["pass_fail_jitter"]:
        obfuscated["status"] = _holdout_pass_fail_state(result["case_id"], manifest_sha256)
    base_loss = float(result.get("scientific_loss") or 0.0)
    noisy_loss = apply_holdout_noise(
        base_loss,
        float(noise_config.get("loss_epsilon", 0.0)),
        _stable_seed(manifest_sha256, result["case_id"], "holdout-loss"),
    )
    obfuscated["loss_band"] = _loss_band(noisy_loss)
    if noise_config["mask_recommendations"]:
        obfuscated["decision_recommendation"] = None
    return obfuscated


def _evaluate_case(
    case: dict[str, Any],
    *,
    case_root: Path,
    manifest_file: Path,
    extra_pack_paths: list[str] | None,
    evaluation_mode: str,
    governance: dict[str, Any],
    case_history: list[dict[str, Any]],
) -> dict[str, Any]:
    _holdout_runtime_guard(case, evaluation_mode)

    if case["case_state"] == "scaffold":
        result = {
            "case_id": case["case_id"],
            "stratum": case["stratum"],
            "partition": case["partition"],
            "category": case["category"],
            "case_state": case["case_state"],
            "gate_behavior": case["gate_behavior"],
            "ambiguity_class": case["ambiguity_class"],
            "tags": case["tags"],
            "central_claim": case.get("central_claim"),
            "claim_type": case.get("claim_type"),
            "expected": case["expected"],
            "expected_decision": case["expected_decision"],
            "expected_redacted": False,
            "status": "scaffold",
            "observed": {},
            "mismatches": [],
            "missing_required_paths": [],
            "error_classes": [],
            "decision_recommendation": None,
            "scientific_recommendation": None,
            "scientific_recommendation_band": None,
            "decision_confidence": None,
            "scientific_score": {**ScientificScore(0.0, 0.0, 0.0, 0.0, 0.0).as_dict(), "total": 0.0},
            **governance_surface_contract.build_scientific_surface_bundle(
                legacy_surface={**ScientificScore(0.0, 0.0, 0.0, 0.0, 0.0).as_dict(), "total": 0.0},
                native_surface=_empty_scientific_score_vector(),
            ),
            "editorial_score": {**EditorialScore(0.0, 0.0, 0.0, 0.0).as_dict(), "total": 0.0},
            "scientific_loss": None,
            "editorial_penalty": None,
            "total_loss": None,
            "boundary_margin": None,
            "decision_score": None,
            "recommendation_bias": None,
            "recommendation_loss": None,
            "loss_band": None,
            "total_score": None,
            "editorial_forecast": None,
            "author_recommendation": None,
            "fatal_override": False,
            "decision_consistency_status": "scaffold",
            "drift_counterfactual": None,
            "drift_counterfactuals": [],
            "drift_counterfactual_stability": None,
            "editorial_plausibility_flags": [],
            "editorial_anomalies": {
                "novelty_density": 0.0,
                "claim_to_evidence_ratio": 0.0,
                "rhetorical_intensity": 0.0,
                "triggered": [],
            },
            "editorial_first_pass": _empty_editorial_first_pass(),
        }
        return result

    payload = read_json(case_root / case["input"])
    case_pack_paths = [_resolve_case_pack_path(manifest_file, path) for path in case.get("pack_paths", [])]
    merged_pack_paths = [*case_pack_paths, *(extra_pack_paths or [])]
    governance_router.validate_input_surface_contract(payload, governance)
    record = run_audit(payload, pack_paths=merged_pack_paths)

    mismatches = _compare_exact_expectations(case, record)
    missing_required_paths = _missing_required_paths(case, record)
    observed = _summarize_observed_surface(record)
    error_classes = _contextual_error_classes(case, observed, mismatches, missing_required_paths, record)
    ok = not mismatches and not missing_required_paths
    editorial_first_pass = _build_editorial_first_pass(payload)
    decision_metrics = _build_case_decision_metrics(
        case,
        record,
        payload,
        observed,
        error_classes,
        governance,
        editorial_first_pass,
        case_history,
    )

    result = {
        "case_id": case["case_id"],
        "stratum": case["stratum"],
        "partition": case["partition"],
        "category": case["category"],
        "case_state": case["case_state"],
        "gate_behavior": case["gate_behavior"],
        "ambiguity_class": case["ambiguity_class"],
        "tags": case["tags"],
        "central_claim": case.get("central_claim"),
        "claim_type": case.get("claim_type"),
        "expected": case["expected"],
        "expected_decision": case["expected_decision"],
        "expected_redacted": False,
        "status": "pass" if ok else "fail",
        "observed": observed,
        "mismatches": mismatches,
        "missing_required_paths": missing_required_paths,
        "error_classes": error_classes,
        "decision_recommendation": observed["decision.recommendation"],
        "editorial_first_pass": editorial_first_pass,
        **decision_metrics,
    }
    return governance_router.apply_case_governance(
        result,
        observed=observed,
        governance=governance,
        case_history=case_history,
    )


def _load_ledger_entries(ledger_path: Path | None) -> list[dict[str, Any]]:
    if ledger_path is None or not ledger_path.exists():
        return []

    schema = load_goldset_ledger_entry_schema()
    Draft202012Validator.check_schema(schema)
    entries: list[dict[str, Any]] = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        validate(instance=entry, schema=schema)
        entries.append(entry)
    return entries


def _validate_reason_code_namespace(reason_codes: list[str] | None) -> None:
    unknown = sorted(set(reason_codes or []) - GOVERNANCE_REASON_CODES)
    if unknown:
        raise ValueError(f"unknown governance reason codes: {', '.join(unknown)}")


def _validate_error_class_namespace(error_classes: list[str] | None) -> None:
    unknown = sorted(set(error_classes or []) - KNOWN_GOLDSET_ERROR_CLASSES)
    if unknown:
        raise ValueError(f"unknown goldset error classes: {', '.join(unknown)}")


def _validate_governance_report_namespace(governance_report: dict[str, Any]) -> None:
    contract_status = governance_report.get("contract_status") or {}
    warning_mode = governance_report.get("warning_mode") or {}
    _validate_reason_code_namespace(contract_status.get("hard_fail_reason_codes"))
    _validate_reason_code_namespace(contract_status.get("soft_warning_reason_codes"))
    _validate_reason_code_namespace(warning_mode.get("reason_codes"))
    for layer in (governance_report.get("layers") or {}).values():
        _validate_reason_code_namespace((layer or {}).get("hard_fail_reason_codes"))
        _validate_reason_code_namespace((layer or {}).get("soft_warning_reason_codes"))


def _validate_case_governance_namespace(case: dict[str, Any]) -> None:
    surface_contract = case.get("surface_contract") or {}
    _validate_reason_code_namespace(surface_contract.get("reason_codes"))
    counterfactual_extended = case.get("counterfactual_extended") or {}
    warning = counterfactual_extended.get("warning")
    if warning:
        _validate_reason_code_namespace([warning])


def _case_histories(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    history: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        for outcome in entry.get("case_outcomes", []):
            history.setdefault(outcome["case_id"], []).append(outcome)
    return history


def _ledger_entry_evaluation_mode(entry: dict[str, Any]) -> str:
    return entry.get("evaluation_mode", DEVELOPMENT_EVALUATION_MODE)


def _case_outcome_index(case_results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {case["case_id"]: case for case in case_results}


def _build_case_deltas(case_results: list[dict[str, Any]], prior_entry: dict[str, Any] | None) -> dict[str, Any]:
    if not prior_entry:
        return {
            "available": False,
            "prior_generated_at_utc": None,
            "changed_case_count": 0,
            "unchanged_case_count": len(case_results),
            "cases": [],
        }

    previous_cases = _case_outcome_index(prior_entry.get("case_outcomes", []))
    deltas: list[dict[str, Any]] = []
    unchanged = 0
    for case in case_results:
        previous = previous_cases.get(case["case_id"])
        if previous is None:
            deltas.append(
                {
                    "case_id": case["case_id"],
                    "change_type": "new_case",
                    "previous_status": None,
                    "current_status": case["status"],
                    "previous_recommendation": None,
                    "current_recommendation": case["decision_recommendation"],
                    "new_error_classes": case["error_classes"],
                    "resolved_error_classes": [],
                }
            )
            continue

        new_error_classes = sorted(set(case["error_classes"]) - set(previous.get("error_classes", [])))
        resolved_error_classes = sorted(set(previous.get("error_classes", [])) - set(case["error_classes"]))
        previous_recommendation = previous.get("decision_recommendation")
        recommendation_changed = previous_recommendation != case["decision_recommendation"]
        status_changed = previous.get("status") != case["status"]
        observed_changed = previous.get("observed", {}) != case["observed"]
        if not (new_error_classes or resolved_error_classes or recommendation_changed or status_changed or observed_changed):
            unchanged += 1
            continue

        deltas.append(
            {
                "case_id": case["case_id"],
                "change_type": "changed",
                "previous_status": previous.get("status"),
                "current_status": case["status"],
                "previous_recommendation": previous_recommendation,
                "current_recommendation": case["decision_recommendation"],
                "new_error_classes": new_error_classes,
                "resolved_error_classes": resolved_error_classes,
            }
        )

    return {
        "available": True,
        "prior_generated_at_utc": prior_entry["generated_at_utc"],
        "changed_case_count": len(deltas),
        "unchanged_case_count": unchanged,
        "cases": deltas,
    }


def _aggregate_recommendation_changes(case_deltas: dict[str, Any]) -> dict[str, Any]:
    if not case_deltas["available"]:
        return {"available": False, "total_changed_cases": 0, "by_transition": {}}

    counter: Counter[str] = Counter()
    for delta in case_deltas["cases"]:
        previous = delta["previous_recommendation"]
        current = delta["current_recommendation"]
        if previous != current:
            counter[f"{previous or 'None'} -> {current or 'None'}"] += 1

    return {
        "available": True,
        "total_changed_cases": sum(counter.values()),
        "by_transition": dict(sorted(counter.items())),
    }


def _count_error_classes(case_results: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for case in case_results:
        for error_class in case["error_classes"]:
            counter[error_class] += 1
    return dict(sorted(counter.items()))


def _count_editorial_plausibility_flags(case_results: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for case in case_results:
        for flag in case.get("editorial_plausibility_flags", []):
            counter[flag] += 1
    return dict(sorted(counter.items()))


def _count_editorial_anomaly_triggers(case_results: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for case in case_results:
        for trigger in case.get("editorial_anomalies", {}).get("triggered", []):
            counter[trigger] += 1
    return dict(sorted(counter.items()))


def _build_score_vector_summary(case_results: list[dict[str, Any]], field_name: str) -> dict[str, Any]:
    active_vectors = [case.get(field_name) or {} for case in case_results if case["case_state"] == "active"]
    keys = sorted({key for vector in active_vectors for key in vector})
    summary: dict[str, Any] = {"case_count": len(active_vectors)}
    for key in keys:
        values = [vector.get(key) for vector in active_vectors if vector.get(key) is not None]
        summary[f"mean_{key}"] = _mean(values)
    return summary


def _build_decision_algebra_summary(case_results: list[dict[str, Any]], governance: dict[str, Any]) -> dict[str, Any]:
    forecast_counts: Counter[str] = Counter()
    author_recommendation_counts: Counter[str] = Counter()
    total_decision_score = 0.0
    total_recommendation_loss = 0
    total_scientific_loss = 0.0
    total_editorial_penalty = 0.0
    total_score = 0.0
    fatal_override_cases = 0
    boundary_margins: list[float] = []

    for case in case_results:
        if case["case_state"] != "active":
            continue
        total_decision_score += case["decision_score"] or 0
        total_recommendation_loss += case["recommendation_loss"] or 0
        total_scientific_loss += case.get("scientific_loss") or 0
        total_editorial_penalty += case.get("editorial_penalty") or 0
        total_score += case["total_score"] or 0
        if case.get("boundary_margin") is not None:
            boundary_margins.append(case["boundary_margin"])
        if case["fatal_override"]:
            fatal_override_cases += 1
        if case.get("editorial_forecast"):
            forecast_counts[case["editorial_forecast"]] += 1
        if case.get("author_recommendation"):
            author_recommendation_counts[case["author_recommendation"]] += 1

    return {
        "severity_weights": governance["severity_weights"],
        "fatal_weight_scale": governance["fatal_weight_scale"],
        "recommendation_loss_model": "asymmetric_matrix",
        "fatal_override_error_classes": sorted(FATAL_OVERRIDE_ERROR_CLASSES),
        "plane_mode": governance["planes"]["mode"],
        "use_editorial_for_decision": governance["gating"]["use_editorial_for_decision"],
        "total_decision_score": _rounded(total_decision_score),
        "total_recommendation_loss": total_recommendation_loss,
        "total_scientific_loss": _rounded(total_scientific_loss),
        "total_editorial_penalty": _rounded(total_editorial_penalty),
        "total_score": _rounded(total_score),
        "fatal_override_cases": fatal_override_cases,
        "minimum_boundary_margin": min(boundary_margins) if boundary_margins else None,
        "editorial_forecast_counts": dict(sorted(forecast_counts.items())),
        "author_recommendation_counts": dict(sorted(author_recommendation_counts.items())),
    }


def _build_editorial_first_pass_summary(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    active_scores = [case["editorial_first_pass"] for case in case_results if case["case_state"] == "active"]
    totals = [score["total"] for score in active_scores if score.get("total") is not None]
    abstract_scores = [score["abstract_clarity"] for score in active_scores if score.get("abstract_clarity") is not None]
    novelty_scores = [score["novelty_explicitness"] for score in active_scores if score.get("novelty_explicitness") is not None]
    evidence_scores = [score["evidence_visibility"] for score in active_scores if score.get("evidence_visibility") is not None]
    return {
        "case_count": len(active_scores),
        "mean_total": _mean(totals),
        "mean_abstract_clarity": _mean(abstract_scores),
        "mean_novelty_explicitness": _mean(novelty_scores),
        "mean_evidence_visibility": _mean(evidence_scores),
        "max_total": max(totals) if totals else None,
        "min_total": min(totals) if totals else None,
    }


def _build_decision_consistency_summary(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for case in case_results:
        counts[case["decision_consistency_status"]] += 1
    comparable_cases = counts["exact_match"] + counts["band_match"] + counts["mismatch"]
    consistent_cases = counts["exact_match"] + counts["band_match"]
    return {
        "exact_match_cases": counts["exact_match"],
        "band_match_cases": counts["band_match"],
        "mismatch_cases": counts["mismatch"],
        "unavailable_cases": counts["unavailable"],
        "scaffold_cases": counts["scaffold"],
        "consistency_rate": _rounded(consistent_cases / comparable_cases) if comparable_cases else None,
    }


def _select_cases_for_run(manifest: dict[str, Any], *, holdout_eval: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    development_cases = [case for case in manifest["cases"] if case["split"] != HOLDOUT_SPLIT]
    holdout_cases = [case for case in manifest["cases"] if case["split"] == HOLDOUT_SPLIT]
    active_holdout_case_ids = [case["case_id"] for case in holdout_cases if case["case_state"] == "active"]
    scaffold_holdout_case_ids = [case["case_id"] for case in holdout_cases if case["case_state"] == "scaffold"]

    if holdout_eval:
        if not holdout_cases:
            raise ValueError("holdout evaluation requested but the manifest contains no split=holdout cases")
        return holdout_cases, {
            "mode": "blind_eval",
            "blind_evaluation": True,
            "active_case_count": len(active_holdout_case_ids),
            "scaffold_case_count": len(scaffold_holdout_case_ids),
            "excluded_case_ids": [],
            "evaluated_case_ids": active_holdout_case_ids,
            "redacted_case_ids": active_holdout_case_ids + scaffold_holdout_case_ids,
        }

    if not development_cases:
        raise ValueError("development evaluation requested but the manifest contains no split=dev cases")

    return development_cases, {
        "mode": "excluded" if holdout_cases else "not_present",
        "blind_evaluation": False,
        "active_case_count": len(active_holdout_case_ids),
        "scaffold_case_count": len(scaffold_holdout_case_ids),
        "excluded_case_ids": active_holdout_case_ids,
        "evaluated_case_ids": [],
        "redacted_case_ids": [],
    }


def _normalize_historical_case_outcome(
    outcome: dict[str, Any],
    manifest_case_index: dict[str, dict[str, Any]],
    governance: dict[str, Any],
) -> dict[str, Any]:
    case = manifest_case_index.get(outcome["case_id"], {})
    expected_decision = dict(outcome.get("expected_decision") or case.get("expected_decision") or {})
    if expected_decision.get("recommendation_band") is None:
        expected_decision["recommendation_band"] = _recommendation_band(expected_decision.get("recommendation"))

    decision_recommendation = outcome.get("decision_recommendation")
    decision_score = outcome.get("decision_score")
    if decision_score is None:
        decision_score = _decision_score(list(outcome.get("error_classes", [])), governance["severity_weights"])

    recommendation_bias = outcome.get("recommendation_bias")
    if recommendation_bias is None:
        recommendation_bias = _recommendation_bias(expected_decision, decision_recommendation)

    recommendation_loss = outcome.get("recommendation_loss")
    if recommendation_loss is None:
        recommendation_loss = _recommendation_loss(expected_decision, decision_recommendation, governance["recommendation_loss_matrix"])

    scientific_loss = outcome.get("scientific_loss")
    if scientific_loss is None:
        scientific_loss = _rounded(decision_score + recommendation_loss)

    total_score = outcome.get("total_score")
    if total_score is None:
        total_score = scientific_loss

    editorial_penalty = outcome.get("editorial_penalty")
    if editorial_penalty is None:
        editorial_penalty = _rounded(max((total_score or 0) - (scientific_loss or 0), 0))

    total_loss = outcome.get("total_loss")
    if total_loss is None:
        total_loss = total_score

    boundary_margin = outcome.get("boundary_margin")
    if boundary_margin is None:
        boundary_margin = _decision_boundary_margin(decision_recommendation)

    fatal_override = outcome.get("fatal_override")
    if fatal_override is None:
        fatal_override = bool(FATAL_OVERRIDE_ERROR_CLASSES.intersection(outcome.get("error_classes", [])))

    decision_consistency_status = outcome.get("decision_consistency_status")
    if decision_consistency_status is None:
        decision_consistency_status = _decision_consistency_status(expected_decision, decision_recommendation)

    expected_band = expected_decision.get("recommendation_band")
    actual_band = _recommendation_band(decision_recommendation)
    scientific_recommendation = outcome.get("scientific_recommendation", decision_recommendation)
    scientific_recommendation_band = outcome.get("scientific_recommendation_band", actual_band)
    decision_confidence = outcome.get("decision_confidence")
    scientific_score = outcome.get("scientific_score") or {
        "evidence_alignment": None,
        "methodological_validity": None,
        "reproducibility": None,
        "falsifiability": None,
        "baseline_comparison": None,
        "total": None,
    }
    scientific_surface_bundle = governance_surface_contract.build_scientific_surface_bundle(
        legacy_surface=scientific_score,
        native_surface=outcome.get("scientific_score_vector_native") or outcome.get("scientific_score_vector") or _masked_scientific_score_vector(),
        alias_surface=outcome.get("scientific_score_vector"),
    )
    editorial_score = outcome.get("editorial_score") or {
        "clarity": None,
        "novelty_explicitness": None,
        "structure_quality": None,
        "rhetorical_density": None,
        "total": None,
    }
    loss_band = outcome.get("loss_band")
    if loss_band is None:
        loss_band = _loss_band(total_loss)
    editorial_forecast = outcome.get("editorial_forecast")
    if editorial_forecast is None:
        editorial_forecast = _forecast_from_total_score(
            total_score,
            expected_band=expected_band,
            actual_band=actual_band,
            fatal_override=fatal_override,
        )

    author_recommendation = outcome.get("author_recommendation")
    if author_recommendation is None:
        author_recommendation = _author_recommendation_for_forecast(editorial_forecast, expected_decision)

    editorial_flags = outcome.get("editorial_plausibility_flags")
    if editorial_flags is None:
        editorial_flags = _editorial_plausibility_flags(
            case or {"ambiguity_class": "none"},
            list(outcome.get("error_classes", [])),
            recommendation_bias,
            recommendation_loss,
            fatal_override,
            decision_consistency_status,
        )
    editorial_first_pass = outcome.get("editorial_first_pass") or _empty_editorial_first_pass()
    editorial_anomalies = outcome.get("editorial_anomalies") or {
        "novelty_density": 0.0,
        "claim_to_evidence_ratio": 0.0,
        "rhetorical_intensity": 0.0,
        "triggered": [],
    }
    drift_counterfactual = outcome.get("drift_counterfactual")
    drift_counterfactuals = outcome.get("drift_counterfactuals", [])
    drift_counterfactual_stability = outcome.get("drift_counterfactual_stability")

    normalized = {
        "case_id": outcome["case_id"],
        "stratum": outcome.get("stratum", case.get("stratum")),
        "partition": outcome.get("partition", case.get("partition")),
        "category": outcome.get("category", case.get("category", outcome.get("partition", "unknown"))),
        "gate_behavior": outcome.get("gate_behavior", case.get("gate_behavior", "unknown")),
        "status": outcome.get("status"),
        "error_classes": list(outcome.get("error_classes", [])),
        "decision_recommendation": decision_recommendation,
        "scientific_recommendation": scientific_recommendation,
        "scientific_recommendation_band": scientific_recommendation_band,
        "decision_confidence": decision_confidence,
        "observed": outcome.get("observed", {}),
        "expected_decision": expected_decision,
        "scientific_score": scientific_score,
        **scientific_surface_bundle,
        "editorial_score": editorial_score,
        "scientific_loss": scientific_loss,
        "editorial_penalty": editorial_penalty,
        "total_loss": total_loss,
        "boundary_margin": boundary_margin,
        "decision_score": decision_score,
        "recommendation_bias": recommendation_bias,
        "recommendation_loss": recommendation_loss,
        "loss_band": loss_band,
        "total_score": total_score,
        "fatal_override": fatal_override,
        "decision_consistency_status": decision_consistency_status,
        "editorial_forecast": editorial_forecast,
        "author_recommendation": author_recommendation,
        "editorial_plausibility_flags": editorial_flags,
        "editorial_first_pass": editorial_first_pass,
        "editorial_anomalies": editorial_anomalies,
        "drift_counterfactual": drift_counterfactual,
        "drift_counterfactuals": drift_counterfactuals,
        "drift_counterfactual_stability": drift_counterfactual_stability,
    }
    for key in ("leakage_guard", "counterfactual_extended", "invariance_trace", "surface_contract"):
        if key in outcome:
            normalized[key] = outcome[key]
    return normalized


def _historical_case_outcomes(
    entry: dict[str, Any],
    manifest_case_index: dict[str, dict[str, Any]],
    governance: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _normalize_historical_case_outcome(outcome, manifest_case_index, governance)
        for outcome in entry.get("case_outcomes", [])
    ]


def _new_metric_bucket() -> dict[str, Any]:
    return {
        "case_count": 0,
        "fail_count": 0,
        "false_accept_count": 0,
        "recommendation_bias_total": 0,
        "recommendation_bias_cases": 0,
        "recommendation_loss_total": 0,
        "decision_score_total": 0,
        "total_score": 0,
        "editorial_forecast_counts": Counter(),
        "author_recommendation_counts": Counter(),
    }


def _finalize_metric_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    case_count = bucket["case_count"]
    bias_cases = bucket["recommendation_bias_cases"]
    return {
        "case_count": case_count,
        "fail_count": bucket["fail_count"],
        "fail_rate": _rounded(bucket["fail_count"] / case_count) if case_count else None,
        "false_accept_count": bucket["false_accept_count"],
        "false_accept_rate": _rounded(bucket["false_accept_count"] / case_count) if case_count else None,
        "mean_recommendation_bias": _rounded(bucket["recommendation_bias_total"] / bias_cases) if bias_cases else None,
        "mean_recommendation_loss": _rounded(bucket["recommendation_loss_total"] / case_count) if case_count else None,
        "decision_score_total": bucket["decision_score_total"],
        "total_score": bucket["total_score"],
        "editorial_forecast_counts": dict(sorted(bucket["editorial_forecast_counts"].items())),
        "author_recommendation_counts": dict(sorted(bucket["author_recommendation_counts"].items())),
    }


def _aggregate_group_metrics(case_results: list[dict[str, Any]], key_name: str) -> dict[str, Any]:
    buckets: dict[str, dict[str, Any]] = {}
    for case in case_results:
        if case.get("status") == "scaffold":
            continue
        key = case.get(key_name) or "unknown"
        bucket = buckets.setdefault(key, _new_metric_bucket())
        bucket["case_count"] += 1
        if case.get("status") != "pass":
            bucket["fail_count"] += 1
        if "false_accept_on_fatal_case" in case.get("error_classes", []):
            bucket["false_accept_count"] += 1
        if case.get("recommendation_bias") is not None:
            bucket["recommendation_bias_total"] += case["recommendation_bias"]
            bucket["recommendation_bias_cases"] += 1
        bucket["recommendation_loss_total"] += case.get("recommendation_loss") or 0
        bucket["decision_score_total"] += case.get("decision_score") or 0
        bucket["total_score"] += case.get("total_score") or 0
        if case.get("editorial_forecast"):
            bucket["editorial_forecast_counts"][case["editorial_forecast"]] += 1
        if case.get("author_recommendation"):
            bucket["author_recommendation_counts"][case["author_recommendation"]] += 1
    return {key: _finalize_metric_bucket(bucket) for key, bucket in sorted(buckets.items())}


def _baseline_group_summary(run_group_metrics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    keys = sorted({key for metrics in run_group_metrics for key in metrics})
    summary: dict[str, dict[str, Any]] = {}
    for key in keys:
        key_metrics = [metrics[key] for metrics in run_group_metrics if key in metrics]
        summary[key] = {
            "run_count": len(key_metrics),
            "false_accept_rate": _mean(
                [metric["false_accept_rate"] for metric in key_metrics if metric["false_accept_rate"] is not None]
            ),
            "mean_recommendation_bias": _mean(
                [
                    metric["mean_recommendation_bias"]
                    for metric in key_metrics
                    if metric["mean_recommendation_bias"] is not None
                ]
            ),
            "mean_recommendation_loss": _mean(
                [
                    metric["mean_recommendation_loss"]
                    for metric in key_metrics
                    if metric["mean_recommendation_loss"] is not None
                ]
            ),
        }
    return summary


def _apply_baseline_to_current_groups(current_groups: dict[str, Any], baseline_groups: dict[str, Any]) -> dict[str, Any]:
    enriched: dict[str, Any] = {}
    for key, metrics in current_groups.items():
        baseline = baseline_groups.get(key, {})
        baseline_false_accept_rate = baseline.get("false_accept_rate")
        baseline_recommendation_bias = baseline.get("mean_recommendation_bias")
        false_accept_rate = metrics.get("false_accept_rate")
        recommendation_bias = metrics.get("mean_recommendation_bias")
        enriched[key] = {
            **metrics,
            "baseline_false_accept_rate": baseline_false_accept_rate,
            "baseline_recommendation_bias": baseline_recommendation_bias,
            "false_accept_drift": (
                _rounded(false_accept_rate - baseline_false_accept_rate)
                if false_accept_rate is not None and baseline_false_accept_rate is not None
                else None
            ),
            "recommendation_bias_drift": (
                _rounded(recommendation_bias - baseline_recommendation_bias)
                if recommendation_bias is not None and baseline_recommendation_bias is not None
                else None
            ),
        }
    return enriched


def _drift_flags(
    diagnostics_by_group: dict[str, dict[str, Any]],
    *,
    false_accept_threshold: float,
    recommendation_bias_threshold: float,
) -> dict[str, list[dict[str, Any]]]:
    false_accept_flags: list[dict[str, Any]] = []
    recommendation_bias_flags: list[dict[str, Any]] = []

    for group_name, groups in diagnostics_by_group.items():
        for group_key, metrics in groups.items():
            false_accept_drift = metrics.get("false_accept_drift")
            if false_accept_drift is not None and false_accept_drift > false_accept_threshold:
                false_accept_flags.append(
                    {
                        "group_by": group_name,
                        "group_key": group_key,
                        "current": metrics["false_accept_rate"],
                        "baseline": metrics["baseline_false_accept_rate"],
                        "drift": false_accept_drift,
                        "threshold": false_accept_threshold,
                    }
                )
            recommendation_bias_drift = metrics.get("recommendation_bias_drift")
            if recommendation_bias_drift is not None and abs(recommendation_bias_drift) > recommendation_bias_threshold:
                recommendation_bias_flags.append(
                    {
                        "group_by": group_name,
                        "group_key": group_key,
                        "current": metrics["mean_recommendation_bias"],
                        "baseline": metrics["baseline_recommendation_bias"],
                        "drift": recommendation_bias_drift,
                        "threshold": recommendation_bias_threshold,
                        "direction": "more_permissive" if recommendation_bias_drift > 0 else "more_conservative",
                    }
                )

    return {
        "false_accept_rate": sorted(false_accept_flags, key=lambda item: (item["group_by"], item["group_key"])),
        "recommendation_bias": sorted(recommendation_bias_flags, key=lambda item: (item["group_by"], item["group_key"])),
    }


def _failed_case_ids_for_group(case_results: list[dict[str, Any]], key_name: str, key_value: str) -> list[str]:
    return sorted(
        case["case_id"]
        for case in case_results
        if case.get("status") != "scaffold"
        and (case.get(key_name) or "unknown") == key_value
        and (case.get("status") != "pass" or case.get("error_classes"))
    )


def _error_class_drift(
    case_results: list[dict[str, Any]],
    baseline_entries: list[dict[str, Any]],
    manifest_case_index: dict[str, dict[str, Any]],
    governance: dict[str, Any],
) -> list[dict[str, Any]]:
    historical_outcomes = [_historical_case_outcomes(entry, manifest_case_index, governance) for entry in baseline_entries]
    baseline_counters = [Counter(error for case in outcomes for error in case["error_classes"]) for outcomes in historical_outcomes]
    current_counter = Counter(error for case in case_results for error in case["error_classes"])
    error_classes = sorted(set(current_counter) | {error for counter in baseline_counters for error in counter})
    drift: list[dict[str, Any]] = []
    for error_class in error_classes:
        baseline_mean = _mean([counter.get(error_class, 0) for counter in baseline_counters]) or 0
        current_count = current_counter.get(error_class, 0)
        delta = _rounded(current_count - baseline_mean)
        if delta <= 0:
            continue
        drift.append(
            {
                "error_class": error_class,
                "current_count": current_count,
                "baseline_mean": baseline_mean,
                "delta": delta,
                "categories": sorted(
                    {
                        case["category"]
                        for case in case_results
                        if error_class in case.get("error_classes", [])
                    }
                ),
            }
        )
    return sorted(drift, key=lambda item: (-item["delta"], item["error_class"]))


def _normalize_git_path(path: str) -> str:
    return path.replace("\\", "/").strip()


def _changed_worktree_files() -> list[str]:
    status_code, status_output = git_output(["status", "--porcelain"], cwd=repo_root())
    if status_code != 0 or not status_output:
        return []
    paths: list[str] = []
    for line in status_output.splitlines():
        raw_path = line[3:].strip()
        if " -> " in raw_path:
            raw_path = raw_path.split(" -> ", 1)[1].strip()
        if raw_path:
            paths.append(_normalize_git_path(raw_path))
    return _dedupe_preserve_order(paths)


def _code_change_surface(path: str) -> str:
    normalized = _normalize_git_path(path)
    for prefix, surface in CODE_CHANGE_SURFACE_RULES:
        if normalized.startswith(prefix):
            return surface
    return "other"


def _recent_code_changes(prior_entry: dict[str, Any] | None, git_metadata: dict[str, Any]) -> dict[str, Any]:
    base_commit = prior_entry.get("commit_sha") if prior_entry else None
    head_commit = git_metadata.get("commit_sha")
    changed_files: list[str] = []
    if base_commit and head_commit and base_commit != head_commit:
        diff_code, diff_output = git_output(["diff", "--name-only", f"{base_commit}..{head_commit}"], cwd=repo_root())
        if diff_code == 0 and diff_output:
            changed_files.extend(_normalize_git_path(line) for line in diff_output.splitlines() if line.strip())
    if git_metadata.get("git_dirty"):
        changed_files.extend(_changed_worktree_files())
    files = _dedupe_preserve_order([path for path in changed_files if path])
    surfaces = Counter(_code_change_surface(path) for path in files)
    return {
        "available": bool(files),
        "base_commit": base_commit,
        "head_commit": head_commit,
        "files": files,
        "surface_counts": dict(sorted(surfaces.items())),
    }


def _dominant_code_change_surface(recent_code_changes: dict[str, Any]) -> str | None:
    if not recent_code_changes.get("available"):
        return None
    surface_counts = dict(recent_code_changes.get("surface_counts") or {})
    ranked = sorted(surface_counts.items(), key=lambda item: (-item[1], item[0]))
    for surface, _ in ranked:
        if surface != "test_only":
            return surface
    return ranked[0][0] if ranked else None


def _editorial_anomaly_diagnostics(case_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    case_ids_by_trigger: dict[str, list[str]] = {}
    for case in case_results:
        for trigger in case.get("editorial_anomalies", {}).get("triggered", []):
            case_ids_by_trigger.setdefault(trigger, []).append(case["case_id"])
    return [
        {
            "trigger": trigger,
            "count": len(case_ids),
            "case_ids": sorted(case_ids),
        }
        for trigger, case_ids in sorted(case_ids_by_trigger.items())
    ]


def _aggregate_drift_pressure(
    category_correlations: list[dict[str, Any]],
    error_class_correlations: list[dict[str, Any]],
) -> float:
    return float(
        _rounded(
            sum(item.get("score", 0) for item in category_correlations)
            + sum(item.get("delta", 0) for item in error_class_correlations)
        )
    )


def _simulate_removal(
    change_surface: str | None,
    *,
    category_correlations: list[dict[str, Any]],
    error_class_correlations: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_pressure = _aggregate_drift_pressure(category_correlations, error_class_correlations)
    if not change_surface:
        return {
            "available": False,
            "surface": None,
            "baseline_pressure": baseline_pressure,
            "pressure_without_surface": baseline_pressure,
            "delta": 0.0,
        }

    filtered_category = [
        item
        for item in category_correlations
        if item.get("category") != change_surface
    ]
    filtered_error: list[dict[str, Any]] = []
    for item in error_class_correlations:
        categories = [category for category in item.get("categories", []) if category != change_surface]
        if not categories:
            continue
        filtered_error.append({**item, "categories": categories})
    pressure_without_surface = _aggregate_drift_pressure(filtered_category, filtered_error)
    return {
        "available": True,
        "surface": change_surface,
        "baseline_pressure": baseline_pressure,
        "pressure_without_surface": pressure_without_surface,
        "delta": float(_rounded(baseline_pressure - pressure_without_surface)),
    }


def _build_drift_attribution(
    case_results: list[dict[str, Any]],
    baseline_entries: list[dict[str, Any]],
    manifest_case_index: dict[str, dict[str, Any]],
    diagnostics_by_group: dict[str, dict[str, Any]],
    prior_entry: dict[str, Any] | None,
    git_metadata: dict[str, Any],
    governance: dict[str, Any],
) -> dict[str, Any]:
    recent_code_changes = _recent_code_changes(prior_entry, git_metadata)
    editorial_anomalies = _editorial_anomaly_diagnostics(case_results)
    if not baseline_entries:
        return {
            "available": False,
            "category_correlations": [],
            "error_class_correlations": [],
            "editorial_anomalies": editorial_anomalies,
            "recent_code_changes": recent_code_changes,
            "likely_source": {
                "available": False,
                "category": None,
                "error_class": None,
                "code_change_surface": None,
                "confidence": "none",
            },
            "likely_cause": None,
            "intervention_delta": _simulate_removal(
                None,
                category_correlations=[],
                error_class_correlations=[],
            ),
        }

    false_accept_threshold = governance["drift_thresholds"]["false_accept_rate"] or 0
    recommendation_bias_threshold = governance["drift_thresholds"]["recommendation_bias"] or 0
    category_correlations: list[dict[str, Any]] = []
    for category, metrics in diagnostics_by_group["category"].items():
        false_accept_drift = metrics.get("false_accept_drift") or 0
        recommendation_bias_drift = metrics.get("recommendation_bias_drift") or 0
        normalized_score = 0.0
        if false_accept_threshold:
            normalized_score += abs(false_accept_drift) / false_accept_threshold
        if recommendation_bias_threshold:
            normalized_score += abs(recommendation_bias_drift) / recommendation_bias_threshold
        if normalized_score <= 0:
            continue
        category_correlations.append(
            {
                "category": category,
                "false_accept_drift": metrics.get("false_accept_drift"),
                "recommendation_bias_drift": metrics.get("recommendation_bias_drift"),
                "score": _rounded(normalized_score),
                "case_ids": _failed_case_ids_for_group(case_results, "category", category),
            }
        )
    category_correlations = sorted(category_correlations, key=lambda item: (-item["score"], item["category"]))

    error_class_correlations = _error_class_drift(case_results, baseline_entries, manifest_case_index, governance)
    dominant_surface = _dominant_code_change_surface(recent_code_changes)
    likely_category = category_correlations[0]["category"] if category_correlations else None
    if likely_category is None and error_class_correlations and error_class_correlations[0]["categories"]:
        likely_category = error_class_correlations[0]["categories"][0]
    evidence_axes = sum(
        1
        for present in (
            bool(category_correlations),
            bool(error_class_correlations),
            dominant_surface is not None,
        )
        if present
    )
    confidence = {0: "none", 1: "low", 2: "medium", 3: "high"}[evidence_axes]
    intervention_delta = (
        _simulate_removal(
            likely_category,
            category_correlations=category_correlations,
            error_class_correlations=error_class_correlations,
        )
        if governance["drift_intervention"]["enabled"]
        else {
            "available": False,
            "surface": likely_category,
            "baseline_pressure": _aggregate_drift_pressure(category_correlations, error_class_correlations),
            "pressure_without_surface": _aggregate_drift_pressure(category_correlations, error_class_correlations),
            "delta": 0.0,
        }
    )
    likely_source = {
        "available": bool(category_correlations or error_class_correlations or dominant_surface),
        "category": likely_category,
        "error_class": error_class_correlations[0]["error_class"] if error_class_correlations else None,
        "code_change_surface": dominant_surface,
        "confidence": confidence,
    }
    return {
        "available": bool(category_correlations or error_class_correlations or recent_code_changes["available"]),
        "category_correlations": category_correlations,
        "error_class_correlations": error_class_correlations,
        "editorial_anomalies": editorial_anomalies,
        "recent_code_changes": recent_code_changes,
        "likely_source": likely_source,
        "likely_cause": {
            "category": likely_source["category"],
            "error_class": likely_source["error_class"],
            "code_change_surface": likely_source["code_change_surface"],
        },
        "intervention_delta": intervention_delta,
    }


def _build_system_diagnostics(
    case_results: list[dict[str, Any]],
    baseline_entries: list[dict[str, Any]],
    manifest_case_index: dict[str, dict[str, Any]],
    *,
    prior_entry: dict[str, Any] | None,
    git_metadata: dict[str, Any],
    governance: dict[str, Any],
) -> dict[str, Any]:
    current_by_category = _aggregate_group_metrics(case_results, "category")
    current_by_stratum = _aggregate_group_metrics(case_results, "stratum")
    current_by_gate_behavior = _aggregate_group_metrics(case_results, "gate_behavior")

    if not baseline_entries:
        diagnostics_by_group = {
            "category": _apply_baseline_to_current_groups(current_by_category, {}),
            "stratum": _apply_baseline_to_current_groups(current_by_stratum, {}),
            "gate_behavior": _apply_baseline_to_current_groups(current_by_gate_behavior, {}),
        }
        return {
            "baseline": {"available": False, "window_size": 0, "run_count": 0},
            "by_category": diagnostics_by_group["category"],
            "by_stratum": diagnostics_by_group["stratum"],
            "by_gate_behavior": diagnostics_by_group["gate_behavior"],
            "drift_flags": {"false_accept_rate": [], "recommendation_bias": []},
            "drift_attribution": _build_drift_attribution(
                case_results,
                baseline_entries,
                manifest_case_index,
                diagnostics_by_group,
                prior_entry,
                git_metadata,
                governance,
            ),
        }

    historical_outcomes = [_historical_case_outcomes(entry, manifest_case_index, governance) for entry in baseline_entries]
    baseline_by_category = _baseline_group_summary([_aggregate_group_metrics(outcomes, "category") for outcomes in historical_outcomes])
    baseline_by_stratum = _baseline_group_summary([_aggregate_group_metrics(outcomes, "stratum") for outcomes in historical_outcomes])
    baseline_by_gate_behavior = _baseline_group_summary(
        [_aggregate_group_metrics(outcomes, "gate_behavior") for outcomes in historical_outcomes]
    )
    diagnostics_by_group = {
        "category": _apply_baseline_to_current_groups(current_by_category, baseline_by_category),
        "stratum": _apply_baseline_to_current_groups(current_by_stratum, baseline_by_stratum),
        "gate_behavior": _apply_baseline_to_current_groups(current_by_gate_behavior, baseline_by_gate_behavior),
    }
    drift_flags = _drift_flags(
        diagnostics_by_group,
        false_accept_threshold=governance["drift_thresholds"]["false_accept_rate"],
        recommendation_bias_threshold=governance["drift_thresholds"]["recommendation_bias"],
    )
    return {
        "baseline": {"available": True, "window_size": len(baseline_entries), "run_count": len(baseline_entries)},
        "by_category": diagnostics_by_group["category"],
        "by_stratum": diagnostics_by_group["stratum"],
        "by_gate_behavior": diagnostics_by_group["gate_behavior"],
        "drift_flags": drift_flags,
        "drift_attribution": _build_drift_attribution(
            case_results,
            baseline_entries,
            manifest_case_index,
            diagnostics_by_group,
            prior_entry,
            git_metadata,
            governance,
        ),
    }


def _build_regression_governor(
    case_results: list[dict[str, Any]],
    baseline_entries: list[dict[str, Any]],
    manifest_case_index: dict[str, dict[str, Any]],
    *,
    evaluation_mode: str,
    baseline_window: int,
    governance: dict[str, Any],
) -> dict[str, Any]:
    current_fatal_error_count = sum(1 for case in case_results if FATAL_OVERRIDE_ERROR_CLASSES.intersection(case["error_classes"]))
    current_core_gold_failure_classes = sorted(
        {
            error_class
            for case in case_results
            if case["case_state"] == "active" and case["stratum"] == "core_gold"
            for error_class in case["error_classes"]
        }
    )

    if not baseline_entries:
        return {
            "available": False,
            "evaluation_mode": evaluation_mode,
            "window_size": baseline_window,
            "run_count": 0,
            "fatal_error_count": {
                "current": current_fatal_error_count,
                "baseline_last": None,
                "baseline_mean": None,
                "baseline_max": None,
            },
            "core_gold_failure_classes": {"current": current_core_gold_failure_classes, "baseline": [], "new": []},
        }

    historical_outcomes = [_historical_case_outcomes(entry, manifest_case_index, governance) for entry in baseline_entries]
    historical_fatal_counts = [
        sum(1 for case in outcomes if FATAL_OVERRIDE_ERROR_CLASSES.intersection(case["error_classes"])) for outcomes in historical_outcomes
    ]
    baseline_core_gold_failure_classes = sorted(
        {
            error_class
            for outcomes in historical_outcomes
            for case in outcomes
            if case["stratum"] == "core_gold"
            for error_class in case["error_classes"]
        }
    )
    return {
        "available": True,
        "evaluation_mode": evaluation_mode,
        "window_size": baseline_window,
        "run_count": len(baseline_entries),
        "fatal_error_count": {
            "current": current_fatal_error_count,
            "baseline_last": historical_fatal_counts[-1] if historical_fatal_counts else None,
            "baseline_mean": _mean(historical_fatal_counts),
            "baseline_max": max(historical_fatal_counts) if historical_fatal_counts else None,
        },
        "core_gold_failure_classes": {
            "current": current_core_gold_failure_classes,
            "baseline": baseline_core_gold_failure_classes,
            "new": sorted(set(current_core_gold_failure_classes) - set(baseline_core_gold_failure_classes)),
        },
    }


def _leakage_resilience_score(case_results: list[dict[str, Any]], governance: dict[str, Any]) -> float:
    if not governance["leakage_guard"]["enabled"]:
        return 0.0
    budget_cap = max(1, int(governance["leakage_guard"].get("budget_cap", 1)))
    scores: list[float] = []
    for case in case_results:
        if case["case_state"] != "active":
            continue
        layer = case.get("leakage_guard")
        if not layer:
            continue
        epsilon_budget = float(layer.get("epsilon_budget") or 0.0)
        noise_scale = float(layer.get("noise_scale") or 0.0)
        budget_used = min(int(layer.get("budget_used") or 0), budget_cap)
        budget_pressure = min(budget_used / float(budget_cap), 1.0)
        if epsilon_budget > 0:
            noise_cover = min(noise_scale / epsilon_budget, 1.0)
        else:
            noise_cover = 1.0 if int(layer.get("query_budget") or 0) == 0 else 0.0
        scores.append(float(_rounded((noise_cover * 0.6) + (budget_pressure * 0.4))))
    return float(_mean(scores) or 0.0)


def _attribution_stability_score(case_results: list[dict[str, Any]], governance: dict[str, Any]) -> float:
    if not governance["attribution_identifiability"]["enabled"]:
        return 0.0
    scores: list[float] = []
    identifiability_weight = {
        "unique": 1.0,
        "correlated": 0.5,
        "degenerate": 0.0,
    }
    for case in case_results:
        if case["case_state"] != "active":
            continue
        extended = case.get("counterfactual_extended")
        if not extended:
            continue
        stability = float(extended.get("stability") or 0.0)
        status = str(extended.get("identifiability_status") or extended.get("identifiability") or "degenerate")
        scores.append(float(_rounded((stability + identifiability_weight.get(status, 0.0)) / 2.0)))
    return float(_mean(scores) or 0.0)


def _case_semantic_change_from_prior(case: dict[str, Any], previous: dict[str, Any] | None) -> bool:
    if previous is None:
        return False
    semantic_fields = (
        "observed",
        "error_classes",
        "scientific_score",
        "scientific_score_vector",
        "scientific_score_vector_legacy",
        "scientific_score_vector_native",
        "editorial_score",
        "decision_score",
        "recommendation_loss",
        "scientific_loss",
        "editorial_penalty",
        "total_loss",
        "boundary_margin",
        "decision_consistency_status",
        "fatal_override",
    )
    return any(previous.get(field) != case.get(field) for field in semantic_fields)


def _build_invariance_metrics(case_results: list[dict[str, Any]], governance: dict[str, Any], prior_entry: dict[str, Any] | None) -> tuple[float, float]:
    if not governance["invariance_trace"]["enabled"]:
        return (0.0, 0.0)
    if prior_entry is None:
        return (1.0, 1.0)
    previous_cases = _case_outcome_index(prior_entry.get("case_outcomes", []))
    true_positive = false_positive = false_negative = 0
    for case in case_results:
        if case["case_state"] != "active":
            continue
        trace = case.get("invariance_trace")
        if not trace:
            continue
        previous = previous_cases.get(case["case_id"])
        if previous is None:
            continue
        public_outputs_same = all(
            previous.get(field) == case.get(field)
            for field in ("decision_recommendation", "loss_band", "status")
        )
        expected_positive = public_outputs_same and _case_semantic_change_from_prior(case, previous)
        predicted_positive = bool(trace.get("drift_detected"))
        if predicted_positive and expected_positive:
            true_positive += 1
        elif predicted_positive and not expected_positive:
            false_positive += 1
        elif expected_positive and not predicted_positive:
            false_negative += 1
    precision = 1.0 if (true_positive + false_positive) == 0 else _ratio(true_positive, true_positive + false_positive)
    recall = 1.0 if (true_positive + false_negative) == 0 else _ratio(true_positive, true_positive + false_negative)
    return (precision, recall)


def _surface_contract_violations(case_results: list[dict[str, Any]], governance: dict[str, Any]) -> int:
    if not governance["surface_contract"]["enabled"]:
        return 0
    return sum(
        1
        for case in case_results
        if case["case_state"] == "active" and bool((case.get("surface_contract") or {}).get("mixed_usage_violation"))
    )


def _build_governance_report(
    case_results: list[dict[str, Any]],
    governance: dict[str, Any],
    prior_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    invariance_precision, invariance_recall = _build_invariance_metrics(case_results, governance, prior_entry)
    return governance_router.build_governance_report(
        case_results,
        governance,
        leakage_resilience_score=_leakage_resilience_score(case_results, governance),
        attribution_stability_score=_attribution_stability_score(case_results, governance),
        invariance_precision=invariance_precision,
        invariance_recall=invariance_recall,
        surface_contract_violations=_surface_contract_violations(case_results, governance),
    )


def _new_gate_failure(
    gate_id: str,
    description: str,
    case_ids: list[str],
    *,
    current_count: int | None = None,
    previous_count: int | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "gate_id": gate_id,
        "description": description,
        "case_ids": sorted(case_ids),
    }
    if current_count is not None:
        payload["current_count"] = current_count
    if previous_count is not None:
        payload["previous_count"] = previous_count
    if details:
        payload["details"] = details
    return payload


def _evaluate_gates(
    case_results: list[dict[str, Any]],
    case_deltas: dict[str, Any],
    prior_entry: dict[str, Any] | None,
    regression_governor: dict[str, Any],
) -> dict[str, Any]:
    absolute_failures: list[dict[str, Any]] = []
    delta_failures: list[dict[str, Any]] = []
    rolling_failures: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    core_gold_failures = [case["case_id"] for case in case_results if case["case_state"] == "active" and case["stratum"] == "core_gold" and case["status"] != "pass"]
    if core_gold_failures:
        absolute_failures.append(
            _new_gate_failure(
                "core_gold_exact_regression",
                "Core gold cases must satisfy exact expectations and required anchor paths.",
                core_gold_failures,
            )
        )

    fatal_gate_case_ids = [case["case_id"] for case in case_results if FATAL_ERROR_CLASSES.intersection(case["error_classes"])]
    if fatal_gate_case_ids:
        absolute_failures.append(
            _new_gate_failure(
                "fatal_gate_miss_present",
                "Fatal-gate misses are absolute failures even without a prior comparator.",
                fatal_gate_case_ids,
                current_count=len(fatal_gate_case_ids),
                previous_count=0,
            )
        )

    if prior_entry is None:
        skipped.extend(
            [
                {
                    "gate_id": "increase_in_fatal_gate_misses",
                    "reason": "No prior ledger entry is available for delta comparison.",
                },
                {
                    "gate_id": "new_null_or_replication_wrong_recommendation",
                    "reason": "No prior ledger entry is available for delta comparison.",
                },
                {
                    "gate_id": "new_specialist_false_reject",
                    "reason": "No prior ledger entry is available for delta comparison.",
                },
                {
                    "gate_id": "new_core_missing_required_evidence_anchor",
                    "reason": "No prior ledger entry is available for delta comparison.",
                },
            ]
        )
    else:
        previous_cases = _case_outcome_index(prior_entry.get("case_outcomes", []))
        previous_fatal_count = sum(1 for case in prior_entry.get("case_outcomes", []) if FATAL_ERROR_CLASSES.intersection(case.get("error_classes", [])))
        current_fatal_count = len(fatal_gate_case_ids)
        if current_fatal_count > previous_fatal_count:
            delta_failures.append(
                _new_gate_failure(
                    "increase_in_fatal_gate_misses",
                    "Fatal-gate miss count increased versus the previous recorded run.",
                    fatal_gate_case_ids,
                    current_count=current_fatal_count,
                    previous_count=previous_fatal_count,
                )
            )

        null_replication_case_ids = []
        specialist_false_reject_case_ids = []
        missing_anchor_case_ids = []
        for case in case_results:
            previous = previous_cases.get(case["case_id"])
            previous_error_classes = set(previous.get("error_classes", [])) if previous else set()
            current_error_classes = set(case["error_classes"])
            if "null_or_replication" in case["tags"] and "wrong_recommendation" in current_error_classes and "wrong_recommendation" not in previous_error_classes:
                null_replication_case_ids.append(case["case_id"])
            if "false_desk_reject_on_viable_specialist_case" in current_error_classes and "false_desk_reject_on_viable_specialist_case" not in previous_error_classes:
                specialist_false_reject_case_ids.append(case["case_id"])
            if case["stratum"] == "core_gold" and previous and previous.get("status") == "pass":
                if "missing_required_evidence_anchor" in current_error_classes and "missing_required_evidence_anchor" not in previous_error_classes:
                    missing_anchor_case_ids.append(case["case_id"])

        if null_replication_case_ids:
            delta_failures.append(
                _new_gate_failure(
                    "new_null_or_replication_wrong_recommendation",
                    "Null or replication cases may not develop new recommendation regressions.",
                    null_replication_case_ids,
                )
            )
        if specialist_false_reject_case_ids:
            delta_failures.append(
                _new_gate_failure(
                    "new_specialist_false_reject",
                    "Specialist-viable cases may not develop new desk-reject behavior.",
                    specialist_false_reject_case_ids,
                )
            )
        if missing_anchor_case_ids:
            delta_failures.append(
                _new_gate_failure(
                    "new_core_missing_required_evidence_anchor",
                    "Previously passing core cases may not lose required evidence-anchor paths.",
                    missing_anchor_case_ids,
                )
            )

    if not regression_governor["available"]:
        skipped.extend(
            [
                {
                    "gate_id": "fatal_error_count_above_baseline",
                    "reason": "Rolling ledger baseline is unavailable for fatal error comparison.",
                },
                {
                    "gate_id": "new_core_gold_failure_class",
                    "reason": "Rolling ledger baseline is unavailable for core_gold failure-class comparison.",
                },
            ]
        )
    else:
        baseline_max = regression_governor["fatal_error_count"]["baseline_max"] or 0
        current_fatal_error_count = regression_governor["fatal_error_count"]["current"]
        fatal_override_case_ids = [
            case["case_id"] for case in case_results if FATAL_OVERRIDE_ERROR_CLASSES.intersection(case["error_classes"])
        ]
        if current_fatal_error_count > baseline_max:
            rolling_failures.append(
                _new_gate_failure(
                    "fatal_error_count_above_baseline",
                    "Current fatal error count exceeds the rolling baseline envelope.",
                    fatal_override_case_ids,
                    current_count=current_fatal_error_count,
                    previous_count=baseline_max,
                )
            )

        new_core_gold_failure_classes = regression_governor["core_gold_failure_classes"]["new"]
        if new_core_gold_failure_classes:
            impacted_case_ids = [
                case["case_id"]
                for case in case_results
                if case["stratum"] == "core_gold"
                and set(case["error_classes"]).intersection(new_core_gold_failure_classes)
            ]
            rolling_failures.append(
                _new_gate_failure(
                    "new_core_gold_failure_class",
                    "A new failure class appeared in core_gold relative to the rolling ledger baseline.",
                    impacted_case_ids,
                    details={"new_failure_classes": new_core_gold_failure_classes},
                )
            )

    return {
        "status": "fail" if absolute_failures or delta_failures or rolling_failures else "pass",
        "absolute_failures": absolute_failures,
        "delta_failures": delta_failures,
        "rolling_failures": rolling_failures,
        "skipped": skipped,
        "prior_run_available": prior_entry is not None,
        "changed_case_count_vs_prior": case_deltas["changed_case_count"],
    }


def _loss_band_ordinal(loss_band: str | None) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(loss_band, 3)


def _editorial_invariant_rank_key(case: dict[str, Any]) -> tuple[int, int, float, str]:
    return (
        _recommendation_ordinal(case.get("scientific_recommendation"), case.get("scientific_recommendation_band")) or 999,
        _loss_band_ordinal(_loss_band(case.get("scientific_loss"))),
        float(case.get("scientific_loss") or 0.0),
        case["case_id"],
    )


def _public_rank_key(case: dict[str, Any]) -> tuple[int, int, float, str]:
    return (
        _recommendation_ordinal(case.get("decision_recommendation"), _recommendation_band(case.get("decision_recommendation"))) or 999,
        _loss_band_ordinal(case.get("loss_band")),
        float(case.get("scientific_loss") or 0.0),
        case["case_id"],
    )


def _enforce_editorial_weight_invariance(case_results: list[dict[str, Any]], governance: dict[str, Any]) -> None:
    if float(governance.get("editorial_penalty_weight") or 0.0) <= 0:
        return

    active_cases = [case for case in case_results if case["case_state"] == "active"]
    if not active_cases:
        return

    # Editorial weight is benchmark-only. If it changes decision classes,
    # calibration bins, or ranking order, APR would be leaking venue-style
    # preference back into a surface that is meant to remain science-first.
    decision_before = {case["case_id"]: case.get("scientific_recommendation") for case in active_cases}
    decision_after = {case["case_id"]: case.get("decision_recommendation") for case in active_cases}
    if decision_before != decision_after:
        raise EditorialDriftError("editorial weighting changed public decision classes")

    calibration_before = {case["case_id"]: _loss_band(case.get("scientific_loss")) for case in active_cases}
    calibration_after = {case["case_id"]: case.get("loss_band") for case in active_cases}
    if calibration_before != calibration_after:
        raise EditorialDriftError("editorial weighting changed calibration bin assignment")

    ranking_before = [case["case_id"] for case in sorted(active_cases, key=_editorial_invariant_rank_key)]
    ranking_after = [case["case_id"] for case in sorted(active_cases, key=_public_rank_key)]
    if ranking_before != ranking_after:
        raise EditorialDriftError("editorial weighting changed public ranking order")


def _build_calibration_export(case_results: list[dict[str, Any]], governance: dict[str, Any]) -> dict[str, Any]:
    active_cases = [case for case in case_results if case["case_state"] == "active" and case.get("decision_score") is not None]
    extended = governance["calibration"]["extended_export"]
    # Calibration export is an analysis surface for comparable runs and external
    # audit, not an alternate acceptance path for manuscript decisions.
    return {
        "available": True,
        "masked": False,
        "schema_version": "1.0",
        "case_count": len(active_cases),
        "cases": [
            (
                {
                    "case_id": case["case_id"],
                    "decision_score": case["decision_score"],
                    "outcome": case["status"],
                    "scientific_score_vector": case["scientific_score"],
                    "scientific_score_vector_legacy": case["scientific_score_vector_legacy"],
                    "scientific_score_vector_native": case["scientific_score_vector_native"],
                    "editorial_score_vector": case["editorial_score"],
                    "decision": case["scientific_recommendation"],
                    "confidence": case["decision_confidence"],
                    "loss": case["scientific_loss"],
                    "boundary_margin": case["boundary_margin"],
                    "calibration_extended": {
                        **governance_surface_contract.build_scientific_surface_bundle(
                            legacy_surface=case["scientific_score_vector_legacy"],
                            native_surface=case["scientific_score_vector_native"],
                            alias_surface=case["scientific_score_vector"],
                            alias_key="scientific_vector",
                            legacy_key="scientific_vector_legacy",
                            native_key="scientific_vector_native",
                        ),
                        "editorial_vector": case["editorial_score"],
                        "decision_margin": case["boundary_margin"],
                        "loss_band": case.get("loss_band"),
                        "drift_features": _case_drift_features(case),
                        "counterfactuals": case.get("drift_counterfactuals", _case_counterfactuals(case, governance)),
                        "drift_counterfactual": case.get("drift_counterfactuals", _case_counterfactuals(case, governance)),
                        "drift_counterfactual_stability": case.get("drift_counterfactual_stability"),
                        **governance_router.export_governance_fields(case),
                    },
                }
                if extended
                else {
                    "case_id": case["case_id"],
                    "decision_score": case["decision_score"],
                    "outcome": case["status"],
                }
            )
            for case in active_cases
        ],
    }


def _build_public_holdout_summary(
    summary: dict[str, Any],
    *,
    manifest_sha256: str,
    governance: dict[str, Any],
) -> dict[str, Any]:
    if summary["evaluation_mode"] != HOLDOUT_BLIND_EVALUATION_MODE:
        return summary

    # Holdout summaries are redacted after full internal evaluation so APR can
    # publish governance evidence without revealing enough case-level signal to
    # tune against hidden expectations.
    redacted_cases = [_redact_holdout_result(case) for case in summary["cases"]]
    if not governance["holdout_noise"]["enabled"]:
        masked_result_type_counts = Counter(case["status"] for case in redacted_cases)
        return {
            **summary,
            "holdout": {
                **summary["holdout"],
                "noise_injected": False,
                "blindness_level": governance["holdout_blindness"]["level"],
            },
            "passed": masked_result_type_counts.get("pass", 0),
            "failed": masked_result_type_counts.get("fail", 0),
            "result_type_counts": dict(sorted(masked_result_type_counts.items())),
            "cases": redacted_cases,
        }

    masked_cases = [_obfuscate_holdout_result(case, manifest_sha256=manifest_sha256, governance=governance) for case in summary["cases"]]
    masked_error_total = sum(len(case["error_classes"]) for case in masked_cases)
    masked_result_type_counts = Counter(case["status"] for case in masked_cases)
    return {
        **summary,
        "holdout": {
            **summary["holdout"],
            "noise_injected": True,
            "blindness_level": governance["holdout_blindness"]["level"],
        },
        "passed": masked_result_type_counts.get("pass", 0),
        "failed": masked_result_type_counts.get("fail", 0),
        "result_type_counts": dict(sorted(masked_result_type_counts.items())),
        "cases": masked_cases,
        "error_class_counts": {HOLDOUT_MASKED_ERROR_CLASS: masked_error_total} if masked_error_total else {},
        "case_deltas": {
            "available": False,
            "prior_generated_at_utc": summary["case_deltas"]["prior_generated_at_utc"],
            "changed_case_count": 0,
            "unchanged_case_count": len(masked_cases),
            "cases": [],
        },
        "recommendation_changes_vs_prior": {
            "available": False,
            "total_changed_cases": 0,
            "by_transition": {},
        },
        "calibration_export": {
            "available": False,
            "masked": True,
            "schema_version": summary["calibration_export"]["schema_version"],
            "case_count": summary["calibration_export"]["case_count"],
            "cases": [],
        },
    }


def _build_ledger_entry(
    summary: dict[str, Any],
    *,
    manifest_file: Path,
    notes: str | None,
    operator: str | None,
) -> dict[str, Any]:
    git_metadata = _current_git_metadata()
    # Ledger entries are append-only run records. New additive fields belong
    # here so prior rows remain valid comparators for regression governance.
    return {
        "generated_at_utc": summary["generated_at_utc"],
        "commit_sha": git_metadata["commit_sha"],
        "git_dirty": git_metadata["git_dirty"],
        "operator": operator or _current_operator_identifier(),
        "notes": notes or "",
        "contract_version": summary["contract_version"],
        "policy_layer_version": summary["policy_layer_version"],
        "manifest_version": summary["manifest_version"],
        "manifest_path": str(manifest_file.resolve()),
        "manifest_sha256": summary["manifest_sha256"],
        "contract_manifest_sha256": summary["contract_manifest_sha256"],
        "policy_layer_sha256": summary["policy_layer_sha256"],
        "canonical_schema_sha256": summary["canonical_schema_sha256"],
        "runtime_identity": summary["runtime_identity"],
        "repo_state": summary["repo_state"],
        "evaluation_mode": summary["evaluation_mode"],
        "holdout": summary["holdout"],
        "result_type_counts": summary["result_type_counts"],
        "error_class_counts": summary["error_class_counts"],
        "governance": summary["governance"],
        "decision_algebra": summary["decision_algebra"],
        "decision_consistency": summary["decision_consistency"],
        "scientific_score_summary": summary["scientific_score_summary"],
        "editorial_score_summary": summary["editorial_score_summary"],
        "editorial_first_pass_score": summary["editorial_first_pass_score"],
        "editorial_plausibility_flags": summary["editorial_plausibility_flags"],
        "editorial_anomalies": summary["editorial_anomalies"],
        "governance_report": summary["governance_report"],
        "calibration_export": summary["calibration_export"],
        "system_diagnostics": summary["system_diagnostics"],
        "regression_governor": summary["regression_governor"],
        "case_deltas": summary["case_deltas"],
        "recommendation_changes_vs_prior": summary["recommendation_changes_vs_prior"],
        "gates": summary["gates"],
        "prior_generated_at_utc": summary["case_deltas"]["prior_generated_at_utc"],
        "case_outcomes": [
            {
                "case_id": case["case_id"],
                "stratum": case["stratum"],
                "partition": case["partition"],
                "category": case["category"],
                "gate_behavior": case["gate_behavior"],
                "status": case["status"],
                "error_classes": case["error_classes"],
                "decision_recommendation": case["decision_recommendation"],
                "scientific_recommendation": case["scientific_recommendation"],
                "scientific_recommendation_band": case["scientific_recommendation_band"],
                "decision_confidence": case["decision_confidence"],
                "observed": case["observed"],
                "expected_decision": case["expected_decision"],
                "scientific_score": case["scientific_score"],
                "scientific_score_vector": case["scientific_score_vector"],
                "scientific_score_vector_legacy": case["scientific_score_vector_legacy"],
                "scientific_score_vector_native": case["scientific_score_vector_native"],
                "editorial_score": case["editorial_score"],
                "scientific_loss": case["scientific_loss"],
                "editorial_penalty": case["editorial_penalty"],
                "total_loss": case["total_loss"],
                "boundary_margin": case["boundary_margin"],
                "decision_consistency_status": case["decision_consistency_status"],
                "decision_score": case["decision_score"],
                "recommendation_bias": case["recommendation_bias"],
                "recommendation_loss": case["recommendation_loss"],
                "loss_band": case["loss_band"],
                "total_score": case["total_score"],
                "editorial_forecast": case["editorial_forecast"],
                "author_recommendation": case["author_recommendation"],
                "fatal_override": case["fatal_override"],
                "drift_counterfactual": case["drift_counterfactual"],
                "drift_counterfactuals": case["drift_counterfactuals"],
                "drift_counterfactual_stability": case["drift_counterfactual_stability"],
                "editorial_plausibility_flags": case["editorial_plausibility_flags"],
                "editorial_first_pass": case["editorial_first_pass"],
                "editorial_anomalies": case["editorial_anomalies"],
                **governance_router.export_governance_fields(case),
            }
            for case in summary["cases"]
            if case["case_state"] == "active"
        ],
    }


def build_goldset_ledger_entry(
    summary: dict[str, Any],
    *,
    manifest_path: str | Path,
    notes: str | None = None,
    operator: str | None = None,
) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    return _build_ledger_entry(
        summary,
        manifest_file=manifest_file,
        notes=notes,
        operator=operator,
    )


def _append_ledger_entry(ledger_path: Path, entry: dict[str, Any]) -> None:
    # Re-validate at append time so ledger growth cannot accumulate records that
    # were valid in memory but invalid for the durable calibration history.
    schema = load_goldset_ledger_entry_schema()
    Draft202012Validator.check_schema(schema)
    _validate_governance_report_namespace(entry.get("governance_report") or {})
    _validate_error_class_namespace(list((entry.get("error_class_counts") or {}).keys()))
    for outcome in entry.get("case_outcomes", []):
        _validate_error_class_namespace(outcome.get("error_classes"))
        _validate_case_governance_namespace(outcome)
    validate(instance=entry, schema=schema)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl_atomic(ledger_path, entry)


def append_goldset_ledger_entry(ledger_path: str | Path, entry: dict[str, Any]) -> None:
    _append_ledger_entry(Path(ledger_path), entry)


def _validate_summary(summary: dict[str, Any]) -> None:
    schema = load_goldset_summary_schema()
    Draft202012Validator.check_schema(schema)
    _validate_governance_report_namespace(summary.get("governance_report") or {})
    _validate_error_class_namespace(list((summary.get("error_class_counts") or {}).keys()))
    for case in summary.get("cases", []):
        _validate_error_class_namespace(case.get("error_classes"))
        _validate_case_governance_namespace(case)
    for calibration_case in (summary.get("calibration_export") or {}).get("cases", []):
        _validate_case_governance_namespace((calibration_case.get("calibration_extended") or {}))
    validate(instance=summary, schema=schema)


def run_goldset_manifest(
    manifest_path: str | Path | None = None,
    *,
    extra_pack_paths: list[str] | None = None,
    ledger_path: str | Path | None = None,
    notes: str | None = None,
    operator: str | None = None,
    holdout_eval: bool = False,
    ledger_baseline_window: int | None = None,
    regression_threshold: float | None = None,
    fatal_weight_scale: float | None = None,
    holdout_noise: bool | None = None,
    loss_quantization: bool | None = None,
    enable_editorial_weight: bool | None = None,
    separate_planes: bool | None = None,
    export_calibration_extended: bool | None = None,
    holdout_blindness_level: str | None = None,
    drift_intervention: bool | None = None,
    drift_counterfactuals: bool | None = None,
    leakage_guard: bool | None = None,
    attribution_identifiability: bool | None = None,
    invariance_trace: bool | None = None,
    strict_surface_contract: bool | None = None,
) -> dict[str, Any]:
    # Development and blind-holdout modes share evaluation machinery but not the
    # same public exposure rules. The mode split exists to prevent benchmark
    # leakage, not to create a second decision policy.
    if manifest_path:
        manifest_file = Path(manifest_path)
    else:
        manifest_file = _default_holdout_manifest() if holdout_eval else _default_manifest()
    manifest = load_goldset_manifest(manifest_file)
    manifest_sha256 = _manifest_sha256(manifest_file)
    contract_fingerprints = _runtime_contract_fingerprints()
    runtime_identity = _runtime_identity()
    governance = _resolve_goldset_governance_config(
        baseline_window=ledger_baseline_window,
        regression_threshold=regression_threshold,
        fatal_weight_scale=fatal_weight_scale,
        holdout_noise=holdout_noise,
        holdout_blindness_level=holdout_blindness_level,
        loss_quantization=loss_quantization,
        enable_editorial_weight=enable_editorial_weight,
        separate_planes=separate_planes,
        export_calibration_extended=export_calibration_extended,
        drift_intervention=drift_intervention,
        drift_counterfactuals=drift_counterfactuals,
        leakage_guard=leakage_guard,
        attribution_identifiability=attribution_identifiability,
        invariance_trace=invariance_trace,
        strict_surface_contract=strict_surface_contract,
    )
    git_metadata = _current_git_metadata()
    manifest_case_index = _case_outcome_index(manifest["cases"])
    case_root = (manifest_file.parent / manifest["case_root"]).resolve()
    evaluation_mode = HOLDOUT_BLIND_EVALUATION_MODE if holdout_eval else DEVELOPMENT_EVALUATION_MODE
    selected_cases, holdout = _select_cases_for_run(manifest, holdout_eval=holdout_eval)

    ledger_entries = _load_ledger_entries(Path(ledger_path) if ledger_path else None)
    comparable_entries = [entry for entry in ledger_entries if _ledger_entry_evaluation_mode(entry) == evaluation_mode]
    case_histories = _case_histories(comparable_entries)
    prior_entry = comparable_entries[-1] if comparable_entries else None
    baseline_window = governance["baseline_window"]
    baseline_entries = comparable_entries[-baseline_window:] if comparable_entries and baseline_window > 0 else []

    case_results: list[dict[str, Any]] = []
    result_type_counts: Counter[str] = Counter()
    stratum_summary = {stratum["name"]: _new_stats() for stratum in manifest["strata"]}
    partition_summary: dict[str, dict[str, int]] = {}

    for case in selected_cases:
        result = _evaluate_case(
            case,
            case_root=case_root,
            manifest_file=manifest_file,
            extra_pack_paths=extra_pack_paths,
            evaluation_mode=evaluation_mode,
            governance=governance,
            case_history=case_histories.get(case["case_id"], []),
        )
        case_results.append(result)

        status = result["status"]
        result_type_counts[status] += 1
        partition_summary.setdefault(result["partition"], _new_stats())

        target_stats = stratum_summary[result["stratum"]]
        partition_stats = partition_summary[result["partition"]]
        if status == "scaffold":
            target_stats["scaffold"] += 1
            partition_stats["scaffold"] += 1
            continue

        target_stats["total"] += 1
        partition_stats["total"] += 1
        if status == "pass":
            target_stats["passed"] += 1
            partition_stats["passed"] += 1
        else:
            target_stats["failed"] += 1
            partition_stats["failed"] += 1

    passed = result_type_counts.get("pass", 0)
    failed = result_type_counts.get("fail", 0)
    scaffold = result_type_counts.get("scaffold", 0)
    _enforce_editorial_weight_invariance(case_results, governance)
    case_deltas = _build_case_deltas(case_results, prior_entry)
    recommendation_changes = _aggregate_recommendation_changes(case_deltas)
    decision_algebra = _build_decision_algebra_summary(case_results, governance)
    decision_consistency = _build_decision_consistency_summary(case_results)
    scientific_score_summary = _build_score_vector_summary(case_results, "scientific_score")
    editorial_score_summary = _build_score_vector_summary(case_results, "editorial_score")
    editorial_first_pass_score = _build_editorial_first_pass_summary(case_results)
    editorial_plausibility_flags = _count_editorial_plausibility_flags(case_results)
    editorial_anomalies = _count_editorial_anomaly_triggers(case_results)
    system_diagnostics = _build_system_diagnostics(
        case_results,
        baseline_entries,
        manifest_case_index,
        prior_entry=prior_entry,
        git_metadata=git_metadata,
        governance=governance,
    )
    regression_governor = _build_regression_governor(
        case_results,
        baseline_entries,
        manifest_case_index,
        evaluation_mode=evaluation_mode,
        baseline_window=baseline_window,
        governance=governance,
    )
    governance_report = _build_governance_report(case_results, governance, prior_entry)
    gates = _evaluate_gates(case_results, case_deltas, prior_entry, regression_governor)
    summary = {
        "manifest_version": manifest["manifest_version"],
        "contract_version": manifest["contract_version"],
        "policy_layer_version": contract_fingerprints["policy_layer_version"],
        "manifest_path": str(manifest_file.resolve()),
        "manifest_sha256": manifest_sha256,
        "contract_manifest_sha256": contract_fingerprints["contract_manifest_sha256"],
        "policy_layer_sha256": contract_fingerprints["policy_layer_sha256"],
        "canonical_schema_sha256": contract_fingerprints["canonical_schema_sha256"],
        "runtime_identity": runtime_identity,
        "repo_state": {
            "commit_sha": git_metadata["commit_sha"],
            "git_dirty": git_metadata["git_dirty"],
        },
        "generated_at_utc": utc_now_iso(),
        "evaluation_mode": evaluation_mode,
        "holdout": holdout,
        "total_cases": passed + failed,
        "passed": passed,
        "failed": failed,
        "scaffold_cases": scaffold,
        "result_type_counts": dict(sorted(result_type_counts.items())),
        "strata": stratum_summary,
        "partitions": partition_summary,
        "error_class_counts": _count_error_classes(case_results),
        "governance": governance,
        "decision_algebra": decision_algebra,
        "decision_consistency": decision_consistency,
        "scientific_score_summary": scientific_score_summary,
        "editorial_score_summary": editorial_score_summary,
        "editorial_first_pass_score": editorial_first_pass_score,
        "editorial_plausibility_flags": editorial_plausibility_flags,
        "editorial_anomalies": editorial_anomalies,
        "governance_report": governance_report,
        "cases": case_results,
        "calibration_export": _build_calibration_export(case_results, governance),
        "system_diagnostics": system_diagnostics,
        "regression_governor": regression_governor,
        "case_deltas": case_deltas,
        "recommendation_changes_vs_prior": recommendation_changes,
        "gates": gates,
        "prior_run": {
            "available": prior_entry is not None,
            "generated_at_utc": prior_entry["generated_at_utc"] if prior_entry else None,
            "manifest_sha256": prior_entry["manifest_sha256"] if prior_entry else None,
            "contract_version": prior_entry["contract_version"] if prior_entry else None,
        },
        "calibration_ledger": {
            "path": str(Path(ledger_path).resolve()) if ledger_path else None,
            "entry_appended": False,
            "baseline_window": baseline_window,
        },
    }
    _validate_summary(summary)

    if ledger_path:
        entry = build_goldset_ledger_entry(
            summary,
            manifest_path=manifest_file,
            notes=notes,
            operator=operator,
        )
        target_ledger_path = Path(ledger_path)
        _append_ledger_entry(target_ledger_path, entry)
        summary["calibration_ledger"] = {
            "path": str(target_ledger_path.resolve()),
            "entry_appended": True,
            "baseline_window": baseline_window,
        }

    # Public holdout masking is applied only after the full summary has been
    # validated, so blindness does not weaken internal governance checks.
    public_summary = _build_public_holdout_summary(summary, manifest_sha256=manifest_sha256, governance=governance)
    _validate_summary(public_summary)
    return public_summary
