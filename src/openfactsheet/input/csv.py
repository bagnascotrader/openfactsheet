"""CSV files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from openfactsheet.exceptions import InputError
from openfactsheet.input.pandas_input import from_frame
from openfactsheet.models.input import RawReturns


def read_csv(path: Path, name: str | None = None) -> list[RawReturns]:
    try:
        # Read everything as text so that '%' labels and accounting negatives survive.
        frame = pd.read_csv(path, dtype=str, sep=None, engine="python", skipinitialspace=True)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise InputError(f"Could not read CSV file {path.name!r}: {exc}") from exc
    frame = frame.dropna(axis=1, how="all")
    return from_frame(frame, name=name, source_type="csv")
