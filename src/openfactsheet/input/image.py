"""Screenshot / image ingestion — roadmap phase 6 (optional extra ``openfactsheet[images]``).

The planned pipeline (CLAUDE.md section 26) is: layout detection → table
extraction → header recognition → cell extraction with confidence → chronological
reconstruction → validation → human-readable reconstructed table. Canonical
metrics will be refused when extraction confidence is materially inadequate.
"""

from __future__ import annotations

from pathlib import Path

from openfactsheet.exceptions import OCRExtractionError

IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"})


def read_image(path: Path) -> None:
    raise OCRExtractionError(
        f"Image ingestion ({path.suffix}) is planned for a later release and is not available "
        "yet. Transcribe the monthly-return table to CSV or paste it as text: "
        "ofs.load(table_text)."
    )
