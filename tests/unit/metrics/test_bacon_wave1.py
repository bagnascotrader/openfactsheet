"""Bacon Wave 1 monthly measures (decision 0036): hand computations and edge cases.

gini_mean_difference, relative_mean_difference, skewness_kurtosis_ratio,
bias_ratio and volatility_skewness.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest
from scipy import stats

import openfactsheet as ofs
from tests.conftest import monthly

WAVE1 = (
    "gini_mean_difference",
    "relative_mean_difference",
    "skewness_kurtosis_ratio",
    "bias_ratio",
    "volatility_skewness",
)


def v(report: ofs.FactsheetReport, mid: str) -> float:
    value = report.metrics[mid].value
    assert value is not None, report.metrics[mid].reason
    return value


def brute_force_md(r: np.ndarray) -> float:
    """Quadratic reference: mean |r_i - r_j| over the n(n-1) ordered pairs i != j."""
    n = len(r)
    total = sum(abs(a - b) for a, b in itertools.permutations(r.tolist(), 2))
    return total / (n * (n - 1))


def order_statistic_md(r: np.ndarray) -> float:
    """Bacon's sorted form: 2 / (n(n-1)) * sum_k (2k - n - 1) r_(k)."""
    n = len(r)
    k = np.arange(1, n + 1)
    return float(2.0 * np.sum((2 * k - n - 1) * np.sort(r)) / (n * (n - 1)))


# --- Hardcoded fixture, values computed by hand -------------------------------------

SMALL = [0.01, -0.02, 0.03, 0.0]


def test_small_fixture_by_hand() -> None:
    rep = ofs.analyze(monthly(SMALL))
    # Pairs: .03 .02 .01 .05 .02 .03 -> sum 0.16; MD = 2 * 0.16 / (4 * 3).
    assert v(rep, "gini_mean_difference") == pytest.approx(0.32 / 12, rel=1e-12)
    # Mean 0.005.
    assert v(rep, "relative_mean_difference") == pytest.approx(0.32 / 12 / 0.005, rel=1e-12)
    # UPM2 = (1e-4 + 9e-4) / 4, LPM2 = 4e-4 / 4 (the zero counts in neither).
    assert v(rep, "volatility_skewness") == pytest.approx(2.5, rel=1e-12)
    # s = sqrt(1.3e-3 / 3) = 0.0208; 0 <= r <= s: {0.01, 0}; -s <= r <= 0: {-0.02, 0}.
    assert v(rep, "bias_ratio") == pytest.approx(2 / 3, rel=1e-12)
    br = rep.metrics["bias_ratio"].details
    assert br["count_0_to_s"] == 2
    assert br["count_minus_s_to_0"] == 2
    assert br["zero_returns_counted_both_sides"] == 1


# --- W1.1 Gini mean difference --------------------------------------------------------


@pytest.mark.parametrize("n", [2, 3, 5, 12, 37, 120])
def test_gmd_sorted_matches_brute_force(n: int) -> None:
    rng = np.random.default_rng(n)
    r = rng.normal(0.005, 0.04, n)
    expected = brute_force_md(r)
    assert order_statistic_md(r) == pytest.approx(expected, rel=1e-10, abs=1e-15)
    rep = ofs.analyze(monthly(r.tolist()), return_scale="decimal")
    assert v(rep, "gini_mean_difference") == pytest.approx(expected, rel=1e-10, abs=1e-15)


def test_gmd_uses_pair_denominator_not_n_squared() -> None:
    r = np.array([0.02, -0.01])
    rep = ofs.analyze(monthly(r.tolist()))
    assert v(rep, "gini_mean_difference") == pytest.approx(0.03, rel=1e-12)  # not 0.015


def test_gmd_differs_from_mean_absolute_deviation() -> None:
    r = np.array(SMALL)
    rep = ofs.analyze(monthly(SMALL))
    mad = float(np.mean(np.abs(r - r.mean())))
    assert v(rep, "mean_absolute_deviation") == pytest.approx(mad)
    assert v(rep, "gini_mean_difference") != pytest.approx(mad)


def test_gmd_identical_returns_is_exactly_zero() -> None:
    rep = ofs.analyze(monthly([0.013] * 9))
    assert rep.metrics["gini_mean_difference"].value == 0.0


def test_gmd_single_observation_insufficient() -> None:
    rep = ofs.analyze(monthly([0.02]))
    for mid in WAVE1:
        assert rep.metrics[mid].status == "insufficient_data", mid


