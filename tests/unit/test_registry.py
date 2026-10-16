"""The registry is the single source of truth and must be fully documented (section 46)."""

from __future__ import annotations

import openfactsheet as ofs
from openfactsheet.metrics.registry import all_metrics
from openfactsheet.models.metric import CATEGORY_ORDER
from openfactsheet.policy.thresholds import MIN_DATA_POLICIES


def test_ids_unique_and_snake_case() -> None:
    ids = [d.id for d in all_metrics()]
    assert len(ids) == len(set(ids))
    assert all(i == i.lower() and " " not in i for i in ids)


def test_phase_one_catalog_is_complete() -> None:
    ids = {d.id for d in all_metrics()}
    required = {
        "cumulative_return", "cagr", "arithmetic_mean", "median_return", "volatility",
        "annualized_volatility", "downside_deviation", "sharpe_ratio", "sortino_ratio",
        "max_drawdown", "average_drawdown", "current_drawdown", "longest_drawdown_duration",
        "ulcer_index", "calmar_ratio", "martin_ratio", "omega_ratio", "skewness",
        "excess_kurtosis", "var_historical_95", "expected_shortfall_historical_95",
        "tail_ratio", "best_period", "worst_period", "positive_period_pct",
        "gain_to_pain_ratio", "autocorrelation_lag1", "zero_return_pct", "alpha", "beta",
        "correlation", "tracking_error", "information_ratio", "treynor_ratio",
        "upside_capture", "downside_capture",
        # Phase 2 (first increment)
        "kappa_3_ratio", "upside_potential_ratio", "burke_ratio", "sterling_ratio",
        "pain_ratio", "payoff_ratio", "semi_deviation", "downside_potential",
        "mean_absolute_deviation", "gaussian_var_95", "modified_var_95",
        "jarque_bera_pvalue", "probabilistic_sharpe_ratio", "sharpe_ratio_standard_error",
        "minimum_track_record_length", "mean_return_standard_error",
        # Phase 2 (second increment)
        "drawdown_at_risk_95", "cdar_95", "edar_95", "evar_95", "modified_es_95",
        "best_calendar_year", "worst_calendar_year", "positive_calendar_years_pct",
        "best_rolling_year", "worst_rolling_year", "positive_rolling_year_pct",
        "median_drawdown", "average_drawdown_duration", "max_peak_to_trough_duration",
        "average_recovery_duration", "recovery_factor", "geometric_mean_return",
        "interquartile_range",
        # Bacon Wave 1 (decision 0036)
        "gini_mean_difference", "relative_mean_difference", "skewness_kurtosis_ratio",
        "bias_ratio", "volatility_skewness",
    }  # fmt: skip
    assert required <= ids


def test_every_metric_is_fully_documented() -> None:
    for d in all_metrics():
        docs = d.docs
        for field in (
            "measures",
            "formula",
            "inputs",
            "retail",
            "institutional",
            "minimum_data",
            "convention",
        ):
            assert getattr(docs, field).strip(), f"{d.id}.{field}"
        assert docs.misleading_when, d.id
        assert docs.formula_latex.strip(), f"{d.id} needs an exact LaTeX formula"
        assert docs.references, d.id
        assert d.min_data_policy in MIN_DATA_POLICIES
        assert d.category in CATEGORY_ORDER


def test_benchmark_metrics_flagged() -> None:
    for d in all_metrics():
        assert d.requires_benchmark == (d.category == "benchmark"), d.id


def test_metric_catalog_frame() -> None:
    cat = ofs.metric_catalog()
    assert len(cat) == len(all_metrics())
    assert {"name", "category", "formula", "minimum_data", "references"} <= set(cat.columns)
