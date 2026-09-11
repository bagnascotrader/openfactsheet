"""CLAUDE.md section 31.1 edge cases, run across the whole metric registry.

Every case must produce a structured result for every metric: a finite value,
or no value plus a reason. Nothing may raise or return NaN/inf.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

import openfactsheet as ofs
from openfactsheet.metrics.registry import all_metrics, get_metric
from openfactsheet.policy.applicability import NO_BENCHMARK_REASON
from tests.conftest import monthly

CASES: dict[str, list[float]] = {
    "typical": [0.01, -0.02, 0.015, 0.005, -0.01, 0.03, 0.02, -0.005],
    "all_positive": [0.01, 0.02, 0.005, 0.03, 0.01, 0.002],
    "all_negative": [-0.01, -0.02, -0.005, -0.03, -0.01, -0.002],
    "constant_zero": [0.0] * 8,
    "constant_positive": [0.01] * 8,
    "single_observation": [0.02],
    "two_observations": [0.02, -0.01],
    "extreme_loss": [0.01, 0.02, -0.6, 0.05, 0.03, 0.01],
    "total_loss": [0.01, 0.02, -1.0, 0.05, 0.03],
}


_PRECHECK_REASONS = (NO_BENCHMARK_REASON, "Annualization requires", "The series contains returns")


def assert_structured(report: ofs.FactsheetReport) -> None:
    ids = [d.id for d in all_metrics()]
    assert [m.id for m in report.metrics] == ids  # compute-all: every metric, canonical order
    for m in report.metrics:
        if m.value is None:
            assert m.reason, f"{m.id} has neither value nor reason"
            assert m.status in ("not_applicable", "insufficient_data", "error")
            if m.status == "not_applicable" and not m.reason.startswith(_PRECHECK_REASONS):
                # Raised by the metric itself: the condition must be documented.
                assert get_metric(m.id).docs.undefined_when, f"{m.id}: document {m.reason!r}"
        else:
            assert math.isfinite(m.value), m.id
        assert m.status != "error", f"{m.id}: {m.reason}"
    report.to_json()  # serializes without NaN


@pytest.mark.parametrize("case", sorted(CASES))
def test_edge_case_is_structured(case: str) -> None:
    assert_structured(ofs.analyze(monthly(CASES[case])))


def test_constant_zero_identities() -> None:
    rep = ofs.analyze(monthly(CASES["constant_zero"]))
    assert rep.metrics["cumulative_return"].value == 0.0
    assert rep.metrics["volatility"].value == 0.0
    assert rep.metrics["max_drawdown"].value == 0.0
    sharpe = rep.metrics["sharpe_ratio"]
    assert sharpe.value is None
    assert sharpe.status == "not_applicable"
    assert sharpe.reason is not None
    assert "zero" in sharpe.reason


def test_all_positive_has_no_drawdown_and_undefined_downside_ratios() -> None:
    rep = ofs.analyze(monthly(CASES["all_positive"]))
    assert rep.metrics["max_drawdown"].value == 0.0
    assert rep.metrics["drawdown_count"].value == 0.0
    for mid in ("sortino_ratio", "calmar_ratio", "omega_ratio", "gain_to_pain_ratio"):
        assert rep.metrics[mid].status == "not_applicable", mid


def test_open_deepest_drawdown_is_flagged() -> None:
    rep = ofs.analyze(monthly([0.05, -0.2, 0.05, 0.02]))
    mdd = rep.metrics["max_drawdown"]
    assert mdd.details["recovered"] is False
    assert any("not recovered" in w for w in mdd.warnings)


def test_single_observation() -> None:
    rep = ofs.analyze(monthly(CASES["single_observation"]))
    assert rep.metrics["cumulative_return"].value == pytest.approx(0.02)
    assert rep.metrics["volatility"].status == "insufficient_data"
    # A single timestamp cannot establish frequency, so annualized metrics are not applicable.
    assert rep.metrics["cagr"].status == "not_applicable"


def test_total_loss() -> None:
    rep = ofs.analyze(monthly(CASES["total_loss"]))
    assert rep.metrics["cumulative_return"].value == pytest.approx(-1.0)
    assert rep.metrics["max_drawdown"].value == pytest.approx(-1.0)
    assert rep.metrics["cagr"].value == pytest.approx(-1.0)
    assert rep.diagnostics.total_loss
    assert any("-100%" in w for w in rep.metrics["max_drawdown"].warnings)


def test_nan_inside_series_is_structured() -> None:
    rep = ofs.analyze(monthly([0.01, np.nan, 0.02, -0.01, 0.005, 0.01]))
    assert_structured(rep)
    assert rep.input_summary.missing_values == 1
    assert any("missing" in w for w in rep.metrics["cagr"].warnings)


def test_undated_input_is_structured() -> None:
    assert_structured(ofs.analyze(CASES["typical"]))


def test_irregular_dates_are_structured() -> None:
    import pandas as pd

    idx = pd.DatetimeIndex(
        ["2020-01-01", "2020-01-20", "2020-03-15", "2020-07-01", "2020-07-05", "2020-12-01"]
    )
    rep = ofs.analyze(pd.Series(CASES["all_positive"], index=idx))
    assert_structured(rep)
    assert rep.metrics["sharpe_ratio"].status == "not_applicable"