# --- W1.2 Relative mean difference ----------------------------------------------------


def test_rmd_keeps_the_sign_of_the_mean() -> None:
    r = np.array([-0.01, -0.02, 0.005, -0.03, 0.01])
    rep = ofs.analyze(monthly(r.tolist()))
    assert r.mean() < 0
    value = v(rep, "relative_mean_difference")
    assert value < 0
    assert value == pytest.approx(brute_force_md(r) / r.mean(), rel=1e-10)
    assert value != pytest.approx(brute_force_md(r) / abs(r.mean()))


def test_rmd_zero_mean_is_not_applicable() -> None:
    rep = ofs.analyze(monthly([0.02, -0.02, 0.01, -0.01]))
    m = rep.metrics["relative_mean_difference"]
    assert m.value is None
    assert m.status == "not_applicable"
    assert m.reason is not None
    assert "zero" in m.reason
    assert v(rep, "gini_mean_difference") > 0  # MD itself is defined


# --- W1.3 Skewness-kurtosis ratio -----------------------------------------------------


def test_skr_uses_pearson_kurtosis_from_canonical_estimators() -> None:
    rng = np.random.default_rng(3)
    r = rng.standard_t(4, 60) * 0.03
    rep = ofs.analyze(monthly(r.tolist()))
    g1 = stats.skew(r, bias=False)
    g2 = stats.kurtosis(r, fisher=True, bias=False)
    assert v(rep, "skewness") == pytest.approx(g1)
    assert v(rep, "excess_kurtosis") == pytest.approx(g2)
    assert v(rep, "skewness_kurtosis_ratio") == pytest.approx(g1 / (g2 + 3.0), rel=1e-12)
    assert v(rep, "skewness_kurtosis_ratio") != pytest.approx(g1 / g2)  # not excess kurtosis


def test_skr_non_positive_bias_corrected_kurtosis_is_not_applicable() -> None:
    # Two-point symmetric sample, n = 4: b2 = 1, G2 = -6, so G2 + 3 = -3.
    rep = ofs.analyze(monthly([-0.01, -0.01, 0.01, 0.01]))
    assert v(rep, "excess_kurtosis") == pytest.approx(-6.0)
    m = rep.metrics["skewness_kurtosis_ratio"]
    assert m.value is None
    assert m.status == "not_applicable"
    assert m.reason is not None
    assert "G2 + 3" in m.reason


def test_skr_needs_four_observations() -> None:
    rep = ofs.analyze(monthly([0.01, -0.02, 0.03]))
    assert rep.metrics["skewness"].value is not None
    assert rep.metrics["skewness_kurtosis_ratio"].status == "insufficient_data"


# --- W1.4 Bias ratio --------------------------------------------------------------------


def test_bias_ratio_closed_intervals_and_double_counted_zero() -> None:
    a = 0.125  # exact in binary: s of [-a, 0, a] is exactly a
    r = [-a, 0.0, a]
    assert float(np.std(r, ddof=1)) == a
    rep = ofs.analyze(monthly(r), return_scale="decimal")
    # Numerator {0, +s} = 2; denominator 1 + {-s, 0} = 3. Open bounds or a zero counted
    # once would give 1/2, 1 or 1/3 instead.
    assert v(rep, "bias_ratio") == pytest.approx(2 / 3, rel=1e-15)


def test_bias_ratio_excludes_returns_beyond_one_standard_deviation() -> None:
    r = np.array([0.05, 0.004, 0.003, -0.002, -0.06, 0.001])
    s = r.std(ddof=1)
    above = int(np.sum((r >= 0) & (r <= s)))
    below = int(np.sum((r >= -s) & (r <= 0)))
    assert (above, below) == (3, 1)
    rep = ofs.analyze(monthly(r.tolist()))
    assert v(rep, "bias_ratio") == pytest.approx(above / (1 + below), rel=1e-15)


def test_bias_ratio_all_zero_returns_is_not_applicable() -> None:
    m = ofs.analyze(monthly([0.0] * 12)).metrics["bias_ratio"]
    assert m.value is None
    assert m.status == "not_applicable"


