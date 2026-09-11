from __future__ import annotations

import pandas as pd
import pytest

from openfactsheet.exceptions import FrequencyInferenceError
from openfactsheet.models.input import ObservationFrequency as F
from openfactsheet.normalization.frequency import infer_frequency, parse_declared_frequency


@pytest.mark.parametrize(
    ("dates", "freq", "ppy"),
    [
        (pd.date_range("2020-01-31", periods=24, freq="ME"), F.MONTHLY, 12.0),
        (pd.date_range("2020-01-01", periods=24, freq="MS"), F.MONTHLY, 12.0),
        (pd.date_range("2020-03-31", periods=12, freq="QE"), F.QUARTERLY, 4.0),
        (pd.date_range("2010-12-31", periods=10, freq="YE"), F.YEARLY, 1.0),
        (pd.date_range("2020-01-03", periods=60, freq="W-FRI"), F.WEEKLY, 52.0),
        (pd.bdate_range("2020-01-01", periods=300), F.DAILY, 252.0),
        (pd.date_range("2020-01-01", periods=400, freq="D"), F.DAILY, 365.0),
    ],
)
def test_regular_frequencies(dates: pd.DatetimeIndex, freq: F, ppy: float) -> None:
    inf = infer_frequency(pd.DatetimeIndex(dates))
    assert inf.frequency is freq
    assert inf.periods_per_year == ppy


def test_business_month_ends_are_monthly() -> None:
    dates = pd.date_range("2020-01-31", periods=36, freq="BME")
    assert infer_frequency(dates).frequency is F.MONTHLY


def test_missing_months_counted() -> None:
    dates = pd.date_range("2020-01-31", periods=24, freq="ME").delete([5, 6, 15])
    inf = infer_frequency(dates)
    assert inf.frequency is F.MONTHLY
    assert inf.missing_expected_periods == 3


def test_many_observations_do_not_imply_daily() -> None:
    # 1000 monthly observations are still monthly.
    dates = pd.date_range("1920-01-31", periods=1000, freq="ME")
    assert infer_frequency(dates).frequency is F.MONTHLY


def test_irregular_spacing() -> None:
    dates = pd.DatetimeIndex(["2020-01-01", "2020-01-20", "2020-03-15", "2020-07-01", "2020-07-05"])
    inf = infer_frequency(dates)
    assert inf.frequency is F.IRREGULAR
    assert inf.periods_per_year is None


def test_two_observations_in_same_month_is_irregular() -> None:
    dates = pd.DatetimeIndex(["2020-01-01", "2020-01-31", "2020-02-29", "2020-03-31", "2020-04-30"])
    inf = infer_frequency(dates)
    assert inf.frequency is F.IRREGULAR
    assert inf.duplicate_periods == 1


def test_single_timestamp_is_unknown() -> None:
    assert infer_frequency(pd.DatetimeIndex(["2020-01-31"])).frequency is F.UNKNOWN


def test_declared_frequency_parsing() -> None:
    assert parse_declared_frequency("Monthly") is F.MONTHLY
    with pytest.raises(FrequencyInferenceError):
        parse_declared_frequency("fortnightly")
    with pytest.raises(FrequencyInferenceError):
        parse_declared_frequency("irregular")
