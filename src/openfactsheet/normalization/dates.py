"""Timestamp coercion helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd

from openfactsheet.exceptions import InputError


def coerce_dates(index: Any) -> tuple[pd.DatetimeIndex | None, tuple[str, ...]]:
    """Convert an index-like object to a naive ``DatetimeIndex`` if it represents dates.

    Returns ``(None, ())`` for non-date indexes (e.g. a default ``RangeIndex``).
    Period indexes are converted to period-end timestamps; timezone-aware
    timestamps are converted to naive local wall time (recorded as a transformation).
    """
    notes: list[str] = []
    if index is None:
        return None, ()
    if isinstance(index, pd.PeriodIndex):
        return pd.DatetimeIndex(index.to_timestamp(how="end").normalize()), (
            "period index converted to period-end dates",
        )
    if isinstance(index, pd.DatetimeIndex):
        dates = index
    elif isinstance(index, pd.RangeIndex) or (
        isinstance(index, pd.Index) and pd.api.types.is_numeric_dtype(index.dtype)
    ):
        # Integer or float labels are positions, never dates: converting them would
        # silently produce 1970-epoch timestamps.
        return None, ()
    else:
        try:
            dates = pd.DatetimeIndex(pd.to_datetime(index))
        except (ValueError, TypeError) as exc:
            raise InputError(
                "Index could not be interpreted as dates; supply a DatetimeIndex or plain values."
            ) from exc
    if dates.tz is not None:
        dates = dates.tz_localize(None)
        notes.append("timezone information removed (wall-clock dates kept)")
    if dates.hasnans:
        raise InputError("Some timestamps are missing (NaT); every observation needs a date.")
    return pd.DatetimeIndex(dates), tuple(notes)
