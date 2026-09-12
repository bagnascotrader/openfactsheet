"""Variance ratio, Lo (2002) Sharpe adjustment and profit factor (decision 0029)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.stattools import acf

import openfactsheet as ofs
from openfactsheet.diagnostics.autocorrelation import (
    autocorrelations,
    variance_ratio,
    variance_ratio_standard_error,
)
from tests.conftest import fixture_series, monthly


def _lo_eta_ar1(phi: float, q: int) -> float:
    """Lo (2002), eq. (33): eta(q) for an AR(1) with coefficient phi."""
    inner = q + 2 * phi / (1 - phi) * (q - (1 - phi**q) / (1 - phi))
    return q / math.sqrt(inner)


@pytest.mark.parametrize("phi", [-0.3, 0.0, 0.2, 0.5, 0.8])
@pytest.mark.parametrize("q", [4, 12, 52])
def test_variance_ratio_matches_lo_closed_form_for_ar1(phi: float, q: int) -> None:
    rho = np.array([phi**k for k in range(1, q)])
    eta = math.sqrt(q / variance_ratio(rho, q))
    assert eta == pytest.approx(_lo_eta_ar1(phi, q), rel=1e-12)


def test_variance_ratio_standard_error_matches_lo_mackinlay() -> None:
    # Lo & MacKinlay (1988): asymptotic variance 2(2q - 1)(q - 1) / (3q) of sqrt(n)(VR - 1).
    n, q = 240, 12
    k = np.arange(1, q)
    via_weights = math.sqrt(4 * np.sum((1 - k / q) ** 2) / n)
    assert variance_ratio_standard_error(n, q) == pytest.approx(via_weights, rel=1e-12)


def test_autocorrelations_match_statsmodels() -> None:
    r = fixture_series("monthly_fund_10y").to_numpy()
    rho = autocorrelations(r, 11)
    assert rho is not None
    np.testing.assert_allclose(rho, acf(r, nlags=11, fft=False, adjusted=False)[1:], rtol=1e-12)


@pytest.mark.parametrize("fixture", ["monthly_fund_10y", "smoothed_hedge_fund", "negative_fund"])
def test_adjusted_sharpe_identity(fixture: str) -> None:
    rep = ofs.analyze(fixture_series(fixture))
    sr = rep.metrics["sharpe_ratio"].value
    adj = rep.metrics["sharpe_ratio_autocorrelation_adjusted"]
    vr = rep.metrics["variance_ratio_1y"].value
    assert sr is not None
    assert adj.value is not None
    assert vr is not None
    # With q = P, eta = sqrt(q / VR), so the adjusted ratio is SR / sqrt(VR).
    assert adj.value == pytest.approx(sr / math.sqrt(vr), rel=1e-12)
    assert adj.details["eta"] == pytest.approx(math.sqrt(12 / vr), rel=1e-12)
    assert adj.details["sqrt_q"] == pytest.approx(math.sqrt(12))


def test_smoothed_fund_sharpe_is_lowered() -> None:
    rep = ofs.analyze(fixture_series("smoothed_hedge_fund"))
    sr = rep.metrics["sharpe_ratio"].value
    adj = rep.metrics["sharpe_ratio_autocorrelation_adjusted"]
    vr = rep.metrics["variance_ratio_1y"]
    assert sr is not None
    assert adj.value is not None
    assert adj.value < sr
    assert vr.value is not None
    assert vr.value > 1.0
    assert vr.status == "supplementary"
    assert vr.details["p_value"] < 0.05
    context = rep.interpretations["sharpe_ratio_autocorrelation_adjusted"].context
    assert any("persist" in c for c in context)


def test_variance_ratio_z_and_p() -> None:
    rep = ofs.analyze(fixture_series("monthly_fund_10y"))
    m = rep.metrics["variance_ratio_1y"]
    se = variance_ratio_standard_error(120, 12)
    assert m.details["standard_error"] == pytest.approx(se)
    assert m.details["z_statistic"] == pytest.approx((m.value - 1) / se)  # type: ignore[operator]
    assert 0.0 <= m.details["p_value"] <= 1.0


def test_needs_two_years() -> None:
    rep = ofs.analyze(monthly(list(np.linspace(-0.02, 0.03, 23))))
    for mid in ("variance_ratio_1y", "sharpe_ratio_autocorrelation_adjusted"):
        m = rep.metrics[mid]
        assert m.value is None
        assert "24 observations" in (m.reason or "")


def test_yearly_data_has_no_within_year_horizon() -> None:
    s = pd.Series(
        [0.08, -0.12, 0.2, 0.05, 0.11, -0.03],
        index=pd.date_range("2015-12-31", periods=6, freq="YE"),
    )
    rep = ofs.analyze(s)
    m = rep.metrics["variance_ratio_1y"]
    assert m.status == "not_applicable"
    assert "single period" in (m.reason or "")


def test_undated_data_is_not_applicable() -> None:
    rep = ofs.analyze(list(np.linspace(-0.02, 0.03, 40)))
    assert rep.metrics["variance_ratio_1y"].status == "not_applicable"
    assert rep.metrics["sharpe_ratio_autocorrelation_adjusted"].status == "not_applicable"


def test_constant_returns() -> None:
    rep = ofs.analyze(monthly([0.01] * 36))
    assert rep.metrics["variance_ratio_1y"].status == "not_applicable"
    assert rep.metrics["sharpe_ratio_autocorrelation_adjusted"].status == "not_applicable"


def test_profit_factor() -> None:
    r = [0.03, -0.01, 0.0, 0.02, -0.02, 0.01]
    rep = ofs.analyze(monthly(r))
    assert rep.metrics["profit_factor"].value == pytest.approx(0.06 / 0.03)
    gpr = rep.metrics["gain_to_pain_ratio"].value
    assert gpr is not None
    assert rep.metrics["profit_factor"].value == pytest.approx(1 + gpr)
    no_loss = ofs.analyze(monthly([0.01, 0.02, 0.0]))
    assert no_loss.metrics["profit_factor"].status == "not_applicable"
