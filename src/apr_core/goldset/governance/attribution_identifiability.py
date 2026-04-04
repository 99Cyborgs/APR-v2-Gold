from __future__ import annotations

from typing import Any


def _as_rows(features: list[str], data: Any) -> list[dict[str, float]]:
    rows = data if isinstance(data, list) else [data]
    return [{feature: float((row or {}).get(feature, 0.0)) for feature in features} for row in rows if row is not None]


def _zeroed(row: dict[str, float], *features: str) -> dict[str, float]:
    updated = dict(row)
    for feature in features:
        updated[feature] = 0.0
    return updated


def compute_conditional_importance(features, model, data):
    rows = _as_rows(list(features), data)
    importance: dict[str, float] = {feature: 0.0 for feature in features}
    if not rows:
        return importance

    for row in rows:
        baseline = float(model(row))
        for feature in features:
            direct_delta = abs(baseline - float(model(_zeroed(row, feature))))
            conditioned_deltas = []
            for other in features:
                if other == feature:
                    continue
                left = float(model(_zeroed(row, other)))
                right = float(model(_zeroed(row, feature, other)))
                conditioned_deltas.append(abs(left - right))
            importance[feature] += direct_delta if not conditioned_deltas else sum(conditioned_deltas) / len(conditioned_deltas)

    row_count = float(len(rows))
    return {feature: round(total / row_count, 6) for feature, total in importance.items()}


def compute_interaction_matrix(features, model, data=None):
    rows = _as_rows(list(features), data if data is not None else {feature: 1.0 for feature in features})
    if not rows:
        return {feature: {other: 0.0 for other in features} for feature in features}

    totals = {feature: {other: 0.0 for other in features} for feature in features}
    for row in rows:
        baseline = float(model(row))
        for feature in features:
            for other in features:
                if feature == other:
                    continue
                delta_pair = baseline - float(model(_zeroed(row, feature, other)))
                delta_feature = baseline - float(model(_zeroed(row, feature)))
                delta_other = baseline - float(model(_zeroed(row, other)))
                totals[feature][other] += delta_pair - delta_feature - delta_other

    row_count = float(len(rows))
    return {
        feature: {
            other: 0.0 if feature == other else round(total / row_count, 6)
            for other, total in others.items()
        }
        for feature, others in totals.items()
    }


def _attribution_matrix(
    features: list[str],
    conditional_importance: dict[str, float],
    interaction_matrix: dict[str, dict[str, float]],
) -> list[list[float]]:
    matrix: list[list[float]] = []
    for feature in features:
        row: list[float] = []
        for other in features:
            if feature == other:
                row.append(float(conditional_importance.get(feature, 0.0)))
            else:
                row.append(float((interaction_matrix.get(feature) or {}).get(other, 0.0)))
        matrix.append(row)
    return matrix


def _matrix_rank(matrix: list[list[float]], tolerance: float = 1e-9) -> int:
    if not matrix:
        return 0
    rows = [list(map(float, row)) for row in matrix]
    rank = 0
    row_count = len(rows)
    column_count = len(rows[0]) if rows else 0

    for column in range(column_count):
        pivot = None
        for row_index in range(rank, row_count):
            if abs(rows[row_index][column]) > tolerance:
                pivot = row_index
                break
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        pivot_value = rows[rank][column]
        rows[rank] = [value / pivot_value for value in rows[rank]]
        for row_index in range(row_count):
            if row_index == rank:
                continue
            factor = rows[row_index][column]
            if abs(factor) <= tolerance:
                continue
            rows[row_index] = [
                current - factor * pivot_component
                for current, pivot_component in zip(rows[row_index], rows[rank], strict=False)
            ]
        rank += 1
        if rank == row_count:
            break
    return rank


def _matrix_inverse(matrix: list[list[float]], tolerance: float = 1e-9) -> list[list[float]] | None:
    size = len(matrix)
    if size == 0:
        return []
    augmented = [
        [float(value) for value in row] + [1.0 if index == row_index else 0.0 for index in range(size)]
        for row_index, row in enumerate(matrix)
    ]
    for column in range(size):
        pivot = None
        for row_index in range(column, size):
            if abs(augmented[row_index][column]) > tolerance:
                pivot = row_index
                break
        if pivot is None:
            return None
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row_index in range(size):
            if row_index == column:
                continue
            factor = augmented[row_index][column]
            if abs(factor) <= tolerance:
                continue
            augmented[row_index] = [
                current - factor * pivot_component
                for current, pivot_component in zip(augmented[row_index], augmented[column], strict=False)
            ]
    return [row[size:] for row in augmented]


