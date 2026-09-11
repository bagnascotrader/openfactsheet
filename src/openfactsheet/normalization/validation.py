"""Early validation of raw values and timestamps (input corruption fails early)."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pandas as pd

from openfactsheet.exceptions import InputError


def validate_values(values: npt.NDArray[np.float64], name: str) -> None:
    if values.size == 0:
        raise InputError(f"{name}: no observations supplied.")
    if np.isinf(values).any():
        positions = np.flatnonzero(np.isinf(values))[:5].tolist()
        raise InputError(
            f"{name}: infinite values at positions {positions}; returns must be finite."
        )
    if np.isnan(values).all():
        raise InputError(f"{name}: all values are missing.")


def find_duplicate_dates(dates: pd.DatetimeIndex) -> list[str]:
    dup = dates[dates.duplicated(keep=False)]
    return sorted({d.strftime("%Y-%m-%d") for d in dup})


def validate_dates(dates: pd.DatetimeIndex, name: str) -> None:
    duplicates = find_duplicate_dates(dates)
    if duplicates:
        shown = ", ".join(duplicates[:5])
        raise InputError(
            f"{name}: duplicate timestamps ({len(duplicates)} distinct dates, e.g. {shown}). "
            "OpenFactsheet will not choose between conflicting observations; remove duplicates."
        )
