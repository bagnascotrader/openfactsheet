"""Acceptance tests from CLAUDE.md sections 48-50."""

from __future__ import annotations

import json
import math

import pandas as pd

import openfactsheet as ofs
from tests.conftest import FIXTURES


def test_first_acceptance_short_monthly_series() -> None:
    returns = pd.Series(
        [0.01, -0.02, 0.015, 0.005, -0.01, 0.03],
        index=pd.date_range("2025-01-31", periods=6, freq="ME"),
    )

    report = ofs.analyze(returns)
    text = report.summary()

    # recognizes monthly frequency and records six observations
    assert report.returns.frequency is ofs.ObservationFrequency.MONTHLY
    assert report.input_summary.observations == 6
    assert "monthly" in text

    # calculates all mathematically valid metrics; nothing is silently missing
    for m in report.metrics:
        assert m.value is not None or m.reason, m.id
        if m.value is not None:
            assert math.isfinite(m.value)
    assert report.metrics["cagr"].value is not None
    assert report.metrics["sharpe_ratio"].value is not None

    # marks unreliable metrics as low-confidence / insufficient-data
    assert report.metrics["sharpe_ratio"].status == "low_confidence"
    assert report.metrics["ljung_box_pvalue"].status == "insufficient_data"

    # explains annualization
    assert "Annualized with 12 periods per year" in text
    assert any("12 periods per year" in a for a in report.metrics["cagr"].assumptions)

    # explains why benchmark metrics are unavailable
    beta = report.metrics["beta"]
    assert beta.status == "not_applicable"
    assert beta.reason is not None and "No benchmark was supplied" in beta.reason

    # produces stable JSON
    first = report.to_json()
    second = ofs.analyze(returns).to_json()
    assert first == second
    parsed = json.loads(first)
    assert parsed["methodology"]["version"] == ofs.METHODOLOGY_VERSION
    assert len(parsed["returns"]) == 6


def test_second_acceptance_benchmark(benchmark_pair: tuple[pd.Series, pd.Series]) -> None:
    fund, bench = benchmark_pair
    report = ofs.analyze(fund, benchmark=bench)
    summary = report.benchmark_summary
    assert summary is not None

    # aligns on common timestamps (month-end fund vs month-start benchmark) and reports loss
    assert summary.aligned_observations == 96
    assert summary.fund_only_periods == 6
    assert summary.benchmark_only_periods == 6
    assert summary.alignment_method == "calendar monthly period"

    # computes the benchmark-relative metrics
    for mid in (
        "beta",
        "alpha",
        "correlation",
        "tracking_error",
        "information_ratio",
        "upside_capture",
        "downside_capture",
        "treynor_ratio",
    ):
        m = report.metrics[mid]
        assert m.value is not None, mid
        # stores the benchmark-dependent observation count separately
        assert m.observations == 96, mid
    assert report.metrics["sharpe_ratio"].observations == 102

    # never fills missing benchmark returns
    assert any("never filled" in w for w in summary.warnings)


def test_second_acceptance_benchmark_is_never_zero_filled() -> None:
    fund = pd.Series(
        [0.01, 0.02, -0.01, 0.03], index=pd.date_range("2020-01-31", periods=4, freq="ME")
    )
    bench = pd.Series([0.01, None, -0.02, 0.02], index=fund.index)
    report = ofs.analyze(fund, benchmark=bench)
    assert report.benchmark_summary is not None
    assert report.benchmark_summary.aligned_observations == 3


def test_third_acceptance_suspicious_hedge_fund(hedge_fund: pd.Series) -> None:
    report = ofs.analyze(hedge_fund)

    # computes Sharpe
    sharpe = report.metrics["sharpe_ratio"]
    assert sharpe.value is not None and sharpe.value > 1.5

    # flags smoothing / serial-correlation concerns
    assert report.diagnostics.smoothing_risk == "high"
    assert any(f.id == "smoothing_risk" for f in report.diagnostics.findings)

    # does not present the high Sharpe as unquestioned evidence of quality
    assert sharpe.status == "low_confidence"
    assert sharpe.confidence == "low"
    assert any("smoothed" in w for w in sharpe.warnings)
    assert any("optimistic bound" in c for c in report.interpretations["sharpe_ratio"].context)

    # shows drawdown / tail metrics
    for mid in ("max_drawdown", "expected_shortfall_historical_95", "worst_period", "skewness"):
        assert report.metrics[mid].value is not None, mid
    text = report.summary()
    assert "Maximum drawdown" in text and "Expected Shortfall" in text


def test_csv_path_input_matches_series(fund_10y: pd.Series) -> None:
    from_path = ofs.analyze(FIXTURES / "monthly_fund_10y.csv", name="monthly_fund_10y")
    from_series = ofs.analyze(fund_10y)
    assert from_path.metrics.values() == from_series.metrics.values()
