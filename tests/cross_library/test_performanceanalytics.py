"""Cross-check against R PerformanceAnalytics 2.0.4 (committed reference JSON).

Regenerate references with ``Rscript validation/r/performanceanalytics_reference.R``.
Known convention differences are asserted explicitly, not hidden
(see docs/validation/reference_implementations.md).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
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


@pytest.mark.parametrize("fixture", SINGLE_FIXTURES)
def test_phase2_agreement(fixture: str, pa_reference: dict[str, Any]) -> None:
    ref = pa_reference[fixture]
    rep = ofs.analyze(fixture_series(fixture))

    assert val(rep, "kappa_3_ratio") == pytest.approx(ref["kappa_3"], **TOL)
    assert val(rep, "upside_potential_ratio") == pytest.approx(ref["upside_potential_full"], **TOL)
    # PA default method='subset' differs (documented, decision 0016).
    assert val(rep, "upside_potential_ratio") != pytest.approx(ref["upside_potential_subset"])
    assert val(rep, "semi_deviation") == pytest.approx(
        ref["semi_deviation_per_period"] * math.sqrt(12), **TOL
    )
    assert val(rep, "mean_absolute_deviation") == pytest.approx(
        ref["mean_absolute_deviation"], **TOL
    )
    assert val(rep, "downside_potential") == pytest.approx(ref["downside_potential"], **TOL)
    assert val(rep, "sterling_ratio") == pytest.approx(ref["sterling_ratio"], **TOL)
    # Burke: PA's own BurkeRatio uses runs of negative returns with a percent-input
    # scaling; OpenFactsheet agrees with the formula on PA's findDrawdowns depths.
    assert val(rep, "burke_ratio") == pytest.approx(ref["burke_from_find_drawdowns"], **TOL)
    assert val(rep, "burke_ratio") != pytest.approx(ref["burke_ratio_pa"])
    assert val(rep, "pain_ratio") == pytest.approx(ref["pain_ratio_from_drawdowns"], **TOL)
    assert val(rep, "gaussian_var_95") == pytest.approx(ref["var_gaussian_95"], **TOL)
    assert val(rep, "modified_var_95") == pytest.approx(ref["var_modified_95"], **TOL)

    # Statistical confidence.
    if ref["psr_ref0_with_kurtosis"] is None:
        # PerformanceAnalytics stops for a negative Sharpe ratio; OpenFactsheet reports the
        # probability (below 0.5) and marks MinTRL as not applicable.
        assert val(rep, "probabilistic_sharpe_ratio") < 0.5
        assert rep.metrics["minimum_track_record_length"].status == "not_applicable"
    else:
        assert val(rep, "probabilistic_sharpe_ratio") == pytest.approx(
            ref["psr_ref0_with_kurtosis"], **TOL
        )
        assert val(rep, "minimum_track_record_length") == pytest.approx(
            ref["min_trl_ref0_with_kurtosis"], **TOL
        )
        # Same variance formula: PA's (rounded, one-sided 95%) interval half-width equals
        # qnorm(0.95) x the per-period standard error.
        se_pp = rep.metrics["sharpe_ratio_standard_error"].details["standard_error_per_period"]
        assert ref["psr_ci_half_width_per_period"] == pytest.approx(1.6448536 * se_pp, abs=1e-4)
    jb = rep.metrics["jarque_bera_pvalue"]
    assert jb.details["statistic"] == pytest.approx(ref["jarque_bera_statistic"], **TOL)
    assert val(rep, "jarque_bera_pvalue") == pytest.approx(ref["jarque_bera_pvalue"], rel=1e-7)

    # Mean-return inference against R's t.test.
    se = rep.metrics["mean_return_standard_error"]
    assert se.details["ci_lower"] == pytest.approx(ref["t_test_ci_lower"], **TOL)
    assert se.details["ci_upper"] == pytest.approx(ref["t_test_ci_upper"], **TOL)
    assert se.details["t_statistic"] == pytest.approx(ref["t_test_statistic"], **TOL)
    assert se.details["p_value"] == pytest.approx(ref["t_test_pvalue"], rel=1e-7)


@pytest.mark.parametrize("fixture", SINGLE_FIXTURES)
def test_phase2b_agreement(fixture: str, pa_reference: dict[str, Any]) -> None:
    ref = pa_reference[fixture]
    rep = ofs.analyze(fixture_series(fixture))

    assert val(rep, "modified_es_95") == pytest.approx(ref["es_modified_95"], **TOL)
    assert val(rep, "geometric_mean_return") == pytest.approx(ref["mean_geometric"], **TOL)
    assert val(rep, "interquartile_range") == pytest.approx(ref["iqr"], **TOL)

    # Episode statistics rebuilt from PerformanceAnalytics' findDrawdowns table. PA counts
    # an episode still open at the end one period longer (length and recovery).
    def as_list(x: Any) -> list[Any]:  # jsonlite unboxes one-element vectors
        return list(x) if isinstance(x, list) else [x]

    depths = as_list(ref["episode_depths"])
    lengths = as_list(ref["episode_lengths"])
    recovery = as_list(ref["episode_recovery"])
    if ref["last_episode_open"]:
        lengths[-1] -= 1
        recovery = recovery[:-1]
    assert val(rep, "median_drawdown") == pytest.approx(float(np.median(depths)), **TOL)
    assert val(rep, "average_drawdown_duration") == pytest.approx(float(np.mean(lengths)), **TOL)
    assert val(rep, "max_peak_to_trough_duration") == max(as_list(ref["episode_peak_to_trough"]))
    # PA's "Conditional Drawdown" (CDD) is the 5% quantile over all findDrawdowns runs (the
    # drawdown episodes and the zero-return runs between them), inverted to a positive
    # number - not a conditional expectation of the drawdown path like cdar_95.
    runs = as_list(ref["all_run_returns"])
    assert ref["cdd_pa"] == pytest.approx(-float(np.quantile(runs, 0.05)), **TOL)
    assert val(rep, "cdar_95") != pytest.approx(-ref["cdd_pa"])
    if recovery:
        assert val(rep, "average_recovery_duration") == pytest.approx(
            float(np.mean(recovery)), **TOL
        )
    else:  # only an open episode: recovery time is unknown
        assert rep.metrics["average_recovery_duration"].status == "not_applicable"

    # Calendar years (complete years only) and rolling 12-month windows.
    years = {int(y): v for y, v in ref["calendar_year_returns"].items()}
    details = rep.metrics["positive_calendar_years_pct"].details
    ours = {int(y): v for y, v in details["calendar_year_returns"].items()}
    assert set(ours) == set(years)
    for y, v in years.items():
        assert ours[y] == pytest.approx(v, **TOL)
    assert val(rep, "best_calendar_year") == pytest.approx(max(years.values()), **TOL)
    assert val(rep, "worst_calendar_year") == pytest.approx(min(years.values()), **TOL)
    assert val(rep, "best_rolling_year") == pytest.approx(ref["rolling_year_max"], **TOL)
    assert val(rep, "worst_rolling_year") == pytest.approx(ref["rolling_year_min"], **TOL)
    assert val(rep, "positive_rolling_year_pct") == pytest.approx(
        ref["rolling_year_positive_share"], **TOL
    )
    assert (
        rep.metrics["positive_rolling_year_pct"].details["windows"] == ref["rolling_year_windows"]
    )


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


def test_benchmark_additions_agreement(pa_reference: dict[str, Any]) -> None:
    """Decision 0027: regime betas, batting averages, residual risk, appraisal ratio, M2."""
    ref = pa_reference["benchmark_case"]
    rep = ofs.analyze(
        fixture_series("benchmark_case_fund"), benchmark=fixture_series("benchmark_case_benchmark")
    )
    m = ref["aligned_observations"]

    # Direct agreement.
    assert val(rep, "bull_beta") == pytest.approx(ref["bull_beta"], **TOL)
    assert val(rep, "bear_beta") == pytest.approx(ref["bear_beta"], **TOL)
    assert val(rep, "timing_ratio") == pytest.approx(ref["timing_ratio"], **TOL)
    batting = rep.metrics["batting_average"].details
    assert batting["up_market_batting_average"] == pytest.approx(ref["up_percent_pa"], **TOL)
    assert batting["down_market_batting_average"] == pytest.approx(ref["down_percent_pa"], **TOL)
    assert val(rep, "m_squared") == pytest.approx(ref["modigliani_pa_per_period"] * 12, **TOL)
    assert val(rep, "residual_volatility") == pytest.approx(
        ref["residual_se_lm"] * math.sqrt(12), **TOL
    )

    # Documented differences: PA's SpecificRisk divides by m (not m - 2) and its appraisal
    # ratio uses Jensen's alpha from geometric annualized returns.
    assert val(rep, "residual_volatility") * math.sqrt((m - 2) / m) == pytest.approx(
        ref["specific_risk_pa"], **TOL
    )
    assert ref["appraisal_ratio_pa"] == pytest.approx(
        ref["jensen_alpha_pa"] / ref["specific_risk_pa"], **TOL
    )
    assert val(rep, "appraisal_ratio") == pytest.approx(
        val(rep, "alpha") / val(rep, "residual_volatility"), **TOL
    )
    assert val(rep, "appraisal_ratio") != pytest.approx(ref["appraisal_ratio_pa"])
