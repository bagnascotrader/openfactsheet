"""pandas Series / DataFrame input."""

from __future__ import annotations

import re
from dataclasses import replace

import pandas as pd

from openfactsheet.exceptions import InputError
from openfactsheet.input.monthly_table import from_monthly_table, is_monthly_table
from openfactsheet.input.values import parse_cells
from openfactsheet.models.input import RawReturns
from openfactsheet.normalization.dates import coerce_dates

_DATE_NAMES = re.compile(r"^(date|dates|period|month|time|timestamp|as of|asof|day)$", re.I)
# Column headers that describe the data type rather than name the investment.
_GENERIC_VALUE_NAMES = frozenset(
    {"return", "returns", "ret", "rets", "r", "value", "values", "performance",
     "monthly return", "monthly returns", "daily return", "daily returns", "total return"}
)  # fmt: skip


def _is_generic(label: object) -> bool:
    text = re.sub(r"[%()\[\]]", "", str(label)).strip().lower()
    return text in _GENERIC_VALUE_NAMES


def from_series(
    series: pd.Series, name: str | None = None, source_type: str | None = None
) -> RawReturns:
    dates, notes = coerce_dates(series.index)
    values, hint = parse_cells(series.tolist())
    label = name or (str(series.name) if series.name is not None else "Returns")
    return RawReturns(
        values=values,
        dates=dates,
        name=label,
        source_type=source_type or "pandas.Series",
        percent_hint=hint,
        transformations=notes,
    )


def _looks_like_dates(col: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(col.dtype) or isinstance(col.dtype, pd.PeriodDtype):
        return True
    if pd.api.types.is_numeric_dtype(col.dtype):
        return False
    non_null = col.dropna()
    if non_null.empty:
        return False
    try:
        parsed = pd.to_datetime(non_null.astype(str), errors="coerce", format="mixed")
    except (ValueError, TypeError):
        return False
    return bool(parsed.notna().all())


def from_frame(
    frame: pd.DataFrame, name: str | None = None, source_type: str | None = None
) -> list[RawReturns]:
    """Interpret a DataFrame as one or more return series.

    Supported layouts:

    * wide monthly table (Year x Jan..Dec);
    * DatetimeIndex (or PeriodIndex) with one column per series;
    * a date column (named like ``date``/``period``/``month`` or fully parseable as
      dates) plus one column per series.
    """
    source = source_type or "pandas.DataFrame"
    if frame.empty:
        raise InputError("The supplied table is empty.")
    if is_monthly_table(frame):
        return [from_monthly_table(frame, name, source)]

    data = frame
    if not isinstance(frame.index, pd.DatetimeIndex | pd.PeriodIndex):
        date_col = None
        for col in frame.columns:
            if _DATE_NAMES.match(str(col).strip()) and _looks_like_dates(frame[col]):
                date_col = col
                break
        if date_col is None:
            first = frame.columns[0]
            if _looks_like_dates(frame[first]):
                date_col = first
        if date_col is not None:
            col_values = frame[date_col]
            idx: pd.Index
            if isinstance(col_values.dtype, pd.PeriodDtype):
                idx = pd.PeriodIndex(col_values)
            else:
                idx = pd.DatetimeIndex(pd.to_datetime(col_values.astype(str), format="mixed"))
            data = frame.drop(columns=[date_col]).set_axis(idx, axis=0)

    columns = list(data.columns)
    if not columns:
        raise InputError("No return columns found in the supplied table.")
    if data.columns.has_duplicates:
        dupes = sorted({str(c) for c in data.columns[data.columns.duplicated()]})
        raise InputError(f"Duplicate column names in the supplied table: {', '.join(dupes)}.")
    out: list[RawReturns] = []
    for col in columns:
        if name is not None and len(columns) == 1:
            label = name
        elif len(columns) == 1 and _is_generic(col):
            label = "Returns"  # the caller (e.g. a file loader) may supply a better name
        else:
            label = str(col)
        raw = from_series(data[col], name=label, source_type=source)
        if "%" in str(col):  # a header such as "Return (%)" labels the whole column
            raw = replace(raw, percent_hint=True)
        out.append(raw)
    return out
