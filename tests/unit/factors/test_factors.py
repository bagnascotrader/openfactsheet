"""Factor analysis (decision 0028): input, alignment, estimation edge cases, policy."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

import openfactsheet as ofs
from openfactsheet.exceptions import FactorAlignmentError, InputError
from openfactsheet.factors.data import load_factor_set
from openfactsheet.factors.models import recognize_model
from openfactsheet.factors.regressions import hac_lags
from openfactsheet.policy.applicability import NO_FACTORS_REASON
from tests.conftest import FIXTURES, fixture_series

FACTOR_METRICS = (
    "factor_alpha",
    "factor_alpha_t_statistic",
    "factor_r_squared",
    "factor_residual_volatility",
)


def _dates(n: int, start: str = "2015-01-31") -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="ME")


def _synthetic(n: int = 72, seed: int = 1, noise: float = 0.01) -> tuple[pd.Series, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    f1 = rng.normal(0.005, 0.04, n)
    f2 = rng.normal(0.0, 0.02, n)
    y = 0.002 + 0.8 * f1 - 0.3 * f2 + noise * rng.standard_normal(n)
    idx = _dates(n)
    return pd.Series(y, index=idx), pd.DataFrame({"MKT": f1, "F2": f2}, index=idx)


def test_no_factors_every_factor_metric_not_applicable() -> None:
    rep = ofs.analyze(fixture_series("monthly_fund_10y"))
    assert rep.factor_analysis is None
    for mid in FACTOR_METRICS:
        m = rep.metrics[mid]
        assert m.status == "not_applicable"
        assert m.reason == NO_FACTORS_REASON
    assert "No factor returns were supplied" in rep.summary()
    assert json.loads(rep.to_json())["factor_analysis"] is None


def test_percent_factors_with_rf_are_scaled_jointly() -> None:
    fs = load_factor_set(FIXTURES / "factor_case_factors.csv")
    assert fs.return_scale == "detected_percent"
    assert fs.names == ("Mkt-RF", "SMB", "HML")
    assert fs.risk_free is not None
    # RF is tiny in percent (~0.15) and would look decimal on its own; it follows the factors.
    assert float(np.max(fs.risk_free.values)) < 0.01
    assert fs.factors["HML"].n == 131  # one missing value dropped, never filled
    assert "One scale is applied to every factor column and to the risk-free column" in (
        fs.return_scale_evidence
    )


def test_declared_scale_applies_to_factors() -> None:
    fund, factors = _synthetic()
    rep = ofs.analyze(fund * 100, factors=factors * 100, return_scale="percent")
    assert rep.factor_analysis is not None
    assert rep.factor_analysis.return_scale == "declared_percent"
    ref = ofs.analyze(fund, factors=factors)
    assert rep.metrics["factor_alpha"].value == pytest.approx(ref.metrics["factor_alpha"].value)


def test_rf_is_subtracted_only_when_supplied() -> None:
    fund, factors = _synthetic()
    rf = pd.Series(0.001, index=factors.index)
    with_rf = ofs.analyze(fund, factors=factors.assign(RF=rf))
    without = ofs.analyze(fund, factors=factors)
    a_rf = with_rf.metrics["factor_alpha"].details["per_period"]
    a0 = without.metrics["factor_alpha"].details["per_period"]
    assert a_rf == pytest.approx(a0 - 0.001)
    assert with_rf.factor_analysis is not None
    assert "RF" in with_rf.factor_analysis.dependent
    assert without.factor_analysis is not None
    assert "risk-free rate 0%" in without.factor_analysis.dependent


def test_recovers_known_loadings() -> None:
    fund, factors = _synthetic(n=240, noise=0.002)
    rep = ofs.analyze(fund, factors=factors)
    fit = rep.factor_analysis.fit  # type: ignore[union-attr]
    assert fit is not None
    assert fit.loadings[0].estimate == pytest.approx(0.8, abs=0.02)
    assert fit.loadings[1].estimate == pytest.approx(-0.3, abs=0.03)
    assert fit.alpha.estimate == pytest.approx(0.002, abs=0.0005)
    assert rep.metrics["factor_r_squared"].value > 0.95  # type: ignore[operator]


def test_alignment_drops_missing_periods_and_discloses_them() -> None:
    fund, factors = _synthetic()
    factors = factors.iloc[6:]  # factors start six months after the fund
    rep = ofs.analyze(fund, factors=factors)
    fa = rep.factor_analysis
    assert fa is not None
    assert fa.alignment.aligned_observations == 66
    assert fa.alignment.fund_only_periods == 6
    assert any("never filled" in w for w in fa.alignment.warnings)
    assert rep.metrics["factor_alpha"].observations == 66


def test_low_coverage_caps_confidence() -> None:
    fund, factors = _synthetic(n=120)
    rep = ofs.analyze(fund, factors=factors.iloc[:96])  # 80% of the fund history
    alpha = rep.metrics["factor_alpha"]
    assert alpha.confidence in ("moderate", "low")
    assert any("overlap only 80%" in w for w in alpha.warnings)


def test_frequency_mismatch_is_an_error() -> None:
    fund, _ = _synthetic()
    quarterly = pd.DataFrame(
        {"MKT": np.linspace(-0.02, 0.02, 24)},
        index=pd.date_range("2015-03-31", periods=24, freq="QE"),
    )
    with pytest.raises(FactorAlignmentError):
        ofs.analyze(fund, factors=quarterly)


def test_only_rf_column_is_rejected() -> None:
    fund, factors = _synthetic()
    with pytest.raises(InputError):
        ofs.analyze(fund, factors=pd.DataFrame({"RF": 0.001}, index=factors.index))


def test_constant_factor_is_not_identified() -> None:
    fund, factors = _synthetic()
    rep = ofs.analyze(fund, factors=factors.assign(F2=0.01))
    for mid in FACTOR_METRICS:
        assert rep.metrics[mid].status == "not_applicable"
        assert "constant" in (rep.metrics[mid].reason or "")
    assert rep.factor_analysis is not None
    assert rep.factor_analysis.fit is None
    assert "constant" in (rep.factor_analysis.reason or "")


def test_collinear_factors_are_not_identified() -> None:
    fund, factors = _synthetic()
    rep = ofs.analyze(fund, factors=factors.assign(F3=2 * factors["MKT"] - factors["F2"]))
    assert rep.metrics["factor_alpha"].status == "not_applicable"
    assert "collinear" in (rep.metrics["factor_alpha"].reason or "")


def test_too_few_observations_is_insufficient_data() -> None:
    fund, factors = _synthetic(n=3)
    rep = ofs.analyze(fund, factors=factors)  # k = 2 needs at least 4
    m = rep.metrics["factor_alpha"]
    assert m.status == "insufficient_data"
    assert "at least 4 aligned observations" in (m.reason or "")


def test_exact_fit_has_no_t_statistic() -> None:
    fund, factors = _synthetic(noise=0.0)
    rep = ofs.analyze(fund, factors=factors)
    assert rep.metrics["factor_alpha"].value == pytest.approx(0.002 * 12)
    t = rep.metrics["factor_alpha_t_statistic"]
    assert t.status == "not_applicable"
    assert "exactly" in (t.reason or "")
    assert rep.metrics["factor_r_squared"].value == 1.0
    assert rep.metrics["factor_residual_volatility"].value == 0.0


def test_fund_equal_to_a_factor_is_an_exact_fit() -> None:
    fund, factors = _synthetic()
    rep = ofs.analyze(factors["MKT"].rename("fund"), factors=factors)
    fit = rep.factor_analysis.fit  # type: ignore[union-attr]
    assert fit is not None
    assert fit.loadings[0].estimate == pytest.approx(1.0)
    assert fit.alpha.t_statistic is None
    del fund


def test_constant_fund() -> None:
    _, factors = _synthetic()
    rep = ofs.analyze(pd.Series(0.004, index=factors.index), factors=factors)
    assert rep.metrics["factor_alpha"].value == pytest.approx(0.048)
    assert rep.metrics["factor_r_squared"].status == "not_applicable"
    assert rep.metrics["factor_alpha_t_statistic"].status == "not_applicable"


def test_smoothed_returns_lower_confidence() -> None:
    fund = fixture_series("smoothed_hedge_fund")
    rng = np.random.default_rng(7)
    factors = pd.DataFrame({"MKT": rng.normal(0.005, 0.04, fund.size)}, index=fund.index)
    rep = ofs.analyze(fund, factors=factors)
    alpha = rep.metrics["factor_alpha"]
    assert alpha.confidence == "low"
    assert any("Asness" in w for w in alpha.warnings)


def test_undated_pair_aligned_by_position_with_warning() -> None:
    fund, factors = _synthetic(n=40)
    rep = ofs.analyze(fund.to_numpy(), factors=factors.reset_index(drop=True), frequency="monthly")
    fa = rep.factor_analysis
    assert fa is not None
    assert fa.alignment.alignment_method.startswith("by position")
    assert any("paired by position" in w for w in rep.metrics["factor_alpha"].warnings)


def test_renderers_and_json_include_loadings() -> None:
    rep = ofs.analyze(
        fixture_series("factor_case_fund"), factors=FIXTURES / "factor_case_factors.csv"
    )
    for text in (rep.summary(), rep.to_markdown(), rep.to_html()):
        assert "Fama-French three-factor model" in text
        assert "Mkt-RF" in text
        assert "alpha (per period)" in text
    data = json.loads(rep.to_json())
    fit = data["factor_analysis"]["fit"]
    assert [c["name"] for c in fit["loadings"]] == ["Mkt-RF", "SMB", "HML"]
    assert data["provenance"]["factor_names"] == ["Mkt-RF", "SMB", "HML"]
    assert len(data["provenance"]["factors_sha256"]) == 64
    assert "NaN" not in rep.to_json()
    # The 14-section structure is unchanged.
    assert "\n14. ASSUMPTIONS & CAVEATS" in rep.summary()
    assert "\n15. " not in rep.summary()


def test_compare_uses_identical_factors() -> None:
    fund, factors = _synthetic()
    other = fund * 0.5 + 0.001
    cmp = ofs.compare({"A": fund, "B": other}, factors=factors)
    fits = [r.factor_analysis for r in cmp.reports.values()]
    assert all(f is not None and f.fit is not None for f in fits)
    assert fits[0].factor_names == fits[1].factor_names  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("names", "label"),
    [
        (("Mkt-RF",), "CAPM (single market factor)"),
        (("Mkt-RF", "SMB", "HML"), "Fama-French three-factor model"),
        (("MKT_RF", "SMB", "HML", "UMD"), "Carhart four-factor model"),
        (("Mkt-RF", "SMB", "HML", "RMW", "CMA"), "Fama-French five-factor model"),
        (
            ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"),
            "Fama-French five-factor model with momentum",
        ),
        (("Mkt-RF", "Credit"), "Custom factor model (2 factors)"),
        (("Carry",), "Custom factor model (1 factor)"),
    ],
)
def test_recognize_model(names: tuple[str, ...], label: str) -> None:
    assert recognize_model(names) == label


@pytest.mark.parametrize(
    ("m", "lags"), [(12, 2), (36, 3), (60, 3), (107, 4), (120, 4), (240, 4), (600, 5)]
)
def test_hac_lag_rule(m: int, lags: int) -> None:
    assert hac_lags(m) == lags
