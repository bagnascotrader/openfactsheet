from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import openfactsheet as ofs
from openfactsheet.exceptions import FrequencyInferenceError, InputError
from tests.conftest import monthly


def test_caller_data_is_never_mutated() -> None:
    s = monthly([1.0, -2.0, 1.5, 0.5, 2.5, -1.0])
    before = s.copy()
    ofs.analyze(s)
    pd.testing.assert_series_equal(s, before)


def test_unsorted_dates_are_sorted_and_disclosed() -> None:
    s = monthly([0.01, -0.02, 0.015, 0.005]).iloc[[2, 0, 3, 1]]
    series = ofs.load(s)
    assert isinstance(series, ofs.ReturnSeries)
    assert series.dates is not None
    assert series.dates.is_monotonic_increasing
    assert series.input_diagnostics is not None
    assert not series.input_diagnostics.was_sorted
    assert "sorted" in " ".join(series.input_diagnostics.transformations)


def test_duplicate_dates_fail_early() -> None:
    idx = pd.DatetimeIndex(["2020-01-31", "2020-01-31", "2020-02-29"])
    with pytest.raises(InputError, match="duplicate"):
        ofs.analyze(pd.Series([0.01, 0.02, 0.03], index=idx))


def test_infinite_values_fail_early() -> None:
    with pytest.raises(InputError, match="infinite"):
        ofs.analyze(monthly([0.01, np.inf, 0.02]))


def test_empty_and_all_missing_fail() -> None:
    with pytest.raises(InputError):
        ofs.analyze([])
    with pytest.raises(InputError):
        ofs.analyze([np.nan, np.nan])


def test_missing_values_are_dropped_not_filled() -> None:
    s = monthly([np.nan, 0.01, 0.02, np.nan, -0.01, 0.03, np.nan])
    series = ofs.load(s)
    assert isinstance(series, ofs.ReturnSeries)
    d = series.input_diagnostics
    assert d is not None
    assert series.n == 4
    assert d.leading_missing_trimmed == 1
    assert d.trailing_missing_trimmed == 1
    assert d.missing_values == 1
    assert d.missing_expected_periods == 1  # the gap is visible in the calendar
    assert 0.0 not in series.values


def test_percent_series_converted_to_decimal() -> None:
    series = ofs.load(monthly([1.5, -0.8, 2.1, 3.0, -2.5, 0.7]))
    assert isinstance(series, ofs.ReturnSeries)
    np.testing.assert_allclose(series.values, [0.015, -0.008, 0.021, 0.03, -0.025, 0.007])
    assert series.return_scale == "detected_percent"


def test_undated_list_has_unknown_frequency_and_no_annualization() -> None:
    report = ofs.analyze([0.01, -0.02, 0.015, 0.005, -0.01, 0.03])
    assert report.returns.frequency is ofs.ObservationFrequency.UNKNOWN
    cagr = report.metrics["cagr"]
    assert cagr.status == "not_applicable"
    assert cagr.reason is not None
    assert "frequency" in cagr.reason
    assert report.metrics["cumulative_return"].value is not None


def test_declared_frequency_for_undated_values() -> None:
    report = ofs.analyze([0.01, -0.02, 0.015, 0.005, -0.01, 0.03], frequency="monthly")
    assert report.returns.periods_per_year == 12
    assert report.returns.frequency_source == "declared"
    assert any("declared" in w for w in report.metrics["cagr"].warnings)


def test_declared_frequency_must_match_dates() -> None:
    with pytest.raises(FrequencyInferenceError):
        ofs.analyze(monthly([0.01, 0.02, 0.03]), frequency="quarterly")


def test_declared_frequency_with_single_timestamp() -> None:
    s = pd.Series([0.01], index=pd.DatetimeIndex(["2020-01-31"]))
    series = ofs.load(s, frequency="monthly")
    assert isinstance(series, ofs.ReturnSeries)
    assert series.periods_per_year == 12
    assert series.frequency_source == "declared"


def test_float_index_is_not_read_as_dates() -> None:
    series = ofs.load(pd.Series([0.01, 0.02, -0.01], index=[0.5, 1.5, 2.5]))
    assert isinstance(series, ofs.ReturnSeries)
    assert series.dates is None


def test_timezone_aware_dates() -> None:
    idx = pd.date_range("2020-01-31", periods=4, freq="ME", tz="US/Eastern")
    series = ofs.load(pd.Series([0.01, 0.02, -0.01, 0.0], index=idx))
    assert isinstance(series, ofs.ReturnSeries)
    assert series.dates is not None
    assert series.dates.tz is None


def test_period_index() -> None:
    idx = pd.period_range("2020-01", periods=5, freq="M")
    series = ofs.load(pd.Series([0.01, 0.02, -0.01, 0.0, 0.03], index=idx))
    assert isinstance(series, ofs.ReturnSeries)
    assert series.frequency is ofs.ObservationFrequency.MONTHLY


def test_values_below_minus_one_are_flagged_not_clipped() -> None:
    report = ofs.analyze(monthly([0.01, -1.5, 0.02, 0.01, -0.02, 0.005]))
    assert report.returns.values[1] == -1.5
    assert report.diagnostics.impossible_return_count == 1
    assert report.metrics["max_drawdown"].status == "not_applicable"
    assert report.metrics["volatility"].value is not None
