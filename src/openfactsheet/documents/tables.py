"""Monthly-return tables reconstructed from page layouts (decisions 0030 and 0031).

1. find header lines naming all twelve months in order (optionally followed by a
   YTD / Year / Total column) and the year rows beneath them;
2. assign every value to the month column whose header it sits under, by
   horizontal position (text extraction drops empty cells, so a row with nine
   values could otherwise start in January or in April);
3. validate: every value assigned to exactly one column, years unique, and each
   year's compounded months reconciled with its YTD cell when one exists;
4. reconstruct the chronological series and record how it was obtained.

The same rules apply to embedded PDF text and to OCR; only the coordinates differ.
"""

from __future__ import annotations

import math
import re
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any, Literal

import pandas as pd

from openfactsheet.documents.layout import Line, PageLayout, Word
from openfactsheet.exceptions import InputError, OCRExtractionError
from openfactsheet.input.monthly_table import from_monthly_table
from openfactsheet.input.values import parse_cell
from openfactsheet.models.input import RawReturns

MONTH_LABELS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}  # fmt: skip
_TOTAL_LABELS = frozenset({"ytd", "year", "total", "annual", "yr", "fy", "cum", "cumulative"})
_YEAR = re.compile(r"^(18|19|20|21)\d{2}$")

Confidence = Literal["high", "moderate", "low"]


def month_of(text: str) -> int | None:
    return _MONTHS.get(re.sub(r"[^a-z]", "", text.lower()))


@dataclass(frozen=True)
class Header:
    line_index: int
    month_centers: tuple[float, ...]  # 12 centers, January first
    total_center: float | None
    total_label: str | None


def find_header(line: Line, line_index: int) -> Header | None:
    words = line.words
    found = [(w, m) for w in words if (m := month_of(w.text)) is not None]
    if [m for _, m in found] != list(range(1, 13)):
        return None
    centers = tuple(w.center for w, _ in found)
    if any(b <= a for a, b in pairwise(centers)):
        return None
    dec_end = found[-1][0].x1
    total = [
        w
        for w in words
        if w.x0 > dec_end and re.sub(r"[^a-z]", "", w.text.lower()) in _TOTAL_LABELS
    ]
    return Header(
        line_index=line_index,
        month_centers=centers,
        total_center=total[0].center if total else None,
        total_label=total[0].text if total else None,
    )


@dataclass
class ExtractedTable:
    """One monthly-return table reconstructed from a page."""

    page: int  # 1-based
    cells: dict[int, dict[int, str]]  # year -> month -> raw cell text
    totals: dict[int, str]  # year -> raw YTD/total cell text
    total_label: str | None
    percent_hint: bool | None
    source: str = "text"
    checks: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # OCR-only details (decision 0031): per-cell confidence and character repairs.
    cell_confidence: dict[tuple[int, int], float] = field(default_factory=dict)
    repairs: list[str] = field(default_factory=list)

    @property
    def years(self) -> list[int]:
        return sorted(self.cells)

    @property
    def n_values(self) -> int:
        return sum(len(v) for v in self.cells.values())

    @property
    def confidence(self) -> Confidence:
        if self.problems:
            return "low"
        if self.warnings:
            return "moderate"
        return "high"

    def to_text(self) -> str:
        """The reconstructed table, as OpenFactsheet read it."""
        label = self.total_label or "YTD"
        head = f"{'Year':<6}" + "".join(f"{m:>9}" for m in MONTH_LABELS) + f"{label:>10}"
        lines = [head]
        for year in self.years:
            row = self.cells[year]
            lines.append(
                f"{year:<6}"
                + "".join(f"{row.get(m, ''):>9}" for m in range(1, 13))
                + f"{self.totals.get(year, ''):>10}"
            )
        return "\n".join(lines)

    def to_frame(self) -> pd.DataFrame:
        rows = [
            {
                "Year": year,
                **{MONTH_LABELS[m - 1]: self.cells[year].get(m, "") for m in range(1, 13)},
            }
            for year in self.years
        ]
        return pd.DataFrame(rows, columns=["Year", *MONTH_LABELS])


def _decimals(text: str) -> int:
    digits = re.sub(r"[^0-9.,]", "", text)
    sep = "." if "." in digits else ("," if "," in digits else None)
    return len(digits.split(sep, 1)[1]) if sep else 0


