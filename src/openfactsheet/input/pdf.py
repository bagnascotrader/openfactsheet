"""PDF factsheet ingestion — roadmap phase 6 (optional extra ``openfactsheet[pdf]``).

Policy: extract embedded text/table data first; OCR only rasterized pages; keep
extraction pluggable and never make metric correctness depend on an opaque
model call.
"""

from __future__ import annotations

from pathlib import Path

from openfactsheet.exceptions import OCRExtractionError


def read_pdf(path: Path) -> None:
    raise OCRExtractionError(
        f"PDF ingestion ({path.name}) is planned for a later release and is not available yet. "
        "Copy the monthly-return table as text and pass it to ofs.load(table_text)."
    )
