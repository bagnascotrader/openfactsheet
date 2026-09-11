"""Observation-frequency inference from calendar spacing (decision 0002).

Calendar spacing is the primary evidence. Monthly, quarterly and yearly data
are compared by *calendar period* so that month-start and month-end dates, or
month-ends falling on weekends, are handled identically. The number of
observations is never used as evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd

from openfactsheet.exceptions import FrequencyInferenceError
from openfactsheet.models.input import ObservationFrequency
from openfactsheet.policy.annualization import periods_per_year

# Share of consecutive spacings that must equal exactly one period for a
# series to count as regular; the remaining spacings are gaps of whole periods,
# which are allowed but counted and disclosed as missing periods.
_REGULAR_SHARE = 0.5
# Share of daily spacings that must be 4 calendar days or less.
_DAILY_SHARE = 0.8


@dataclass(frozen=True)
class FrequencyInference:
    frequency: ObservationFrequency
    periods_per_year: float | None
    calendar_days: bool
    missing_expected_periods: int | None
    duplicate_periods: int
    evidence: str


def _period_steps(dates: pd.DatetimeIndex, per_year: int) -> npt.NDArray[np.int64]:
    years = np.asarray(dates.year, dtype=np.int64)
    months = np.asarray(dates.month, dtype=np.int64)
    if per_year == 12:
        idx = years * 12 + (months - 1)
    elif per_year == 4:
        idx = years * 4 + (months - 1) // 3
    else:
        idx = years
    return np.diff(idx)


def _classify_steps(
    steps: npt.NDArray[np.int64], label: str, unit: str
) -> tuple[bool, int, int, str]:
    """Return (regular, missing_periods, duplicate_periods, evidence)."""
    duplicates = int(np.sum(steps == 0))
    if duplicates:
        return (
            False,
            0,
            duplicates,
            f"{duplicates} pair(s) of observations fall in the same calendar {unit}; "
            f"spacing is not consistently {label}.",
        )
    share_one = float(np.mean(steps == 1)) if len(steps) else 0.0
    if share_one < _REGULAR_SHARE:
        return (
            False,
            0,
            0,
            f"Only {share_one:.0%} of spacings are exactly one {unit}; "
            "spacing is irregular or the frequency changes.",
        )
    missing = int(np.sum(steps - 1))
    evidence = f"{share_one:.0%} of consecutive observations are exactly one calendar {unit} apart"
    if missing:
        evidence += f"; {missing} expected {unit}(s) missing"
    return True, missing, 0, evidence + "."


def infer_frequency(dates: pd.DatetimeIndex) -> FrequencyInference:
    """Infer the observation frequency of sorted, unique period-end timestamps."""
    n = len(dates)
    if n < 2:
        return FrequencyInference(
            ObservationFrequency.UNKNOWN,
            None,
            False,
            None,
            0,
            "A single timestamp cannot establish observation spacing.",
        )

    day_gaps = np.asarray((dates[1:] - dates[:-1]).days, dtype=np.int64)
    median_gap = float(np.median(day_gaps))

    period_rules: tuple[tuple[float, float, ObservationFrequency, int, str], ...] = (
        (25, 35, ObservationFrequency.MONTHLY, 12, "month"),
        (80, 100, ObservationFrequency.QUARTERLY, 4, "quarter"),
        (300, 400, ObservationFrequency.YEARLY, 1, "year"),
    )
    for lo, hi, freq, per_year, unit in period_rules:
        if lo <= median_gap <= hi:
            steps = _period_steps(dates, per_year)
            regular, missing, dups, evidence = _classify_steps(steps, freq.value, unit)
            if regular:
                return FrequencyInference(freq, periods_per_year(freq), False, missing, 0, evidence)
            return FrequencyInference(
                ObservationFrequency.IRREGULAR, None, False, None, dups, evidence
            )

    if 5 <= median_gap <= 9:
        weeks = np.rint(day_gaps / 7.0).astype(np.int64)
        aligned = np.abs(day_gaps - 7 * weeks) <= 1
        if bool(np.all(aligned)) and bool(np.all(weeks >= 1)):
            regular, missing, dups, evidence = _classify_steps(weeks, "weekly", "week")
            if regular:
                return FrequencyInference(
                    ObservationFrequency.WEEKLY,
                    periods_per_year(ObservationFrequency.WEEKLY),
                    False,
                    missing,
                    0,
                    evidence,
                )
        return FrequencyInference(
            ObservationFrequency.IRREGULAR,
            None,
            False,
            None,
            0,
            "Median spacing is about one week but spacings are not consistent multiples of 7 days.",
        )

    if median_gap <= 4:
        weekend = bool(np.any(np.asarray(dates.dayofweek) >= 5))
        long_gaps = int(np.sum(day_gaps > 7))
        share_short = float(np.mean(day_gaps <= 4))
        if share_short < _DAILY_SHARE:
            return FrequencyInference(
                ObservationFrequency.IRREGULAR,
                None,
                False,
                None,
                0,
                f"Median spacing is daily but only {share_short:.0%} of gaps are 4 days or less.",
            )
        if weekend:
            missing = int(np.sum(day_gaps - 1))
            evidence = (
                "Daily spacing with weekend observations present: calendar-day series "
                f"(365 periods per year); {missing} calendar day(s) missing."
            )
            return FrequencyInference(
                ObservationFrequency.DAILY,
                periods_per_year(ObservationFrequency.DAILY, calendar_days=True),
                True,
                missing,
                0,
                evidence,
            )
        evidence = (
            "Daily spacing with no weekend observations: business-day series "
            "(252 periods per year). Missing days are not counted because exchange "
            "holidays are legitimate gaps"
        )
        evidence += f"; {long_gaps} gap(s) longer than 7 days." if long_gaps else "."
        return FrequencyInference(
            ObservationFrequency.DAILY,
            periods_per_year(ObservationFrequency.DAILY, calendar_days=False),
            False,
            None,
            0,
            evidence,
        )

    return FrequencyInference(
        ObservationFrequency.IRREGULAR,
        None,
        False,
        None,
        0,
        f"Median spacing of {median_gap:g} days matches no canonical frequency.",
    )


def parse_declared_frequency(value: str | ObservationFrequency) -> ObservationFrequency:
    if isinstance(value, ObservationFrequency):
        freq = value
    else:
        try:
            freq = ObservationFrequency(str(value).strip().lower())
        except ValueError as exc:
            allowed = ", ".join(f.value for f in ObservationFrequency if f.is_regular)
            raise FrequencyInferenceError(
                f"Unknown frequency {value!r}; declare one of: {allowed}."
            ) from exc
    if not freq.is_regular:
        raise FrequencyInferenceError(
            "Only a regular frequency (daily, weekly, monthly, quarterly, yearly) can be declared."
        )
    return freq
