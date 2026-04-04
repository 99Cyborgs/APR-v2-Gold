from __future__ import annotations

from apr_core.goldset.governance.leakage_guard import GOVERNANCE_VERSION, enforce_leakage_envelope


def _fit_linear(xs: list[float], ys: list[float]) -> tuple[float, float]:
    if not xs:
        return (0.0, 0.0)
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=False))
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return (0.0, y_mean)
    slope = numerator / denominator
    intercept = y_mean - (slope * x_mean)
    return (slope, intercept)


def test_reconstruction_error_remains_above_threshold_under_repeated_queries():
    base_loss = 3.0
    delta = 0.02
    history: list[dict[str, object]] = []
    visible_outputs: list[tuple[float, float]] = []

    for iteration in range(12):
        true_loss = base_loss + (iteration * delta)
        envelope = enforce_leakage_envelope(
            "reconstruction-target",
            {
                "loss": true_loss,
                "epsilon": 1.0,
                "budget_cap": 8,
                "run_id": iteration + 1,
                "governance_version": GOVERNANCE_VERSION,
            },
            history,
        )
        if envelope["noisy_loss"] is not None:
            visible_outputs.append((float(envelope["noisy_loss"]), true_loss))
        history.append({"case_id": "reconstruction-target", "leakage_guard": envelope})

    train_x = [point[0] for point in visible_outputs[:4]]
    train_y = [point[1] for point in visible_outputs[:4]]
    test_x = [point[0] for point in visible_outputs[4:]]
    test_y = [point[1] for point in visible_outputs[4:]]

    slope, intercept = _fit_linear(train_x, train_y)
    mean_absolute_error = sum(abs(((slope * value) + intercept) - expected) for value, expected in zip(test_x, test_y, strict=False)) / len(test_x)

    assert mean_absolute_error > 0.05
    assert len({value for value, _ in visible_outputs}) == len(visible_outputs)


def test_noise_does_not_collapse_and_budget_exhaustion_is_explicit():
    history: list[dict[str, object]] = []
    budgets: list[int] = []
    visible_outputs: list[float | None] = []

    for iteration in range(12):
        envelope = enforce_leakage_envelope(
            "budget-target",
            {
                "loss": 2.5,
                "epsilon": 1.0,
                "budget_cap": 8,
                "run_id": iteration + 1,
                "governance_version": GOVERNANCE_VERSION,
            },
            history,
        )
        budgets.append(envelope["query_budget"])
        visible_outputs.append(envelope["noisy_loss"])
        history.append({"case_id": "budget-target", "leakage_guard": envelope})

    assert budgets == sorted(budgets, reverse=True)
    assert budgets[-1] == 0
    assert visible_outputs[-1] is None
    assert len({value for value in visible_outputs[:-4] if value is not None}) == len([value for value in visible_outputs[:-4] if value is not None])
