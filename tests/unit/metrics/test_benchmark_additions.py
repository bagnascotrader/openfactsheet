"""Decision 0027: capture ratio, batting average, residual risk, appraisal ratio, M-squared,
bull / bear betas and the timing ratio - formulas and benchmark edge cases."""

from __future__ import annotations

import math

import numpy as np
import pytest

import openfactsheet as ofs
from tests.conftest import monthly
from tests.unit.metrics.test_edge_cases import assert_structured

FUND = np.array(
    [0.012, -0.018, 0.02, 0.004, -0.012, 0.028, 0.017, -0.004, 0.011, -0.016, 0.007, 0.006,
     0.009, -0.025, 0.015, 0.001, -0.007, 0.021]
)  # fmt: skip
BENCH = np.array(
    [0.010, -0.015, 0.012, 0.0, -0.02, 0.025, 0.015, -0.01, 0.01, -0.02, 0.005, 0.01,
     0.004, -0.03, 0.02, 0.003, -0.012, 0.018]
)  # fmt: skip
NEW = (
    "capture_ratio",
    "batting_average",
    "residual_volatility",
    "appraisal_ratio",
    "m_squared",
    "bull_beta",
    "bear_beta",
    "timing_ratio",
)


def v(report: ofs.FactsheetReport, mid: str) -> float:
    value = report.metrics[mid].value
    assert value is not None, report.metrics[mid].reason
    return value


def analyze(fund: np.ndarray, bench: np.ndarray) -> ofs.FactsheetReport:
    return ofs.analyze(monthly(list(fund)), benchmark=monthly(list(bench)))


@pytest.fixture(scope="module")
def report() -> ofs.FactsheetReport:
    return analyze(FUND, BENCH)


def test_regression_based_metrics(report: ofs.FactsheetReport) -> None:
    beta, alpha = np.polyfit(BENCH, FUND, 1)
    resid = FUND - alpha - beta * BENCH
    sigma = math.sqrt(float(np.sum(resid**2)) / (len(FUND) - 2))
    assert v(report, "residual_volatility") == pytest.approx(sigma * math.sqrt(12))
    assert v(report, "appraisal_ratio") == pytest.approx(alpha / sigma * math.sqrt(12))
    systematic = report.metrics["residual_volatility"].details["systematic_volatility"]
    assert systematic == pytest.approx(abs(beta) * BENCH.std(ddof=1) * math.sqrt(12))


def test_regime_betas_and_timing_ratio(report: ofs.FactsheetReport) -> None:
    up, down = BENCH > 0, BENCH < 0
    bull = np.polyfit(BENCH[up], FUND[up], 1)[0]
    bear = np.polyfit(BENCH[down], FUND[down], 1)[0]
    assert v(report, "bull_beta") == pytest.approx(bull)
    assert v(report, "bear_beta") == pytest.approx(bear)
    assert v(report, "timing_ratio") == pytest.approx(bull / bear)
    assert report.metrics["bull_beta"].details["up_periods"] == int(up.sum())
    # Zero-benchmark periods (one here) belong to neither regime.
    assert int(up.sum()) + int(down.sum()) == len(BENCH) - 1
    assert any("only" in w for w in report.metrics["bear_beta"].warnings)


def test_batting_average_and_capture_ratio(report: ofs.FactsheetReport) -> None:
    beat = FUND > BENCH
    assert v(report, "batting_average") == pytest.approx(beat.mean())
    d = report.metrics["batting_average"].details
    assert d["up_market_batting_average"] == pytest.approx(beat[BENCH > 0].mean())
    assert d["down_market_batting_average"] == pytest.approx(beat[BENCH < 0].mean())
    assert v(report, "capture_ratio") == pytest.approx(
        v(report, "upside_capture") / v(report, "downside_capture")
    )


def test_m_squared(report: ofs.FactsheetReport) -> None:
    expected = FUND.mean() / FUND.std(ddof=1) * BENCH.std(ddof=1) * 12
    assert v(report, "m_squared") == pytest.approx(expected)
    d = report.metrics["m_squared"].details
    assert d["m_squared_excess"] == pytest.approx(expected - BENCH.mean() * 12)
    # M-squared at the benchmark's own volatility: equal to the benchmark's return when the
    # fund has the benchmark's Sharpe ratio (here: the fund is the leveraged benchmark).
    lev = analyze(2.0 * BENCH, BENCH)
    assert v(lev, "m_squared") == pytest.approx(BENCH.mean() * 12)


def test_identical_fund_and_benchmark() -> None:
    rep = analyze(BENCH, BENCH)
    assert_structured(rep)
    assert v(rep, "bull_beta") == pytest.approx(1.0)
    assert v(rep, "bear_beta") == pytest.approx(1.0)
    assert v(rep, "timing_ratio") == pytest.approx(1.0)
    assert v(rep, "capture_ratio") == pytest.approx(1.0)
    assert v(rep, "batting_average") == 0.0  # ties never count as beating
    assert rep.metrics["batting_average"].details["ties"] == len(BENCH)
    assert v(rep, "residual_volatility") == pytest.approx(0.0, abs=1e-12)
    assert v(rep, "m_squared") == pytest.approx(BENCH.mean() * 12)
    # Residuals are zero up to rounding: alpha / residual risk would be rounding noise.
    assert rep.metrics["appraisal_ratio"].status == "not_applicable"


