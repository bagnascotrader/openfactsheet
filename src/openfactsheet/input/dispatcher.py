"""Route any supported input to the right parser.

Every parser returns :class:`RawReturns`; normalization happens afterwards so
that all inputs share one set of conventions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from openfactsheet.exceptions import InputError
from openfactsheet.input.arrays import from_sequence
from openfactsheet.input.clipboard import read_text_table
from openfactsheet.input.csv import read_csv
from openfactsheet.input.excel import read_excel
from openfactsheet.input.image import IMAGE_SUFFIXES, read_image
from openfactsheet.input.pandas_input import from_frame, from_series
from openfactsheet.input.pdf import read_pdf
from openfactsheet.models.input import RawReturns

_TEXT_SUFFIXES = frozenset({".csv", ".txt", ".tsv"})
_EXCEL_SUFFIXES = frozenset({".xlsx", ".xlsm", ".xls"})


def _from_path(path: Path, name: str | None) -> list[RawReturns]:
    if not path.exists():
        raise InputError(f"File not found: {path}")
    suffix = path.suffix.lower()
    label = name or path.stem
    if suffix in _TEXT_SUFFIXES:
        raws = read_csv(path, name=name)
    elif suffix in _EXCEL_SUFFIXES:
        raws = read_excel(path, name=name)
    elif suffix in IMAGE_SUFFIXES:
        read_image(path)
        raise AssertionError("unreachable")  # pragma: no cover
    elif suffix == ".pdf":
        read_pdf(path)
        raise AssertionError("unreachable")  # pragma: no cover
    else:
        raise InputError(f"Unsupported file type {suffix!r} for {path.name}.")
    out: list[RawReturns] = []
    for r in raws:
        default_name = len(raws) == 1 and name is None and r.name == "Returns"
        out.append(
            replace(
                r,
                name=label if default_name else r.name,
                metadata={**r.metadata, "file_name": path.name},
            )
        )
    return out


def to_raw(source: Any, name: str | None = None) -> list[RawReturns]:
    """Parse ``source`` into one or more :class:`RawReturns` objects."""
    if isinstance(source, RawReturns):
        return [source]
    if isinstance(source, pd.Series):
        return [from_series(source, name=name)]
    if isinstance(source, pd.DataFrame):
        return from_frame(source, name=name)
    if isinstance(source, Path):
        return _from_path(source, name)
    if isinstance(source, str):
        if "\n" in source.strip():
            return read_text_table(source, name=name)
        return _from_path(Path(source), name)
    if isinstance(source, np.ndarray | list | tuple):
        return [from_sequence(source, name=name)]
    if isinstance(source, Sequence):  # pragma: no cover - other sequence types
        return [from_sequence(list(source), name=name)]
    raise InputError(
        f"Unsupported input type {type(source).__name__}. Supply a list, tuple, NumPy array, "
        "pandas Series/DataFrame, CSV/Excel path, or pasted table text."
    )
