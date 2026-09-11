"""Hand-computed values for every Phase-1 metric on a small monthly series."""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats

import openfactsheet as ofs
from tests.conftest import monthly

R = [0.01, -0.02, 0.015, 0.005, -0.01, 0.03, 0.02, -0.005, 0.012, -0.015, 0.008, 0.004]
r = np.asarray(R)
N = len(R)


@pytest.fixture(scope="module")
def report() -> ofs.FactsheetReport:
    return ofs.analyze(monthly(R))


def v(report: ofs.FactsheetReport, mid: str) -> float:
    value = report.metrics[mid].value
    assert value is not None, report.metrics[mid].reason
    return value


def test_return_metrics(report: ofs.FactsheetReport) -> None:
    growth = float(np.prod(1 + r))
    assert v(report, "cumulative_return") == pytest.approx(growth - 1)
    assert v(report, "cagr") == pytest.approx(growth ** (12 / N) - 1)
    assert v(report, "arithmetic_mean") == pytest.approx(r.mean())
    assert v(report, "annualized_arithmetic_mean") == pytest.approx(12 * r.mean())
    assert v(report, "median_return") == pytest.approx(np.median(r))
    assert v(report, "best_period") == 0.03
    assert v(report, "worst_period") == -0.02
    assert report.metrics["worst_period"].details["date"] == "2020-02-29"
    assert v(report, "gain_to_pain_ratio") == pytest.approx(r.sum() / abs(r[r < 0].sum()))


def test_volatility_metrics(report: ofs.FactsheetReport) -> None:
    sd = r.std(ddof=1)
    assert v(report, "volatility") == pytest.approx(sd)
    assert v(report, "annualized_volatility") == pytest.approx(sd * math.sqrt(12))
    dd = math.sqrt(np.mean(np.minimum(r, 0) ** 2))
    assert v(report, "downside_deviation") == pytest.approx(dd * math.sqrt(12))


def test_risk_adjusted(report: ofs.FactsheetReport) -> None:
    sd = r.std(ddof=1)
    assert v(report, "sharpe_ratio") == pytest.approx(r.mean() / sd * math.sqrt(12))
    dd = math.sqrt(np.mean(np.minimum(r, 0) ** 2))
    assert v(report, "sortino_ratio") == pytest.approx(r.mean() / dd * math.sqrt(12))
    assert v(report, "omega_ratio") == pytest.approx(r[r > 0].sum() / -r[r < 0].sum())
    wealth = np.concatenate([[1.0], np.cumprod(1 + r)])
    ddpath = wealth / np.maximum.accumulate(wealth) - 1
    cagr = float(np.prod(1 + r)) ** (12 / N) - 1
    assert v(report, "calmar_ratio") == pytest.approx(cagr / abs(ddpath.min()))
    ulcer = math.sqrt(np.mean(ddpath[1:] ** 2))
    assert v(report, "martin_ratio") == pytest.approx(cagr / ulcer)


def test_drawdown_metrics(report: ofs.FactsheetReport) -> None:
    wealth = np.concatenate([[1.0], np.cumprod(1 + r)])
    ddpath = (wealth / np.maximum.accumulate(wealth) - 1)[1:]
    assert v(report, "max_drawdown") == pytest.approx(ddpath.min())
    assert v(report, "current_drawdown") == pytest.approx(ddpath[-1])
    assert v(report, "ulcer_index") == pytest.approx(math.sqrt(np.mean(ddpath**2)))
    assert v(report, "pain_index") == pytest.approx(np.mean(np.abs(ddpath)))
    assert v(report, "time_underwater_pct") == pytest.approx(np.mean(ddpath < 0))
    assert v(report, "drawdown_count") >= 1
    assert v(report, "average_drawdown") >= v(report, "max_drawdown")


def test_tail_metrics(report: ofs.FactsheetReport) -> None:
    q = np.quantile(r, 0.05)
    assert v(report, "var_historical_95") == pytest.approx(q)
    assert v(report, "expected_shortfall_historical_95") == pytest.approx(r[r <= q].mean())
    assert v(report, "tail_ratio") == pytest.approx(abs(np.quantile(r, 0.95)) / abs(q))
    assert v(report, "expected_shortfall_historical_95") <= v(report, "var_historical_95")


def test_distribution(report: ofs.FactsheetReport) -> None:
    assert v(report, "skewness") == pytest.approx(stats.skew(r, bias=False))
    assert v(report, "excess_kurtosis") == pytest.approx(stats.kurtosis(r, bias=False))


def test_consistency(report: ofs.FactsheetReport) -> None:
    assert v(report, "positive_period_pct") == pytest.approx(np.mean(r > 0))
    assert v(report, "negative_period_pct") == pytest.approx(np.mean(r < 0))
    assert v(report, "longest_winning_streak") == 2
    assert v(report, "longest_losing_streak") == 1


def test_dependence(report: ofs.FactsheetReport) -> None:
    m = r.mean()
    rho1 = np.sum((r[1:] - m) * (r[:-1] - m)) / np.sum((r - m) ** 2)
    assert v(report, "autocorrelation_lag1") == pytest.approx(rho1)
    assert v(report, "zero_return_pct") == 0.0
    lb = report.metrics["ljung_box_pvalue"]
    assert lb.status == "supplementary"
    assert 0.0 <= v(report, "ljung_box_pvalue") <= 1.0


def test_benchmark_metrics() -> None:
    fund = np.asarray(R)
    bench = np.asarray(
        [0.012, -0.015, 0.01, 0.0, -0.02, 0.025, 0.015, -0.01, 0.01, -0.02, 0.005, 0.01]
    )
    rep = ofs.analyze(monthly(list(fund)), benchmark=monthly(list(bench)))
    b, a = np.polyfit(bench, fund, 1)
    assert v(rep, "beta") == pytest.approx(b)
    assert v(rep, "alpha") == pytest.approx(a * 12)
    assert v(rep, "correlation") == pytest.approx(np.corrcoef(fund, bench)[0, 1])
    assert v(rep, "r_squared") == pytest.approx(np.corrcoef(fund, bench)[0, 1] ** 2)
    active = fund - bench
    te = active.std(ddof=1) * math.sqrt(12)
    assert v(rep, "tracking_error") == pytest.approx(te)
    assert v(rep, "active_return") == pytest.approx(active.mean() * 12)
    assert v(rep, "information_ratio") == pytest.approx(active.mean() * 12 / te)
    assert v(rep, "treynor_ratio") == pytest.approx(fund.mean() * 12 / b)
    up = bench > 0

    def ann(x: np.ndarray) -> float:
        return float(np.prod(1 + x) ** (12 / len(x)) - 1)

    assert v(rep, "upside_capture") == pytest.approx(ann(fund[up]) / ann(bench[up]))
    down = bench < 0
    assert v(rep, "downside_capture") == pytest.approx(ann(fund[down]) / ann(bench[down]))
