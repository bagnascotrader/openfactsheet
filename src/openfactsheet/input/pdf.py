"""Monthly-return tables from PDF factsheets with embedded text (decision 0030).

Optional extra ``openfactsheet[pdf]`` (pypdf, BSD). Each page's embedded text is
extracted with its layout (character positions kept) and handed to the shared
table reconstruction of :mod:`openfactsheet.documents.tables`, which assigns
values to month columns by position and reconciles every year with its YTD
cell. Scanned (image-only) PDFs contain no text; OCR is not part of the core
library, so they are refused with an explanation. Extraction that fails
validation is refused too, showing the reconstructed table: OpenFactsheet never
calculates silently from a table it could not read reliably.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from openfactsheet.documents.tables import (
    MONTH_LABELS,
    ExtractedTable,
    find_monthly_tables,
    tables_to_raw,
)
from openfactsheet.documents.text_pdf import open_pdf, pypdf_engine, text_layouts
from openfactsheet.exceptions import OCRExtractionError
from openfactsheet.models.input import RawReturns

__all__ = ["MONTH_LABELS", "ExtractedTable", "extract_monthly_tables", "read_pdf"]


def extract_monthly_tables(path: Path) -> list[ExtractedTable]:
    """Find and reconstruct every monthly-return table in the PDF's embedded text."""
    layouts = text_layouts(open_pdf(path))
    tables = [t for layout in layouts for t in find_monthly_tables(layout)]
    if not any(layout.lines for layout in layouts):
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
    tables = extract_monthly_tables(path)
    return tables_to_raw(
        tables,
        file_name=path.name,
        stem=path.stem,
        name=name,
        source_type="pdf",
        how="embedded PDF text",
        extraction={
            "engine": pypdf_engine(),
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
    )
