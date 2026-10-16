"""Excel workbooks (optional extra: ``pip install openfactsheet[excel]``)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from openfactsheet.exceptions import InputError
from openfactsheet.input.limits import check_excel_package
from openfactsheet.input.pandas_input import from_frame
from openfactsheet.models.input import RawReturns


def read_excel(path: Path, name: str | None = None) -> list[RawReturns]:
    try:
        import openpyxl  # noqa: F401
    except ImportError as exc:
        raise InputError(
            "Reading Excel files requires the optional dependency openpyxl: "
            "pip install 'openfactsheet[excel]'"
        ) from exc
    check_excel_package(path)  # zip-bomb guard before openpyxl inflates any part
    try:
        # Only the first sheet is read; choosing among sheets would be a guess.
        frame = pd.read_excel(path, sheet_name=0)
    except (OSError, ValueError) as exc:
        raise InputError(f"Could not read Excel file {path.name!r}: {exc}") from exc
    frame = frame.dropna(axis=1, how="all").dropna(axis=0, how="all")
    return from_frame(frame, name=name, source_type="excel")
