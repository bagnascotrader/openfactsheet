"""Plain Python / NumPy sequences of returns (undated)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from openfactsheet.exceptions import InputError
from openfactsheet.input.values import parse_cells
from openfactsheet.models.input import RawReturns


def from_sequence(data: Sequence[Any] | np.ndarray, name: str | None = None) -> RawReturns:
    if isinstance(data, np.ndarray):
        if data.ndim != 1:
            if data.ndim == 2 and 1 in data.shape:
                data = data.reshape(-1)
            else:
                raise InputError(
                    f"Expected a one-dimensional array of returns, got shape {data.shape}."
                )
        source = "numpy.ndarray"
    else:
        source = type(data).__name__
    if np.ndim(data) != 1:
        raise InputError("Expected a flat sequence of returns.")
    values, hint = parse_cells(list(data))
    return RawReturns(
        values=values,
        dates=None,
        name=name or "Returns",
        source_type=source,
        percent_hint=hint,
    )
