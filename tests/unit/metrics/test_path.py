"""The shared wealth / drawdown-episode engine."""

from __future__ import annotations

import numpy as np
import pytest

from openfactsheet.metrics.path import drawdown_episodes, drawdown_path, wealth_index


def episodes(r: list[float]):  # type: ignore[no-untyped-def]
    w = wealth_index(np.asarray(r, dtype=np.float64))
    return drawdown_episodes(drawdown_path(w), None)


def test_wealth_starts_at_one() -> None:
    w = wealth_index(np.array([0.1, -0.5]))
    np.testing.assert_allclose(w, [1.0, 1.1, 0.55])


def test_first_period_loss_is_a_drawdown() -> None:
    (ep,) = episodes([-0.1, 0.2])
    assert ep.peak_index == 0
    assert ep.depth == pytest.approx(-0.1)
    assert ep.recovery_index == 2
    assert ep.duration_periods == 2
    assert ep.total_underwater_periods == 1


def test_no_drawdown_when_wealth_never_falls() -> None:
    assert episodes([0.01, 0.0, 0.02]) == ()


def test_multiple_episodes_and_ongoing() -> None:
    eps = episodes([0.1, -0.1, 0.2, -0.05, -0.05])
    assert len(eps) == 2
    first, second = eps
    assert first.recovered
    assert first.peak_index == 1
    assert first.trough_index == 2
    assert not second.recovered
    assert second.duration_periods == 2  # from peak (index 3) to the end (index 5)
    assert second.depth == pytest.approx(0.95 * 0.95 - 1)


def test_total_loss_never_recovers() -> None:
    (ep,) = episodes([0.1, -1.0, 0.5])
    assert ep.depth == pytest.approx(-1.0)
    assert not ep.recovered


def test_area_is_sum_of_underwater_depths() -> None:
    (ep,) = episodes([-0.1, -0.1, 0.3])
    assert ep.area == pytest.approx(0.1 + (1 - 0.81))