def test_bias_ratio_near_zero_returns() -> None:
    r = np.array([1e-9, -2e-9, 3e-9, 0.0, -1e-9, 2e-9])
    s = r.std(ddof=1)
    expected = np.sum((r >= 0) & (r <= s)) / (1 + np.sum((r >= -s) & (r <= 0)))
    rep = ofs.analyze(monthly(r.tolist()), return_scale="decimal")
    assert v(rep, "bias_ratio") == pytest.approx(float(expected), rel=1e-15)


def test_bias_ratio_is_a_neutral_diagnostic() -> None:
    m = ofs.analyze(monthly(SMALL)).metrics["bias_ratio"]
    assert m.direction == "neutral"
    from openfactsheet.metrics.registry import get_metric

    retail = get_metric("bias_ratio").docs.retail
    assert "not a fraud detector" in retail


# --- W1.5 Volatility skewness ----------------------------------------------------------


def test_volatility_skewness_all_positive_is_not_applicable() -> None:
    m = ofs.analyze(monthly([0.01, 0.02, 0.005, 0.03])).metrics["volatility_skewness"]
    assert m.value is None
    assert m.status == "not_applicable"


def test_volatility_skewness_all_negative_is_zero() -> None:
    assert v(ofs.analyze(monthly([-0.01, -0.02, -0.005])), "volatility_skewness") == 0.0


def test_volatility_skewness_returns_at_the_target_count_on_neither_side() -> None:
    rep = ofs.analyze(monthly([0.0, 0.0, 0.01, -0.02]))
    assert v(rep, "volatility_skewness") == pytest.approx(0.25, rel=1e-12)
    # Zeros and gains only: no downside variance.
    assert (
        ofs.analyze(monthly([0.0, 0.01, 0.0, 0.02])).metrics["volatility_skewness"].status
        == "not_applicable"
    )


def test_volatility_skewness_has_no_square_roots() -> None:
    r = np.array([0.03, -0.01, 0.02, -0.02, 0.01])
    upm2 = np.mean(np.maximum(r, 0) ** 2)
    lpm2 = np.mean(np.maximum(-r, 0) ** 2)
    value = v(ofs.analyze(monthly(r.tolist())), "volatility_skewness")
    assert value == pytest.approx(upm2 / lpm2, rel=1e-12)
    su, sl = np.sqrt(upm2), np.sqrt(lpm2)
    assert value != pytest.approx((su - sl) / (su + sl))


# --- Total loss and missing observations ----------------------------------------------


def test_total_loss_return() -> None:
    r = np.array([0.01, -1.0, 0.02, 0.03, -0.01])
    rep = ofs.analyze(monthly(r.tolist()))
    md = brute_force_md(r)
    assert v(rep, "gini_mean_difference") == pytest.approx(md, rel=1e-12)
    assert v(rep, "relative_mean_difference") == pytest.approx(md / r.mean(), rel=1e-12)
    g1 = stats.skew(r, bias=False)
    g2 = stats.kurtosis(r, bias=False)
    assert v(rep, "skewness_kurtosis_ratio") == pytest.approx(g1 / (g2 + 3), rel=1e-12)
    lpm2 = np.mean(np.maximum(-r, 0) ** 2)
    assert v(rep, "volatility_skewness") == pytest.approx(
        np.mean(np.maximum(r, 0) ** 2) / lpm2, rel=1e-12
    )
    s = r.std(ddof=1)
    assert v(rep, "bias_ratio") == pytest.approx(
        np.sum((r >= 0) & (r <= s)) / (1 + np.sum((r >= -s) & (r <= 0)))
    )


def test_missing_month_is_dropped_not_filled() -> None:
    values = [0.01, np.nan, 0.02, -0.01, 0.005, -0.03, 0.015]
    rep = ofs.analyze(monthly(values))
    kept = np.array([x for x in values if not np.isnan(x)])
    assert rep.metrics["gini_mean_difference"].observations == len(kept)
    assert v(rep, "gini_mean_difference") == pytest.approx(brute_force_md(kept), rel=1e-12)
    filled = np.nan_to_num(np.array(values))
    assert v(rep, "gini_mean_difference") != pytest.approx(brute_force_md(filled))


def test_no_annualization_or_period_dependence() -> None:
    """Per-period statistics: identical values whether the series is monthly or undated."""
    r = [0.01, -0.02, 0.015, 0.005, -0.01, 0.03, 0.02, -0.005]
    dated = ofs.analyze(monthly(r))
    undated = ofs.analyze(pd.Series(r))
    for mid in WAVE1:
        assert dated.metrics[mid].value == undated.metrics[mid].value, mid
