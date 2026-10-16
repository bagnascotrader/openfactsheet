"""Cross-checks against empyrical-reloaded and QuantStats (optional ``validation`` extra).

Skipped automatically when the reference libraries are not installed.
"""

from __future__ import annotations

from importlib.metadata import version

import numpy as np
import pandas as pd
import pytest
from packaging.version import Version
from scipy import stats

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
    assert val(rep, "capture_ratio") == pytest.approx(
        ep.up_down_capture(fr, br, period="monthly"), **TOL
    )


@pytest.mark.parametrize("fixture", SINGLE_FIXTURES)
def test_skfolio_drawdown_and_entropic_measures(fixture: str) -> None:
    sm = pytest.importorskip("skfolio.measures")
    s = fixture_series(fixture)
    rep = ofs.analyze(s)
    r = s.to_numpy()
    wealth = np.concatenate([[1.0], np.cumprod(1 + r)])
    d = (wealth / np.maximum.accumulate(wealth) - 1)[1:]  # canonical path D_1..D_n
    # Drawdown path (decision 0007): OpenFactsheet counts W_0 = 1 as a peak, so a
    # first-period loss is a drawdown. skfolio started its running peak at W_1 until
    # 1.4.1, which adopted the same convention; both are asserted by version because
    # the validation extra is not pinned.
    if Version(version("skfolio")) >= Version("1.4.1"):
        np.testing.assert_allclose(sm.get_drawdowns(r, compounded=True), d)
    else:
        w1 = wealth[1:]
        np.testing.assert_allclose(
            sm.get_drawdowns(r, compounded=True), w1 / np.maximum.accumulate(w1) - 1
        )
    # The risk-measure estimators are compared on the canonical path.

    # EDaR / EVaR: same definition, solver tolerance.
    assert val(rep, "edar_95") == pytest.approx(-sm.edar(d, 0.95), rel=1e-7)
    assert val(rep, "evar_95") == pytest.approx(-sm.evar(r, 0.95), rel=1e-7)
    # DaR: skfolio uses the lower order statistic; OpenFactsheet the linear quantile.
    assert sm.drawdown_at_risk(d, 0.95) == pytest.approx(
        float(np.quantile(-d, 0.95, method="inverted_cdf")), **TOL
    )
    assert val(rep, "drawdown_at_risk_95") == pytest.approx(
        float(np.quantile(d, 0.05, method="linear")), **TOL
    )
    # CDaR agrees exactly when (1 - 0.95) * n is an integer (n = 120 in monthly_fund_10y).
    if round(0.05 * len(r), 9).is_integer():
        assert val(rep, "cdar_95") == pytest.approx(-sm.cdar(d, 0.95), **TOL)


@pytest.mark.parametrize("fixture", SINGLE_FIXTURES)
def test_skfolio_gini_mean_difference(fixture: str) -> None:
    sm = pytest.importorskip("skfolio.measures")
    s = fixture_series(fixture)
    rep = ofs.analyze(s)
    r = s.to_numpy()
    # Same definition: mean |r_i - r_j| over the n(n-1) ordered pairs (decision 0036).
    assert val(rep, "gini_mean_difference") == pytest.approx(sm.gini_mean_difference(r), **TOL)
    assert val(rep, "relative_mean_difference") == pytest.approx(
        sm.gini_mean_difference(r) / r.mean(), **TOL
    )


def test_quantstats_recovery_factor_uses_arithmetic_sum() -> None:
    qs = pytest.importorskip("quantstats")
    s = fixture_series("monthly_fund_10y")
    rep = ofs.analyze(s)
    mdd = abs(val(rep, "max_drawdown"))
    assert qs.stats.recovery_factor(s) == pytest.approx(float(s.sum()) / mdd, **TOL)
    assert val(rep, "recovery_factor") == pytest.approx(val(rep, "cumulative_return") / mdd, **TOL)
    assert val(rep, "recovery_factor") != pytest.approx(qs.stats.recovery_factor(s))


@pytest.mark.parametrize("fixture", SINGLE_FIXTURES)
def test_scipy_normality_and_mean_inference(fixture: str) -> None:
    s = fixture_series(fixture)
    rep = ofs.analyze(s)
    jb = stats.jarque_bera(s.to_numpy())
    assert rep.metrics["jarque_bera_pvalue"].details["statistic"] == pytest.approx(
        jb.statistic, **TOL
    )
    assert val(rep, "jarque_bera_pvalue") == pytest.approx(jb.pvalue, rel=1e-7)
    tt = stats.ttest_1samp(s.to_numpy(), 0.0)
    assert rep.metrics["mean_return_standard_error"].details["p_value"] == pytest.approx(
        tt.pvalue, rel=1e-9
    )


def test_quantstats_information_ratio_is_per_period() -> None:
    qs = pytest.importorskip("quantstats")
    fund, bench = fixture_series("benchmark_case_fund"), fixture_series("benchmark_case_benchmark")
    rep = ofs.analyze(fund, benchmark=bench)
    f, b = fund.copy(), bench.copy()
    f.index, b.index = f.index.to_period("M"), b.index.to_period("M")
    f, b = f.align(b, join="inner")
    f.index, b.index = f.index.to_timestamp(how="end"), b.index.to_timestamp(how="end")
    # QuantStats reports the non-annualized ratio; OpenFactsheet annualizes by sqrt(12).
    assert val(rep, "information_ratio") / np.sqrt(12) == pytest.approx(
        qs.stats.information_ratio(f, b), **TOL
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
    assert val(rep, "gain_to_pain_ratio") == pytest.approx(qs.stats.gain_to_pain_ratio(s), **TOL)
    assert val(rep, "profit_factor") == pytest.approx(qs.stats.profit_factor(s), **TOL)
    # CAGR agrees when the frequency is passed; the default (252) treats months as days.
    assert val(rep, "cagr") == pytest.approx(qs.stats.cagr(s, periods=12), **TOL)
    assert qs.stats.cagr(s) != pytest.approx(val(rep, "cagr"))
    # Calmar inherits the default CAGR, divided by |max drawdown|.
    assert qs.stats.calmar(s) == pytest.approx(
        qs.stats.cagr(s) / abs(val(rep, "max_drawdown")), **TOL
    )
    # QuantStats VaR is parametric (normal, sample std), not historical.
    r = s.to_numpy()
    normal_var = stats.norm.ppf(0.05, r.mean(), r.std(ddof=1))
    assert qs.stats.value_at_risk(s) == pytest.approx(normal_var, **TOL)
    assert qs.stats.value_at_risk(s) != pytest.approx(val(rep, "var_historical_95"))
    assert val(rep, "payoff_ratio") == pytest.approx(qs.stats.payoff_ratio(s), **TOL)
    # QuantStats win_rate excludes zero returns; fixtures have none, so values coincide.
    assert (s == 0).sum() == 0
    assert val(rep, "positive_period_pct") == pytest.approx(qs.stats.win_rate(s), **TOL)
    assert isinstance(s.index, pd.DatetimeIndex)