def _matrix_infinity_norm(matrix: list[list[float]]) -> float:
    if not matrix:
        return 0.0
    return max(sum(abs(float(value)) for value in row) for row in matrix)


def _condition_number(matrix: list[list[float]], tolerance: float = 1e-9) -> float:
    inverse = _matrix_inverse(matrix, tolerance=tolerance)
    if inverse is None:
        return float("inf")
    return _matrix_infinity_norm(matrix) * _matrix_infinity_norm(inverse)


def detect_non_identifiability(attribution_vector):
    if not attribution_vector:
        return "degenerate"
    if "classification" in attribution_vector:
        return attribution_vector["classification"]

    conditional_importance = attribution_vector.get("conditional_importance", attribution_vector)
    if not isinstance(conditional_importance, dict) or not conditional_importance:
        return "degenerate"

    features = list(conditional_importance)
    interaction_matrix = attribution_vector.get("interaction_matrix", {})
    attribution_matrix = _attribution_matrix(features, conditional_importance, interaction_matrix)
    tolerance = float(attribution_vector.get("rank_tolerance", 1e-9) or 1e-9)
    rank_threshold = min(len(features), int(attribution_vector.get("rank_threshold", len(features)) or len(features)))
    if _matrix_rank(attribution_matrix, tolerance=tolerance) < rank_threshold:
        return "degenerate"

    condition_number = _condition_number(attribution_matrix, tolerance=tolerance)
    if condition_number > float(attribution_vector.get("condition_number_threshold", 1_000_000.0) or 1_000_000.0):
        return "degenerate"

    ordered = sorted((abs(float(value)), key) for key, value in conditional_importance.items())
    top = ordered[-1][0]
    second = ordered[-2][0] if len(ordered) > 1 else 0.0
    if top <= 0.0:
        return "degenerate"
    interaction_threshold = float(attribution_vector.get("correlation_threshold", 0.05) or 0.05)
    if second > 0.0 and abs(top - second) <= max(0.05, top * 0.1):
        for feature, others in interaction_matrix.items():
            for other, strength in (others or {}).items():
                if feature != other and abs(float(strength)) > interaction_threshold:
                    return "correlated"
        return "degenerate"
    return "unique"


def build_counterfactual_summary(counterfactuals: list[dict[str, Any]], stability: float | None) -> dict[str, Any]:
    if not counterfactuals:
        return {
            "stability": 1.0 if stability is None else stability,
            "identifiability": "degenerate",
            "identifiability_status": "degenerate",
            "interaction_strength": 0.0,
            "conditional_importance": {},
            "interaction_matrix": {},
            "attribution_rank": 0,
            "warning": "non_identifiable_attribution",
        }

    features = [item["feature"] for item in counterfactuals]
    base_row = {item["feature"]: float(item.get("delta_loss") or 0.0) for item in counterfactuals}
    model = lambda row: sum(float(value) for value in row.values())
    conditional_importance = compute_conditional_importance(features, model, base_row)
    interaction_matrix = compute_interaction_matrix(features, model, base_row)
    attribution_rank = _matrix_rank(_attribution_matrix(features, conditional_importance, interaction_matrix))
    identifiability = detect_non_identifiability(
        {
            "conditional_importance": conditional_importance,
            "interaction_matrix": interaction_matrix,
        }
    )
    interaction_strength = max(
        (abs(float(strength)) for others in interaction_matrix.values() for strength in others.values()),
        default=0.0,
    )
    result = {
        "stability": 1.0 if stability is None else stability,
        "identifiability": identifiability,
        "identifiability_status": identifiability,
        "interaction_strength": round(interaction_strength, 6),
        "conditional_importance": conditional_importance,
        "interaction_matrix": interaction_matrix,
        "attribution_rank": attribution_rank,
    }
    if identifiability != "unique":
        result["warning"] = "non_identifiable_attribution"
    return result
