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
