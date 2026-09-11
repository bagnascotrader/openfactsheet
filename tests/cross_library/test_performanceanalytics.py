"""Cross-check against R PerformanceAnalytics 2.0.4 (committed reference JSON).

Regenerate references with ``Rscript validation/r/performanceanalytics_reference.R``.
Known convention differences are asserted explicitly, not hidden
(see docs/validation/reference_implementations.md).
"""

from __future__ import annotations

import math
from typing import Any

import pytest

import openfactsheet as ofs
from tests.conftest import SINGLE_FIXTURES, fixture_series

pytestmark = pytest.mark.cross_library

TOL = {"rel": 1e-9, "abs": 1e-12}


def val(report: ofs.FactsheetReport, mid: str) -> float:
    v = report.metrics[mid].value
    assert v is not None, f"{mid}: {report.metrics[mid].reason}"
    return v


@pytest.mark.parametrize("fixture", SINGLE_FIXTURES)
def test_single_series_agreement(fixture: str, pa_reference: dict[str, Any]) -> None:
    ref = pa_reference[fixture]
    rep = ofs.analyze(fixture_series(fixture))
    assert rep.returns.n == ref["n"]

    # Direct agreement.
    assert val(rep, "cumulative_return") == pytest.approx(ref["cumulative_return"], **TOL)
    assert val(rep, "cagr") == pytest.approx(ref["cagr"], **TOL)
    assert val(rep, "annualized_arithmetic_mean") == pytest.approx(
        ref["annualized_arithmetic_mean"], **TOL
    )
    assert val(rep, "volatility") == pytest.approx(ref["volatility"], **TOL)
    assert val(rep, "annualized_volatility") == pytest.approx(ref["annualized_volatility"], **TOL)
    assert val(rep, "downside_deviation") == pytest.approx(
        ref["downside_deviation_per_period"] * math.sqrt(12), **TOL
    )
    assert val(rep, "sharpe_ratio") == pytest.approx(ref["sharpe_ratio_arithmetic"], **TOL)
    assert val(rep, "sortino_ratio") == pytest.approx(
        ref["sortino_ratio_per_period"] * math.sqrt(12), **TOL
    )
    assert val(rep, "calmar_ratio") == pytest.approx(ref["calmar_ratio"], **TOL)
    assert val(rep, "omega_ratio") == pytest.approx(ref["omega_ratio"], **TOL)
    assert val(rep, "excess_kurtosis") == pytest.approx(ref["excess_kurtosis_sample"], **TOL)
    assert val(rep, "var_historical_95") == pytest.approx(ref["var_historical_95"], **TOL)
    assert val(rep, "expected_shortfall_historical_95") == pytest.approx(
        ref["es_historical_95"], **TOL
    )
    for lag in (1, 2, 3):
        assert val(rep, f"autocorrelation_lag{lag}") == pytest.approx(ref[f"acf_lag{lag}"], **TOL)
    assert val(rep, "ljung_box_pvalue") == pytest.approx(ref["ljung_box_pvalue_3"], rel=1e-7)

    # Sign convention: OpenFactsheet reports drawdowns as signed returns.
    assert val(rep, "max_drawdown") == pytest.approx(-ref["max_drawdown_magnitude"], **TOL)
    assert val(rep, "average_drawdown") == pytest.approx(-ref["average_drawdown_magnitude"], **TOL)

    # Ulcer / Pain: PA's UlcerIndex/PainIndex use DrawdownPeak (percent-input assumption);
    # OpenFactsheet agrees with the same formulas applied to PA's own Drawdowns() path.
    assert val(rep, "ulcer_index") == pytest.approx(ref["ulcer_index_from_drawdowns"], **TOL)
    assert val(rep, "pain_index") == pytest.approx(ref["pain_index_from_drawdowns"], **TOL)
    assert val(rep, "martin_ratio") == pytest.approx(
        ref["cagr"] / ref["ulcer_index_from_drawdowns"], **TOL
    )

    # Skewness: PA 'moment' is the biased g1; OpenFactsheet reports bias-corrected G1.
    n = ref["n"]
    g1 = ref["skewness_moment"]
    assert val(rep, "skewness") == pytest.approx(g1 * math.sqrt(n * (n - 1)) / (n - 2), **TOL)
    # PA 'sample' = G1 * (n / (n - 1))^1.5 (documented discrepancy).
    assert ref["skewness_pa_sample"] == pytest.approx(
        val(rep, "skewness") * (n / (n - 1)) ** 1.5, **TOL
    )

    # Documented difference: PA's default annualized Sharpe uses the geometric return.
    assert ref["sharpe_ratio_pa_default_geometric"] != pytest.approx(val(rep, "sharpe_ratio"))


