"""Cross-checks against empyrical-reloaded and QuantStats (optional ``validation`` extra).

Skipped automatically when the reference libraries are not installed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import openfactsheet as ofs
from tests.conftest import SINGLE_FIXTURES, fixture_series

pytestmark = pytest.mark.cross_library
TOL = {"rel": 1e-9, "abs": 1e-12}


def val(report: ofs.FactsheetReport, mid: str) -> float:
    v = report.metrics[mid].value
    assert v is not None
    return v


@pytest.mark.parametrize("fixture", SINGLE_FIXTURES)
def test_empyrical(fixture: str) -> None:
    ep = pytest.importorskip("empyrical")
    s = fixture_series(fixture)
    rep = ofs.analyze(s)
    r = s.to_numpy()
    assert val(rep, "cumulative_return") == pytest.approx(ep.cum_returns_final(r), **TOL)
    assert val(rep, "cagr") == pytest.approx(ep.annual_return(r, period="monthly"), **TOL)
    assert val(rep, "annualized_volatility") == pytest.approx(
        ep.annual_volatility(r, period="monthly"), **TOL
    )
    assert val(rep, "sharpe_ratio") == pytest.approx(ep.sharpe_ratio(r, period="monthly"), **TOL)
    assert val(rep, "sortino_ratio") == pytest.approx(ep.sortino_ratio(r, period="monthly"), **TOL)
    assert val(rep, "downside_deviation") == pytest.approx(
        ep.downside_risk(r, period="monthly"), **TOL
    )
    assert val(rep, "max_drawdown") == pytest.approx(ep.max_drawdown(r), **TOL)
    assert val(rep, "calmar_ratio") == pytest.approx(ep.calmar_ratio(r, period="monthly"), **TOL)
    assert val(rep, "omega_ratio") == pytest.approx(ep.omega_ratio(r), **TOL)
    assert val(rep, "tail_ratio") == pytest.approx(ep.tail_ratio(r), **TOL)


def test_empyrical_benchmark() -> None:
    ep = pytest.importorskip("empyrical")
    fund, bench = fixture_series("benchmark_case_fund"), fixture_series("benchmark_case_benchmark")
    rep = ofs.analyze(fund, benchmark=bench)
    f = fund.copy()
    f.index = f.index.to_period("M")
    b = bench.copy()
    b.index = b.index.to_period("M")
    f, b = f.align(b, join="inner")
    fr, br = f.to_numpy(), b.to_numpy()
    assert val(rep, "beta") == pytest.approx(ep.beta(fr, br), **TOL)
    # empyrical annualizes alpha geometrically; OpenFactsheet arithmetically (decision 0012).
    alpha_pp = val(rep, "alpha") / 12
    assert ep.alpha(fr, br, period="monthly") == pytest.approx((1 + alpha_pp) ** 12 - 1, **TOL)
    assert val(rep, "upside_capture") == pytest.approx(
        ep.up_capture(fr, br, period="monthly"), **TOL
    )
    assert val(rep, "downside_capture") == pytest.approx(
        ep.down_capture(fr, br, period="monthly"), **TOL
    )


@pytest.mark.parametrize("fixture", SINGLE_FIXTURES)
def test_quantstats(fixture: str) -> None:
    qs = pytest.importorskip("quantstats")
    s = fixture_series(fixture)
    rep = ofs.analyze(s)
    assert val(rep, "sharpe_ratio") == pytest.approx(qs.stats.sharpe(s, periods=12), **TOL)
    assert val(rep, "max_drawdown") == pytest.approx(qs.stats.max_drawdown(s), **TOL)
    assert val(rep, "skewness") == pytest.approx(qs.stats.skew(s), **TOL)
    assert val(rep, "excess_kurtosis") == pytest.approx(qs.stats.kurtosis(s), **TOL)
    assert val(rep, "tail_ratio") == pytest.approx(qs.stats.tail_ratio(s), **TOL)
    assert val(rep, "best_period") == pytest.approx(float(np.max(s)), **TOL)
    assert val(rep, "worst_period") == pytest.approx(float(np.min(s)), **TOL)
    # QuantStats win_rate excludes zero returns; fixtures have none, so values coincide.
    assert (s == 0).sum() == 0
    assert val(rep, "positive_period_pct") == pytest.approx(qs.stats.win_rate(s), **TOL)
    assert isinstance(s.index, pd.DatetimeIndex)
