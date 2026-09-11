from __future__ import annotations

import pytest

import openfactsheet as ofs
from openfactsheet.policy.defaults import CANONICAL_ASSUMPTIONS, canonical_methodology
from openfactsheet.policy.thresholds import MIN_DATA_POLICIES, get_policy
from tests.conftest import fixture_series, monthly


def test_methodology_is_versioned_and_immutable() -> None:
    m = ofs.methodology()
    assert m.version == ofs.METHODOLOGY_VERSION
    assert m.get("tail.var_confidence") == 0.95
    assert m.get("annualization.periods_per_year.monthly") == 12.0
    with pytest.raises(TypeError):
        m.conventions["return_type"] = "log"  # type: ignore[index]
    assert (
        m.to_dict()["conventions"]["risk_free"]["rate"]
        == CANONICAL_ASSUMPTIONS["risk_free"]["rate"]
    )


def test_methodology_is_embedded_in_every_report() -> None:
    rep = ofs.analyze(monthly([0.01, 0.02, -0.01]))
    assert rep.to_dict()["methodology"] == canonical_methodology().to_dict()
    assert all(m.methodology_version == ofs.METHODOLOGY_VERSION for m in rep.metrics)


@pytest.mark.parametrize(
    ("years", "expected"),
    [(None, "low"), (1.0, "low"), (3.5, "moderate"), (10.0, "high")],
)
def test_years_policy(years: float | None, expected: str) -> None:
    conf, _ = get_policy("ratio_standard").confidence(120, years)
    assert conf == expected


def test_tail_policy_counts_expected_tail_observations() -> None:
    p = get_policy("tail")
    assert p.confidence(60, 5.0, 0.05)[0] == "low"
    assert p.confidence(150, 12.5, 0.05)[0] == "moderate"
    assert p.confidence(250, 20.0, 0.05)[0] == "high"


def test_every_policy_has_description() -> None:
    for policy in MIN_DATA_POLICIES.values():
        assert policy.description
        assert policy.math_min_obs >= 1


def test_low_confidence_never_hides_value() -> None:
    rep = ofs.analyze(monthly([0.01, -0.02, 0.015, 0.005]))
    low = [m for m in rep.metrics if m.status == "low_confidence"]
    assert low
    assert all(m.value is not None for m in low)


def test_smoothing_lowers_confidence_of_volatility_based_metrics_only() -> None:
    rep = ofs.analyze(fixture_series("smoothed_hedge_fund"))
    assert rep.metrics["sharpe_ratio"].confidence == "low"
    assert rep.metrics["annualized_volatility"].confidence == "low"
    # Path statistics are not downgraded for smoothing.
    assert rep.metrics["max_drawdown"].confidence == "high"


def test_rf_assumption_is_disclosed() -> None:
    rep = ofs.analyze(fixture_series("monthly_fund_10y"))
    assert any(
        "Risk-free rate assumed to be 0%" in a for a in rep.metrics["sharpe_ratio"].assumptions
    )
    assert not any("Risk-free" in a for a in rep.metrics["max_drawdown"].assumptions)


def test_benchmark_overlap_warning() -> None:
    fund = monthly([0.01, 0.02, -0.01, 0.03, 0.0, 0.01, 0.02, -0.02, 0.01, 0.0])
    bench = monthly([0.01, 0.015, -0.02, 0.02, 0.005], start="2020-06-30")
    rep = ofs.analyze(fund, benchmark=bench)
    assert rep.benchmark_summary is not None
    assert rep.benchmark_summary.aligned_observations == 5
    assert any("overlaps only" in w for w in rep.metrics["beta"].warnings)
