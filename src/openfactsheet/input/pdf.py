"""Monthly-return tables from PDF factsheets with embedded text (decision 0030).

Optional extra ``openfactsheet[pdf]`` (pypdf, BSD). Pipeline:

1. extract each page's embedded text with its layout (character positions kept);
2. find header lines naming all twelve months in order (optionally followed by
   a YTD / Year / Total column) and the year rows beneath them;
3. assign every value to the month column whose header it sits under, by
   horizontal position (text extraction drops empty cells, so a row with nine
   values could otherwise start in January or in April);
4. validate: every value assigned to exactly one column, years unique, and each
   year's compounded months reconciled with its YTD cell when one exists;
5. reconstruct the chronological series and record how it was obtained.

Scanned (image-only) PDFs contain no text; OCR is not part of the core library,
so they are refused with an explanation. Extraction that fails validation is
refused too, showing the reconstructed table: OpenFactsheet never calculates
silently from a table it could not read reliably.
"""

from __future__ import annotations

import hashlib
import math
import re
import statistics
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

import pandas as pd

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
_TOKEN = re.compile(r"\S+")

Confidence = Literal["high", "moderate", "low"]


@dataclass(frozen=True)
class _Token:
    text: str
    start: int
    end: int

    @property
    def center(self) -> float:
        return (self.start + self.end) / 2.0


def _tokens(line: str) -> list[_Token]:
    out: list[_Token] = []
    for m in _TOKEN.finditer(line):
        tok = _Token(m.group(0), m.start(), m.end())
        # A detached "%" (e.g. "1.2 %") belongs to the number before it.
        if tok.text == "%" and out:
            prev = out[-1]
            out[-1] = _Token(prev.text + "%", prev.start, tok.end)
            continue
        out.append(tok)
    return out


def _month_of(text: str) -> int | None:
    return _MONTHS.get(re.sub(r"[^a-z]", "", text.lower()))


@dataclass(frozen=True)
class _Header:
    line_index: int
    month_centers: tuple[float, ...]  # 12 centers, January first
    total_center: float | None
    total_label: str | None


def _header(tokens: list[_Token], line_index: int) -> _Header | None:
    months = [(t, _month_of(t.text)) for t in tokens]
    found = [(t, m) for t, m in months if m is not None]
    if [m for _, m in found] != list(range(1, 13)):
        return None
    centers = tuple(t.center for t, _ in found)
    if any(b <= a for a, b in pairwise(centers)):
        return None
    dec_end = found[-1][0].end
    total = [
        t
        for t in tokens
        if t.start > dec_end and re.sub(r"[^a-z]", "", t.text.lower()) in _TOTAL_LABELS
    ]
    return _Header(
        line_index=line_index,
        month_centers=centers,
        total_center=total[0].center if total else None,
        total_label=total[0].text if total else None,
    )


@dataclass
class ExtractedTable:
    """One monthly-return table reconstructed from a PDF page."""

    page: int  # 1-based
    cells: dict[int, dict[int, str]]  # year -> month -> raw cell text
    totals: dict[int, str]  # year -> raw YTD/total cell text
    total_label: str | None
    percent_hint: bool | None
    checks: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

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


def _parse_rows(lines: list[str], header: _Header) -> tuple[list[tuple[int, list[_Token]]], int]:
    """Year rows under ``header``: returns ``[(year, value tokens)]`` and the last line used."""
    rows: list[tuple[int, list[_Token]]] = []
    last = header.line_index
    blank_run = 0
    for i in range(header.line_index + 1, len(lines)):
        tokens = _tokens(lines[i])
        if not tokens:
            blank_run += 1
            if blank_run > 2:
                break
            continue
        blank_run = 0
        if not _YEAR.match(tokens[0].text):
            break
        rows.append((int(tokens[0].text), tokens[1:]))
        last = i
    return rows, last


def _assign(table: ExtractedTable, header: _Header, rows: list[tuple[int, list[_Token]]]) -> None:
    centers = list(header.month_centers)
    spacing = statistics.median(b - a for a, b in pairwise(centers))
    tolerance = 0.5 * spacing
    columns: list[tuple[float, int | None]] = [(c, m) for m, c in enumerate(centers, start=1)]
    if header.total_center is not None:
        columns.append((header.total_center, None))  # None = the total column
    for year, tokens in rows:
        if year in table.cells:
            table.problems.append(f"Year {year} appears in more than one row.")
            continue
        row: dict[int, str] = {}
        for tok in tokens:
            center, month = min(columns, key=lambda c: abs(c[0] - tok.center))
            if abs(center - tok.center) > tolerance:
                table.problems.append(
                    f"{year}: value {tok.text!r} is not under any column header (offset "
                    f"{abs(center - tok.center):.0f} characters)."
                )
                continue
            try:
                parse_cell(tok.text)
            except InputError:
                table.problems.append(f"{year}: {tok.text!r} is not a return value.")
                continue
            if month is None:
                if year in table.totals:
                    table.problems.append(f"{year}: more than one value under the total column.")
                table.totals[year] = tok.text
            elif month in row:
                table.problems.append(
                    f"{year}: two values ({row[month]!r}, {tok.text!r}) fall under "
                    f"{MONTH_LABELS[month - 1]}."
                )
            else:
                row[month] = tok.text
        table.cells[year] = row