@pytest.mark.parametrize(("scale", "shift"), [(0.5, 0.0), (1.7, 0.002), (-0.3, -0.001)])
def test_exact_fit_makes_appraisal_ratio_undefined(scale: float, shift: float) -> None:
    rep = analyze(scale * BENCH + shift, BENCH)
    assert v(rep, "r_squared") == pytest.approx(1.0)
    res = rep.metrics["appraisal_ratio"]
    assert res.status == "not_applicable"
    assert res.reason is not None
    assert "floating-point precision" in res.reason


def test_nearly_exact_fit_still_has_an_appraisal_ratio() -> None:
    noise = np.sin(np.arange(len(BENCH))) * 1e-6  # tiny but real residual risk
    rep = analyze(BENCH + noise, BENCH)
    assert math.isfinite(v(rep, "appraisal_ratio"))


def test_benchmark_without_down_periods() -> None:
    bench = np.abs(BENCH) + 0.001
    rep = analyze(FUND, bench)
    assert_structured(rep)
    for mid in ("bear_beta", "timing_ratio", "capture_ratio", "downside_capture"):
        assert rep.metrics[mid].status == "not_applicable", mid
    assert rep.metrics["batting_average"].details["down_market_batting_average"] is None
    assert rep.metrics["bull_beta"].value is not None


def test_negative_downside_capture_makes_capture_ratio_undefined() -> None:
    fund = np.where(BENCH < 0, 0.01, BENCH)  # gains whenever the benchmark falls
    rep = analyze(fund, BENCH)
    assert v(rep, "downside_capture") < 0
    res = rep.metrics["capture_ratio"]
    assert res.status == "not_applicable"
    assert res.reason is not None
    assert "non-positive denominator" in res.reason


def test_negative_bear_beta_makes_timing_ratio_undefined() -> None:
    fund = np.where(BENCH < 0, -0.5 * BENCH, BENCH)
    rep = analyze(fund, BENCH)
    assert v(rep, "bear_beta") == pytest.approx(-0.5)
    assert rep.metrics["timing_ratio"].status == "not_applicable"


def test_too_few_regime_periods() -> None:
    bench = np.array([0.01, 0.02, -0.01, 0.015, 0.03, -0.02, 0.01, 0.005])  # 2 down periods
    fund = bench * 0.8 + 0.001
    rep = analyze(fund, bench)
    assert_structured(rep)
    res = rep.metrics["bear_beta"]
    assert res.status == "not_applicable"
    assert res.reason is not None
    assert "down periods contain 2" in res.reason


def test_constant_benchmark() -> None:
    rep = analyze(FUND, np.full(len(FUND), 0.005))
    assert_structured(rep)
    for mid in ("residual_volatility", "appraisal_ratio", "m_squared", "bull_beta"):
        assert rep.metrics[mid].status == "not_applicable", mid
    assert v(rep, "batting_average") == pytest.approx(float(np.mean(FUND > 0.005)))


@pytest.mark.parametrize("level", [0.0, 0.01, -0.003])
def test_constant_fund_has_exact_zero_beta(level: float) -> None:
    """A constant fund has beta exactly 0; rounding noise must not reach ratios dividing by
    beta or by residual risk (found while adding decision 0027)."""
    rep = analyze(np.full(len(BENCH), level), BENCH)
    assert_structured(rep)
    for mid in ("beta", "bull_beta", "bear_beta", "residual_volatility"):
        assert rep.metrics[mid].value == 0.0, mid
    assert v(rep, "alpha") == pytest.approx(level * 12)
    for mid in ("treynor_ratio", "appraisal_ratio", "timing_ratio", "r_squared", "m_squared"):
        assert rep.metrics[mid].status == "not_applicable", mid


@pytest.mark.parametrize(
    ("fund", "bench"),
    [
        ([0.01, -0.02, 0.03], [0.02, -0.01, 0.01]),  # minimal regression overlap
        ([0.01, -0.02], [0.02, -0.01]),  # below the regression minimum
        ([0.0] * 8, [0.01, -0.02, 0.015, 0.005, -0.01, 0.03, 0.02, -0.005]),  # constant fund
        ([-0.01] * 3 + [-0.02] * 3, [-0.01, -0.02, -0.015, -0.005, -0.03, -0.01]),  # all down
    ],
)
def test_benchmark_edge_cases_are_structured(fund: list[float], bench: list[float]) -> None:
    rep = analyze(np.asarray(fund), np.asarray(bench))
    assert_structured(rep)
    for mid in NEW:
        assert mid in rep.metrics


def test_new_metrics_not_applicable_without_benchmark() -> None:
    rep = ofs.analyze(monthly(list(FUND)))
    for mid in NEW:
        assert rep.metrics[mid].status == "not_applicable", mid
