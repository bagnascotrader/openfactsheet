"""Wide monthly-return tables (years in rows, months in columns).

Typical factsheet layout::

           Jan    Feb   ...   Dec    YTD
    2022   1.2%  -0.3%  ...  0.8%   5.1%
    2023   ...

is reconstructed chronologically as ``2022-01-31: 0.012, 2022-02-28: -0.003, ...``.
Empty future cells are preserved as missing (and trimmed at the end), never
treated as zero. Annual total columns (YTD/Year/Total) are ignored for
calculation and recorded as such.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from openfactsheet.exceptions import InputError
from openfactsheet.input.values import parse_cells
from openfactsheet.models.input import RawReturns

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}  # fmt: skip
_YEAR_NAMES = {"year", "yr", "years", "fy"}


def _month_of(label: object) -> int | None:
    key = re.sub(r"[^a-z]", "", str(label).strip().lower())
    return _MONTHS.get(key)


def is_monthly_table(frame: pd.DataFrame) -> bool:
    months = {_month_of(c) for c in frame.columns} - {None}
    return len(months) >= 12


def _year_values(frame: pd.DataFrame) -> tuple[pd.Series, str | None]:
    for col in frame.columns:
        if str(col).strip().lower() in _YEAR_NAMES:
            return frame[col], str(col)
    index = frame.index
    return pd.Series(index, index=index), None


def from_monthly_table(frame: pd.DataFrame, name: str | None, source_type: str) -> RawReturns:
    month_cols: dict[int, object] = {}
    for col in frame.columns:
        m = _month_of(col)
        if m is not None:
            if m in month_cols:
                raise InputError(f"Monthly table has more than one column for month {m}.")
            month_cols[m] = col
    if sorted(month_cols) != list(range(1, 13)):
        raise InputError("Monthly table must have exactly one column for each of the 12 months.")

    years_raw, year_col = _year_values(frame)
    try:
        years = [int(float(str(y).strip())) for y in years_raw]
    except ValueError as exc:
        raise InputError(
            "Monthly table rows must be labelled with years (a 'Year' column or year index)."
        ) from exc
    if any(y < 1800 or y > 2200 for y in years):
        raise InputError(f"Implausible year labels in monthly table: {years}.")
    if len(set(years)) != len(years):
        raise InputError("Monthly table contains duplicate year rows.")

    ignored = [
        str(c)
        for c in frame.columns
        if _month_of(c) is None and (year_col is None or c != year_col)
    ]

    cells: list[object] = []
    dates: list[pd.Timestamp] = []
    for row_pos, year in enumerate(years):
        for month in range(1, 13):
            cells.append(frame[month_cols[month]].iloc[row_pos])
            dates.append(pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0))
    values, hint = parse_cells(cells)
    order = np.argsort(np.asarray(dates, dtype="datetime64[ns]"), kind="stable")
    values = values[order]
    index = pd.DatetimeIndex(np.asarray(dates, dtype="datetime64[ns]")[order])

    header_percent = any("%" in str(c) for c in frame.columns)
    transformations = ["reshaped wide monthly table (year x month) into a chronological series"]
    if ignored:
        transformations.append("ignored non-month columns for calculation: " + ", ".join(ignored))
    return RawReturns(
        values=values,
        dates=index,
        name=name or "Returns",
        source_type=f"{source_type} (monthly table)",
        percent_hint=True if header_percent else hint,
        transformations=tuple(transformations),
    )