def parse_rows(lines: Sequence[Line], header: Header) -> tuple[list[tuple[int, list[Word]]], int]:
    """Year rows under ``header``: returns ``[(year, value words)]`` and the last line used."""
    rows: list[tuple[int, list[Word]]] = []
    last = header.line_index
    blank_run = 0
    for i in range(header.line_index + 1, len(lines)):
        words = lines[i].words
        if not words:
            blank_run += 1
            if blank_run > 2:
                break
            continue
        blank_run = 0
        if not _YEAR.match(words[0].text):
            break
        rows.append((int(words[0].text), list(words[1:])))
        last = i
    return rows, last


def assign(
    table: ExtractedTable,
    header: Header,
    rows: list[tuple[int, list[Word]]],
    unit: str = "characters",
) -> None:
    centers = list(header.month_centers)
    spacing = statistics.median(b - a for a, b in pairwise(centers))
    tolerance = 0.5 * spacing
    columns: list[tuple[float, int | None]] = [(c, m) for m, c in enumerate(centers, start=1)]
    if header.total_center is not None:
        columns.append((header.total_center, None))  # None = the total column
    for year, words in rows:
        if year in table.cells:
            table.problems.append(f"Year {year} appears in more than one row.")
            continue
        row: dict[int, str] = {}
        for word in words:
            center, month = min(columns, key=lambda c: abs(c[0] - word.center))
            if abs(center - word.center) > tolerance:
                table.problems.append(
                    f"{year}: value {word.text!r} is not under any column header (offset "
                    f"{abs(center - word.center):.0f} {unit})."
                )
                continue
            try:
                parse_cell(word.text)
            except InputError:
                table.problems.append(f"{year}: {word.text!r} is not a return value.")
                continue
            if month is None:
                if year in table.totals:
                    table.problems.append(f"{year}: more than one value under the total column.")
                table.totals[year] = word.text
                if word.confidence is not None:
                    table.cell_confidence[(year, 0)] = word.confidence
            elif month in row:
                table.problems.append(
                    f"{year}: two values ({row[month]!r}, {word.text!r}) fall under "
                    f"{MONTH_LABELS[month - 1]}."
                )
            else:
                row[month] = word.text
                if word.confidence is not None:
                    table.cell_confidence[(year, month)] = word.confidence
        table.cells[year] = row


def reconcile_totals(table: ExtractedTable) -> None:
    """Check each year's compounded months against its YTD / total cell."""
    for year, total_text in sorted(table.totals.items()):
        cells = table.cells.get(year, {})
        values = [parse_cell(t)[0] for t in cells.values()]
        values = [v for v in values if not math.isnan(v)]
        total, _ = parse_cell(total_text)
        if not values or math.isnan(total):
            continue
        # Cells and total share one unit. Compound as percentages and, unless the table
        # is labelled in percent, also as decimals; either reading may reconcile.
        scales = (100.0,) if table.percent_hint else (100.0, 1.0)
        compounded = [(math.prod(1.0 + v / s for v in values) - 1.0) * s for s in scales]
        summed = sum(values)
        unit = 10.0 ** (-max(_decimals(t) for t in cells.values()))
        tol = 0.5 * 10.0 ** (-_decimals(total_text)) + 0.5 * unit * len(values) + 1e-9
        match = next((c for c in compounded if abs(c - total) <= tol), None)
        if match is not None:
            table.checks.append(
                f"{year}: compounded months {match:.4g} match {table.total_label or 'YTD'} "
                f"{total_text}."
            )
        elif abs(summed - total) <= tol:
            table.checks.append(
                f"{year}: {table.total_label or 'YTD'} {total_text} equals the sum."
            )
            table.warnings.append(
                f"{year}: the {table.total_label or 'YTD'} column is the arithmetic sum of the "
                "months, not their compounded return."
            )
        else:
            table.problems.append(
                f"{year}: the months compound to {compounded[0]:.4g} (as percentages), but the "
                f"{table.total_label or 'YTD'} cell says {total_text} (tolerance {tol:.2g})."
            )