def test_drawdown_duration_convention(pa_reference: dict[str, Any]) -> None:
    """PA findDrawdowns length equals OpenFactsheet duration for recovered episodes and is
    one period longer for an episode still open at the end of the data."""
    for fixture in SINGLE_FIXTURES:
        rep = ofs.analyze(fixture_series(fixture))
        dur = rep.metrics["longest_drawdown_duration"]
        ongoing = bool(dur.details["ongoing"])
        expected = pa_reference[fixture]["longest_drawdown_length"] - (1 if ongoing else 0)
        assert dur.value == expected, fixture


def test_benchmark_agreement(pa_reference: dict[str, Any]) -> None:
    ref = pa_reference["benchmark_case"]
    rep = ofs.analyze(
        fixture_series("benchmark_case_fund"), benchmark=fixture_series("benchmark_case_benchmark")
    )
    assert rep.benchmark_summary is not None
    assert rep.benchmark_summary.aligned_observations == ref["aligned_observations"]
    assert val(rep, "beta") == pytest.approx(ref["beta"], **TOL)
    assert val(rep, "alpha") == pytest.approx(ref["alpha_per_period"] * 12, **TOL)
    assert val(rep, "correlation") == pytest.approx(ref["correlation"], **TOL)
    assert val(rep, "r_squared") == pytest.approx(ref["r_squared"], **TOL)
    assert val(rep, "tracking_error") == pytest.approx(ref["tracking_error"], **TOL)
    assert val(rep, "information_ratio") == pytest.approx(
        ref["information_ratio_arithmetic"], **TOL
    )
    # Documented differences (geometric numerators / arithmetic capture in PA).
    assert val(rep, "information_ratio") != pytest.approx(ref["information_ratio_pa"])
    assert val(rep, "active_return") != pytest.approx(ref["active_premium_pa"])
    assert val(rep, "upside_capture") != pytest.approx(ref["up_capture_pa"])
    assert val(rep, "downside_capture") != pytest.approx(ref["down_capture_pa"])

    # PA capture = ratio of summed returns, with zero-benchmark periods counted as "down".
    fund, bench = rep.returns_frame(), fixture_series("benchmark_case_benchmark")
    f = fund.set_axis(fund.index.to_period("M"))
    b = bench.set_axis(bench.index.to_period("M"))
    f, b = f.align(b, join="inner")
    up, down = b > 0, b <= 0
    assert ref["up_capture_pa"] == pytest.approx(f[up].sum() / b[up].sum(), **TOL)
    assert ref["down_capture_pa"] == pytest.approx(f[down].sum() / b[down].sum(), **TOL)

    # PA Treynor = geometric annualized return / beta; OpenFactsheet uses the arithmetic mean.
    geometric = float((1 + f).prod() ** (12 / len(f)) - 1)
    assert ref["treynor_ratio_pa"] == pytest.approx(geometric / ref["beta"], **TOL)
    assert val(rep, "treynor_ratio") == pytest.approx(f.mean() * 12 / ref["beta"], **TOL)
    assert val(rep, "treynor_ratio") != pytest.approx(ref["treynor_ratio_pa"])
