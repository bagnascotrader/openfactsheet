"""Mathematical identities (CLAUDE.md section 31.2), property-based."""

from __future__ import annotations

import math

import numpy as np
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import openfactsheet as ofs
from tests.conftest import monthly

returns = st.lists(
    st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=48,
)
SETTINGS = settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow])


@SETTINGS
@given(returns)
def test_no_metric_is_ever_non_finite(values: list[float]) -> None:
    rep = ofs.analyze(monthly(values), return_scale="decimal")
    for m in rep.metrics:
        assert (m.value is None and m.reason) or (m.value is not None and math.isfinite(m.value))
        assert m.status != "error", f"{m.id}: {m.reason}"


@SETTINGS
@given(st.integers(min_value=1, max_value=36))
def test_zero_returns(n: int) -> None:
    rep = ofs.analyze(monthly([0.0] * n))
    assert rep.metrics["cumulative_return"].value == 0.0
    assert rep.metrics["max_drawdown"].value == 0.0
    if n >= 2:
        assert rep.metrics["volatility"].value == 0.0


@SETTINGS
@given(st.lists(st.floats(min_value=0.0, max_value=0.2), min_size=1, max_size=48))
def test_non_decreasing_wealth_has_no_drawdown(values: list[float]) -> None:
    rep = ofs.analyze(monthly(values), return_scale="decimal")
    assert rep.metrics["max_drawdown"].value == 0.0
    assert rep.metrics["time_underwater_pct"].value == 0.0


@SETTINGS
@given(st.lists(st.floats(min_value=-0.2, max_value=0.2), min_size=4, max_size=48))
def test_identical_fund_and_benchmark(values: list[float]) -> None:
    arr = np.asarray(values)
    if np.ptp(arr) < 1e-6:
        return
    s = monthly(values)
    rep = ofs.analyze(s, benchmark=s.copy(), return_scale="decimal")
    assert rep.metrics["beta"].value is not None
    assert math.isclose(rep.metrics["beta"].value, 1.0, rel_tol=1e-9)
    assert rep.metrics["tracking_error"].value == 0.0
    assert rep.metrics["active_return"].value == 0.0
    assert rep.metrics["information_ratio"].status == "not_applicable"


@SETTINGS
@given(returns)
def test_ordering_invariants(values: list[float]) -> None:
    rep = ofs.analyze(monthly(values), return_scale="decimal")
    m = rep.metrics
    assert m["worst_period"].value is not None
    assert m["best_period"].value is not None
    assert m["worst_period"].value <= m["median_return"].value <= m["best_period"].value  # type: ignore[operator]
    mdd = m["max_drawdown"].value
    cur = m["current_drawdown"].value
    assert mdd is not None
    assert cur is not None
    assert -1.0 <= mdd <= cur <= 0.0
    es, var = m["expected_shortfall_historical_95"].value, m["var_historical_95"].value
    if es is not None and var is not None:
        assert es <= var + 1e-15
