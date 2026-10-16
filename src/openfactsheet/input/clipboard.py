"""Pasted text tables (e.g. a monthly-return table copied from a PDF or web page)."""

from __future__ import annotations

import io

import pandas as pd

from openfactsheet.exceptions import InputError
from openfactsheet.input.limits import check_text_size
from openfactsheet.input.pandas_input import from_frame
from openfactsheet.models.input import RawReturns


def read_text_table(text: str, name: str | None = None) -> list[RawReturns]:
    """Parse a pasted table. Delimiters (tab, comma, semicolon, whitespace) are sniffed."""
    check_text_size(text)
    stripped = text.strip()
    if not stripped:
        raise InputError("The pasted text is empty.")
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip()]
    sep: str | None
    if all("\t" in ln for ln in lines):
        sep = "\t"
    elif all(";" in ln for ln in lines):
        sep = ";"
    elif all("," in ln for ln in lines) and not _decimal_commas(lines):
        sep = ","
    else:
        sep = r"\s+"
    try:
        frame = pd.read_csv(
            io.StringIO("\n".join(lines)),
            sep=sep,
            dtype=str,
            engine="python",
            skipinitialspace=True,
        )
    except pd.errors.ParserError as exc:
        raise InputError(f"Could not parse the pasted table: {exc}") from exc
    # A header row with one fewer field than the data rows (a blank top-left cell)
    # makes pandas use the first column as index; restore it as data.
    if not isinstance(frame.index, pd.RangeIndex):
        frame = frame.reset_index()
        frame = frame.rename(columns={frame.columns[0]: "Year"})
    return from_frame(frame, name=name, source_type="pasted text")


def _decimal_commas(lines: list[str]) -> bool:
    """True when commas look like decimal separators (e.g. ``1,2%``) rather than delimiters."""
    body = " ".join(lines[1:])
    return "." not in body and any(ch.isspace() for ch in body)
