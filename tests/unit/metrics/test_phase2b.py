"""Phase 2b metrics: drawdown tail, entropic risk, modified ES, calendar and rolling years."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

import openfactsheet as ofs
from openfactsheet.utils.math import entropic_value_at_risk
from tests.conftest import monthly

R = [0.01, -0.02, 0.015, 0.005, -0.01, 0.03, 0.02, -0.005, 0.012, -0.015, 0.008, 0.004]
r = np.asarray(R)


def v(report: ofs.FactsheetReport, mid: str) -> float:
    value = report.metrics[mid].value
    assert value is not None, report.metrics[mid].reason
    return value


@pytest.fixture(scope="module")
def report() -> ofs.FactsheetReport:
    return ofs.analyze(monthly(R))


def drawdown_path(x: np.ndarray) -> np.ndarray:
    wealth = np.concatenate([[1.0], np.cumprod(1 + x)])
    return (wealth / np.maximum.accumulate(wealth) - 1)[1:]


def test_simple_additions(report: ofs.FactsheetReport) -> None:
    assert v(report, "geometric_mean_return") == pytest.approx(np.prod(1 + r) ** (1 / 12) - 1)
    assert v(report, "interquartile_range") == pytest.approx(
        np.quantile(r, 0.75) - np.quantile(r, 0.25)
    )
    d = drawdown_path(r)
    assert v(report, "recovery_factor") == pytest.approx((np.prod(1 + r) - 1) / abs(d.min()))


def test_drawdown_tail(report: ofs.FactsheetReport) -> None:
    d = drawdown_path(r)
    q = np.quantile(d, 0.05)
    assert v(report, "drawdown_at_risk_95") == pytest.approx(q)
    assert v(report, "cdar_95") == pytest.approx(d[d <= q].mean())
    edar = v(report, "edar_95")
    # Ordering of coherent drawdown measures: MDD <= EDaR <= CDaR <= DaR <= 0.
    assert d.min() - 1e-12 <= edar <= v(report, "cdar_95") <= v(report, "drawdown_at_risk_95")


def test_entropic_var_brute_force() -> None:
    losses = -np.random.default_rng(7).normal(0.005, 0.03, 60)  # n > 1/alpha: interior optimum
    alpha = 0.05
    zs = np.exp(np.linspace(-8, 2, 40_001))
    brute = min(float(z * (np.log(np.mean(np.exp(losses / z))) - np.log(alpha))) for z in zs)
    assert entropic_value_at_risk(losses, alpha) == pytest.approx(brute, rel=1e-6)
    # EVaR lies between the Expected Shortfall and the worst loss.
    es = losses[losses >= np.quantile(losses, 0.95)].mean()
    assert es - 1e-12 <= entropic_value_at_risk(losses, alpha) <= losses.max() + 1e-12


def test_entropic_var_small_samples_equal_worst_loss() -> None:
    # With n <= 1/alpha (= 20) observations the infimum is the z -> 0 limit: max(X).
    assert entropic_value_at_risk(-r, 0.05) == pytest.approx(float((-r).max()))
    assert entropic_value_at_risk(np.zeros(5), 0.05) == 0.0
    assert entropic_value_at_risk(np.full(5, 0.03), 0.05) == pytest.approx(0.03)


def test_overflowing_ratio_is_not_applicable_not_error() -> None:
    # Found by hypothesis: a subnormal loss makes the gain-to-pain denominator ~0.
    rep = ofs.analyze(monthly([0.5, -2.2250738585e-313]), return_scale="decimal")
    res = rep.metrics["gain_to_pain_ratio"]
    assert res.status == "not_applicable"
    assert res.reason is not None
    assert "overflows" in res.reason


def test_nearly_constant_returns_have_no_shape_statistics() -> None:
    rep = ofs.analyze(monthly([0.01] * 30))
    for mid in ("skewness", "excess_kurtosis", "modified_var_95", "jarque_bera_pvalue"):
        assert rep.metrics[mid].status == "not_applicable", mid


def test_modified_es(report: ofs.FactsheetReport) -> None:
    mean, m2 = r.mean(), np.mean((r - r.mean()) ** 2)
    s = np.mean((r - mean) ** 3) / m2**1.5
    k = np.mean((r - mean) ** 4) / m2**2 - 3
    z = stats.norm.ppf(0.05)
    h = z + (z**2 - 1) * s / 6 + (z**3 - 3 * z) * k / 24 - (2 * z**3 - 5 * z) * s**2 / 36
    bracket = (
        1 + h**3 * s / 6 + (h**6 - 9 * h**4 + 9 * h**2 + 3) * s**2 / 72
        + (h**4 - 2 * h**2 - 1) * k / 24
    )  # fmt: skip
    expected = mean - math.sqrt(m2) / 0.05 * stats.norm.pdf(h) * bracket
    assert v(report, "modified_es_95") == pytest.approx(expected)


def test_episode_durations() -> None:
    # Episodes: peak 0 -> recovered at 3 (trough 2); peak 3 -> open (trough 5).
    rep = ofs.analyze(monthly([-0.1, -0.05, 0.3, -0.02, -0.03, 0.01]))
    assert v(rep, "average_drawdown_duration") == pytest.approx((3 + 3) / 2)
    assert v(rep, "max_peak_to_trough_duration") == 2
    assert v(rep, "average_recovery_duration") == 1  # only the recovered episode counts
    assert any("open episode" in w for w in rep.metrics["average_recovery_duration"].warnings)
    depths = [0.9 * 0.95 - 1, 0.98 * 0.97 - 1]
    assert v(rep, "median_drawdown") == pytest.approx(np.median(depths))


def test_calendar_years_exclude_partial_years() -> None:
    idx = pd.date_range("2019-07-31", "2022-03-31", freq="ME")
    values = np.linspace(-0.02, 0.03, len(idx))
    rep = ofs.analyze(pd.Series(values, index=idx))
    details = rep.metrics["positive_calendar_years_pct"].details
    assert set(details["calendar_year_returns"]) == {"2020", "2021"}
    assert set(details["excluded_partial_years"]) == {"2019", "2022"}
    y2020 = np.prod(1 + values[(idx.year == 2020)]) - 1
    assert details["calendar_year_returns"]["2020"] == pytest.approx(y2020)
    assert any(
        "Partial calendar years excluded" in w for w in rep.metrics["best_calendar_year"].warnings
    )


def test_calendar_year_with_missing_month_is_incomplete() -> None:
    idx = pd.date_range("2020-01-31", "2021-12-31", freq="ME").delete(5)
    rep = ofs.analyze(pd.Series(np.full(len(idx), 0.01), index=idx))
    details = rep.metrics["positive_calendar_years_pct"].details
    assert set(details["calendar_year_returns"]) == {"2021"}
    assert "2020" in details["excluded_partial_years"]


def test_calendar_years_quarterly_and_daily() -> None:
    q = pd.Series([0.01] * 8, index=pd.date_range("2020-03-31", periods=8, freq="QE"))
    assert ofs.analyze(q).metrics["positive_calendar_years_pct"].details["complete_years"] == 2
    days = pd.bdate_range("2020-01-02", "2021-06-30")
    daily = pd.Series(np.full(len(days), 0.0005), index=days)
    details = ofs.analyze(daily).metrics["positive_calendar_years_pct"].details
    assert set(details["calendar_year_returns"]) == {"2020"}
    assert set(details["excluded_partial_years"]) == {"2021"}


def test_calendar_years_need_dates() -> None:
    rep = ofs.analyze(list(np.full(24, 0.01)), frequency="monthly")
    res = rep.metrics["best_calendar_year"]
    assert res.status == "not_applicable"
    assert res.reason is not None
    assert "dated" in res.reason


def test_no_complete_year() -> None:
    rep = ofs.analyze(monthly([0.01] * 8, start="2020-03-31"))
    assert rep.metrics["worst_calendar_year"].status == "not_applicable"


def test_rolling_years() -> None:
    values = list(np.linspace(-0.03, 0.04, 30))
    rep = ofs.analyze(monthly(values))
    x = np.asarray(values)
    rolled = np.array([np.prod(1 + x[i : i + 12]) - 1 for i in range(len(x) - 11)])
    assert v(rep, "best_rolling_year") == pytest.approx(rolled.max())
    assert v(rep, "worst_rolling_year") == pytest.approx(rolled.min())
    assert v(rep, "positive_rolling_year_pct") == pytest.approx(np.mean(rolled > 0))
    assert rep.metrics["best_rolling_year"].details["windows"] == 19
    short = ofs.analyze(monthly([0.01] * 11))
    assert short.metrics["worst_rolling_year"].status == "not_applicable"
