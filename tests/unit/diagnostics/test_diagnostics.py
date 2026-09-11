from __future__ import annotations

import numpy as np

import openfactsheet as ofs
from openfactsheet.diagnostics.outliers import robust_outlier_count
from openfactsheet.diagnostics.smoothing import assess_smoothing
from openfactsheet.diagnostics.stale_returns import longest_identical_run, zero_return_count
from tests.conftest import fixture_series, monthly


def ids(report: ofs.FactsheetReport) -> set[str]:
    return {f.id for f in report.diagnostics.findings}


def test_clean_series_has_no_material_findings() -> None:
    rep = ofs.analyze(fixture_series("monthly_fund_10y"))
    assert not rep.diagnostics.findings_by_severity("critical")
    assert rep.diagnostics.smoothing_risk == "none"


def test_stale_returns_flagged() -> None:
    values = [0.01, 0.0, 0.0, 0.0, 0.02, -0.01, 0.0, 0.015, 0.0, 0.01, -0.005, 0.0]
    rep = ofs.analyze(monthly(values))
    assert {"excessive_zero_returns", "repeated_returns"} <= ids(rep)
    assert rep.diagnostics.zero_return_count == 6
    assert rep.diagnostics.longest_identical_run == 3


def test_outliers_flagged_not_removed() -> None:
    rng = np.random.default_rng(0)
    values = list(rng.normal(0.005, 0.01, 60))
    values[30] = 0.35
    rep = ofs.analyze(monthly(values))
    assert "suspicious_large_returns" in ids(rep)
    assert rep.returns.n == 60


def test_short_history_flagged() -> None:
    assert "very_short_history" in ids(ofs.analyze(monthly([0.01, 0.02, -0.01])))
    assert "short_history" in ids(ofs.analyze(monthly([0.01, 0.02, -0.01] * 8)))


def test_missing_periods_flagged() -> None:
    s = monthly([0.01, 0.02, -0.01, 0.03, 0.0, 0.01]).drop(monthly([0] * 6).index[2])
    rep = ofs.analyze(s)
    assert "missing_periods" in ids(rep)


def test_smoothing_rule() -> None:
    assert assess_smoothing(0.5, 100)[0] == "high"
    assert assess_smoothing(0.2, 100)[0] == "moderate"
    assert assess_smoothing(0.05, 100)[0] == "none"
    assert assess_smoothing(0.5, 8)[0] == "not_assessable"
    assert assess_smoothing(None, 100)[0] == "not_assessable"
    # Large autocorrelation that is not significant at 5% (z = 0.35 * sqrt(30) = 1.92) is
    # "moderate", not "high"; at n = 20 (z = 1.57) it is not flagged at all.
    assert assess_smoothing(0.35, 30)[0] == "moderate"
    assert assess_smoothing(0.35, 20)[0] == "none"


def test_helpers() -> None:
    assert zero_return_count(np.array([0.0, 0.1, 0.0])) == 2
    assert longest_identical_run(np.array([0.1, 0.1, 0.2, 0.2, 0.2])) == 3
    assert robust_outlier_count(np.array([0.01, 0.02, 0.0, 0.01, 0.02, 0.5]), 5.0) == 1
