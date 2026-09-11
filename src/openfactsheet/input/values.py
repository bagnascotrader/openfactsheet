"""Parsing of individual return cells (numbers or strings such as ``"-1.2%"``)."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from typing import Any

import numpy as np
import numpy.typing as npt

from openfactsheet.exceptions import InputError

_MISSING_TOKENS = frozenset({"", "-", "--", "—", "–", "na", "n/a", "nan", "none", "null", "#n/a"})
_NUMBER = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")


def parse_cell(cell: Any) -> tuple[float, bool]:
    """Parse one cell into ``(value, had_percent_sign)``; missing cells give NaN.

    Accepted string forms: ``"1.2"``, ``"1.2%"``, ``"-1.2 %"``, ``"(1.2)"``
    (accounting negative), unicode minus ``"−1.2"``, and a decimal comma
    ``"1,2"`` when no period is present (thousands separators are not plausible
    in return data).
    """
    if cell is None:
        return math.nan, False
    if isinstance(cell, bool):
        raise InputError(f"Boolean value {cell!r} is not a return.")
    if isinstance(cell, int | float | np.integer | np.floating):
        return float(cell), False
    text = str(cell).strip()
    if text.lower() in _MISSING_TOKENS:
        return math.nan, False
    percent = "%" in text
    text = text.replace("%", "").replace("−", "-").replace(" ", "").replace(" ", "")
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    if not _NUMBER.match(text):
        raise InputError(f"Cannot parse {cell!r} as a return value.")
    value = float(text)
    return (-value if negative else value), percent


def parse_cells(cells: Iterable[Any]) -> tuple[npt.NDArray[np.float64], bool | None]:
    """Parse many cells; the percent hint is ``True`` if any cell carried ``%``.

    Returns ``(values, percent_hint)`` where ``percent_hint`` is ``None`` when no
    cell was a string (numeric input carries no label evidence).
    """
    values: list[float] = []
    any_string = False
    any_percent = False
    for cell in cells:
        if isinstance(cell, str):
            any_string = True
        v, pct = parse_cell(cell)
        any_percent = any_percent or pct
        values.append(v)
    hint: bool | None = any_percent if any_string else None
    return np.asarray(values, dtype=np.float64), hint
