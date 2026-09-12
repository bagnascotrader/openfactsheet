"""Monthly-return tables from PDF factsheets (decisions 0030 and 0031).

Optional extra ``openfactsheet[pdf]`` (pypdf, BSD). Each page's embedded text is
extracted with its layout (character positions kept) and handed to the shared
table reconstruction of :mod:`openfactsheet.documents.tables`, which assigns
values to month columns by position and reconciles every year with its YTD
cell. Pages without embedded text (scans) are rendered and recognized by OCR
when the ``openfactsheet[ocr]`` extra is installed, under OCR's stricter
acceptance rules. Extraction that fails validation is refused, showing the
reconstructed table: OpenFactsheet never calculates silently from a table it
could not read reliably.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Any

from openfactsheet.documents.layout import PageLayout
from openfactsheet.documents.profile import extract_profile
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


def _ocr_layouts(
    path: Path, pages: list[int], ocr_engine: str | None
) -> tuple[list[PageLayout], dict[str, Any]]:
    from openfactsheet.documents.ocr import get_engine, ocr_layout
    from openfactsheet.documents.raster import pdfium_version, render_pages
    from openfactsheet.policy.defaults import canonical_methodology

    engine = get_engine(ocr_engine)
    dpi = int(canonical_methodology().get("ocr.dpi"))
    layouts = [ocr_layout(img, engine, page=n) for n, img in render_pages(path, pages, dpi)]
    info: dict[str, Any] = {
        "engine": engine.info.label,
        "ocr": engine.info.to_dict(),
        "renderer": pdfium_version(),
        "dpi": dpi,
    }
    return layouts, info


def extract_monthly_tables(
    path: Path, ocr_engine: str | None = None
) -> tuple[list[ExtractedTable], dict[int, PageLayout], dict[str, Any]]:
    """Every monthly-return table of the PDF, with the page layouts and OCR details."""
    layouts = {layout.page: layout for layout in text_layouts(open_pdf(path))}
    scanned = [n for n, layout in layouts.items() if not layout.lines]
    ocr_info: dict[str, Any] = {}
    ocr_error: OCRExtractionError | None = None
    if scanned:
        try:
            ocr_layouts, ocr_info = _ocr_layouts(path, scanned, ocr_engine)
            layouts.update({layout.page: layout for layout in ocr_layouts})
        except OCRExtractionError as exc:
            ocr_error = exc
    tables = [t for n in sorted(layouts) for t in find_monthly_tables(layouts[n])]
    if not tables:
        if len(scanned) == len(layouts):
            raise OCRExtractionError(
                f"{path.name} contains no embedded text (it is probably a scanned image) "
                + (
                    f"and could not be recognized: {ocr_error}"
                    if ocr_error is not None
                    else "and OCR of its pages found no monthly-return table."
                )
            )
        raise OCRExtractionError(
            f"No monthly-return table (a header row naming all twelve months, followed by "
            f"year rows) was found in {path.name}."
            + (f" Scanned page(s) {scanned} were not recognized: {ocr_error}" if ocr_error else "")
        )
    return tables, layouts, ocr_info


def read_pdf(
    path: Path, name: str | None = None, ocr_engine: str | None = None
) -> list[RawReturns]:
    """Parse every monthly-return table of a PDF; refuse unreliable extractions."""
    tables, layouts, ocr_info = extract_monthly_tables(path, ocr_engine)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()

    def describe(table: ExtractedTable) -> tuple[str, dict[str, Any]]:
        if table.source == "ocr":
            return "OCR of a scanned PDF page", {
                **ocr_info,
                "source_sha256": sha,
                "image_sha256": layouts[table.page].image_sha256,
            }
        return "embedded PDF text", {"engine": pypdf_engine(), "source_sha256": sha}

    raws = tables_to_raw(
        tables,
        file_name=path.name,
        stem=path.stem,
        name=name,
        source_type="pdf",
        describe=describe,
    )
    profile = extract_profile([layouts[n] for n in sorted(layouts)], path.name, tables)
    return [replace(r, metadata={**r.metadata, "document": profile}) for r in raws]