def _reconcile_totals(table: ExtractedTable) -> None:
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


def _check_gaps(table: ExtractedTable) -> None:
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


def _percent_hint(lines: list[str], header: _Header, table: ExtractedTable) -> bool | None:
    texts = [t for row in table.cells.values() for t in row.values()]
    if any("%" in t for t in texts):
        return True
    context = lines[max(0, header.line_index - 3) : header.line_index + 1]
    if any("%" in line for line in context):
        return True
    return None


def _reader(path: Path) -> Any:
    try:
        import pypdf
    except ImportError as exc:  # pragma: no cover - depends on the optional extra
        raise OCRExtractionError(
            "Reading PDF files needs the optional dependency pypdf: "
            'pip install "openfactsheet[pdf]".'
        ) from exc
    try:
        return pypdf.PdfReader(str(path))
    except Exception as exc:  # malformed or encrypted files
        raise OCRExtractionError(f"Could not open {path.name} as a PDF ({exc}).") from exc


def extract_monthly_tables(path: Path) -> list[ExtractedTable]:
    """Find and reconstruct every monthly-return table in the PDF's embedded text."""
    reader = _reader(path)
    tables: list[ExtractedTable] = []
    any_text = False
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text(extraction_mode="layout") or ""
        any_text = any_text or bool(text.strip())
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            header = _header(_tokens(lines[i]), i)
            if header is None:
                i += 1
                continue
            rows, last = _parse_rows(lines, header)
            if rows:
                table = ExtractedTable(
                    page=page_number,
                    cells={},
                    totals={},
                    total_label=header.total_label,
                    percent_hint=None,
                )
                _assign(table, header, rows)
                table.percent_hint = _percent_hint(lines, header, table)
                _check_gaps(table)
                _reconcile_totals(table)
                if header.total_center is None:
                    table.warnings.append(
                        "The table has no YTD / total column, so the extraction could not be "
                        "cross-checked against annual totals."
                    )
                tables.append(table)
            i = last + 1
    if not any_text:
        raise OCRExtractionError(
            f"{path.name} contains no embedded text (it is probably a scanned image). OCR is not "
            "part of the core library; transcribe the monthly-return table to CSV or paste it as "
            "text: ofs.load(table_text)."
        )
    if not tables:
        raise OCRExtractionError(
            f"No monthly-return table (a header row naming all twelve months, followed by "
            f"year rows) was found in the text of {path.name}."
        )
    return tables


def read_pdf(path: Path, name: str | None = None) -> list[RawReturns]:
    """Parse every monthly-return table of a text PDF; refuse unreliable extractions."""
    from importlib.metadata import version

    tables = extract_monthly_tables(path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    engine = f"pypdf {version('pypdf')}"
    out: list[RawReturns] = []
    for k, table in enumerate(tables, start=1):
        where = f"table on page {table.page}"
        if table.confidence == "low":
            raise OCRExtractionError(
                f"The monthly-return {where} of {path.name} could not be read reliably, so no "
                "metrics are calculated from it:\n  - "
                + "\n  - ".join(table.problems)
                + "\nReconstructed table:\n"
                + table.to_text()
                + "\nCorrect it and pass it as text (ofs.load(table_text)) or as a CSV file."
            )
        raw = from_monthly_table(table.to_frame(), None, "pdf")
        label = name if (name and len(tables) == 1) else ("Returns" if len(tables) == 1 else None)
        if label is None:
            label = f"{name or path.stem} (table {k}, page {table.page})"
        transformations = (
            f"monthly table extracted from embedded PDF text ({where}, {engine}); "
            f"{table.n_values} monthly values; extraction confidence {table.confidence}",
            *raw.transformations,
        )
        out.append(
            RawReturns(
                values=raw.values,
                dates=raw.dates,
                name=label,
                source_type="pdf (monthly table)",
                percent_hint=table.percent_hint if table.percent_hint else raw.percent_hint,
                transformations=transformations,
                warnings=tuple(table.warnings),
                metadata={
                    "extraction": {
                        "engine": engine,
                        "source_sha256": sha,
                        "page": table.page,
                        "confidence": table.confidence,
                        "monthly_values": table.n_values,
                        "checks": list(table.checks),
                        "warnings": list(table.warnings),
                        "reconstructed_table": table.to_text(),
                    }
                },
            )
        )
    return out