def check_gaps(table: ExtractedTable) -> None:
    observed = sorted((y, m) for y in table.cells for m in table.cells[y])
    if not observed:
        table.problems.append("The table contains no monthly values.")
        return
    first, last = observed[0], observed[-1]
    present = set(observed)
    gaps = []
    y, m = first
    while (y, m) != last:
        if (y, m) not in present:
            gaps.append(f"{MONTH_LABELS[m - 1]} {y}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    if gaps:
        table.warnings.append(
            f"{len(gaps)} month(s) inside the history have no value ({', '.join(gaps[:6])}"
            + (", ..." if len(gaps) > 6 else "")
            + "); they are treated as missing, never as zero."
        )


def _percent_hint(lines: Sequence[Line], header: Header, table: ExtractedTable) -> bool | None:
    texts = [t for row in table.cells.values() for t in row.values()]
    if any("%" in t for t in texts):
        return True
    context = lines[max(0, header.line_index - 3) : header.line_index + 1]
    if any("%" in line.text for line in context):
        return True
    return None


def find_monthly_tables(layout: PageLayout) -> list[ExtractedTable]:
    """Every monthly-return table on one page, reconstructed and validated."""
    lines = layout.lines
    tables: list[ExtractedTable] = []
    i = 0
    while i < len(lines):
        header = find_header(lines[i], i)
        if header is None:
            i += 1
            continue
        rows, last = parse_rows(lines, header)
        if rows:
            table = ExtractedTable(
                page=layout.page,
                cells={},
                totals={},
                total_label=header.total_label,
                percent_hint=None,
                source=layout.source,
            )
            assign(table, header, rows, layout.unit)
            table.percent_hint = _percent_hint(lines, header, table)
            check_gaps(table)
            reconcile_totals(table)
            if header.total_center is None:
                table.warnings.append(
                    "The table has no YTD / total column, so the extraction could not be "
                    "cross-checked against annual totals."
                )
            tables.append(table)
        i = last + 1
    return tables


def refuse(table: ExtractedTable, file_name: str) -> OCRExtractionError:
    """The error raised for a table that could not be read reliably."""
    return OCRExtractionError(
        f"The monthly-return table on page {table.page} of {file_name} could not be read "
        "reliably, so no metrics are calculated from it:\n  - "
        + "\n  - ".join(table.problems)
        + "\nReconstructed table:\n"
        + table.to_text()
        + "\nCorrect it and pass it as text (ofs.load(table_text)) or as a CSV file."
    )


def tables_to_raw(
    tables: Sequence[ExtractedTable],
    *,
    file_name: str,
    stem: str,
    name: str | None,
    source_type: str,
    how: str,
    extraction: dict[str, Any],
) -> list[RawReturns]:
    """Turn accepted tables into :class:`RawReturns`; refuse any unreliable one.

    ``how`` describes the extraction for the transformation note (e.g. "embedded PDF
    text"); ``extraction`` is merged into each series' ``metadata["extraction"]``.
    """
    out: list[RawReturns] = []
    for k, table in enumerate(tables, start=1):
        if table.confidence == "low":
            raise refuse(table, file_name)
        raw = from_monthly_table(table.to_frame(), None, source_type)
        label = name if (name and len(tables) == 1) else ("Returns" if len(tables) == 1 else None)
        if label is None:
            label = f"{name or stem} (table {k}, page {table.page})"
        engine = extraction.get("engine", "")
        transformations = (
            f"monthly table extracted from {how} (table on page {table.page}, {engine}); "
            f"{table.n_values} monthly values; extraction confidence {table.confidence}",
            *raw.transformations,
        )
        details: dict[str, Any] = {
            **extraction,
            "page": table.page,
            "confidence": table.confidence,
            "monthly_values": table.n_values,
            "checks": list(table.checks),
            "warnings": list(table.warnings),
            "reconstructed_table": table.to_text(),
        }
        if table.source == "ocr":
            details["repairs"] = list(table.repairs)
            details["min_cell_confidence"] = (
                min(table.cell_confidence.values()) if table.cell_confidence else None
            )
        out.append(
            RawReturns(
                values=raw.values,
                dates=raw.dates,
                name=label,
                source_type=f"{source_type} (monthly table)",
                percent_hint=table.percent_hint if table.percent_hint else raw.percent_hint,
                transformations=transformations,
                warnings=tuple(table.warnings),
                metadata={"extraction": details},
            )
        )
    return out
