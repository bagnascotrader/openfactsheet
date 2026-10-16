"""Monthly-return tables from screenshots and images, by OCR (decision 0031).

Optional extra ``openfactsheet[ocr]`` (RapidOCR with its bundled models; or
``openfactsheet[tesseract]``). The recognized words go through the same table
reconstruction as PDF text, under OCR's stricter rules: a confidence floor per
cell, recorded character repairs, and a YTD / total column that must reconcile
every year. A table that fails is refused with the reconstructed table.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Any

from openfactsheet.documents.profile import extract_profile
from openfactsheet.documents.tables import ExtractedTable, find_monthly_tables, tables_to_raw
from openfactsheet.exceptions import OCRExtractionError
from openfactsheet.input.limits import check_pixels
from openfactsheet.models.input import RawReturns

IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"})


def read_image(
    path: Path, name: str | None = None, ocr_engine: str | None = None
) -> list[RawReturns]:
    """Recognize the monthly-return table(s) in an image; refuse unreliable ones."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise OCRExtractionError(
            f'Reading images ({path.suffix}) needs OCR: pip install "openfactsheet[ocr]".'
        ) from exc
    from openfactsheet.documents.ocr import get_engine, ocr_layout

    try:
        with Image.open(path) as opened:
            # Image.open reads only the header: check the size before decoding pixels.
            check_pixels(*opened.size, what=path.name)
            image = opened.convert("RGB")
    except (OSError, Image.DecompressionBombError) as exc:
        raise OCRExtractionError(f"Could not open {path.name} as an image ({exc}).") from exc
    engine = get_engine(ocr_engine)
    layout = ocr_layout(image, engine)
    tables = find_monthly_tables(layout)
    if not tables:
        seen = "\n".join(line.text for line in layout.lines[:12])
        raise OCRExtractionError(
            f"No monthly-return table (a header row naming the months, followed by year rows) "
            f"was recognized in {path.name}. First recognized lines:\n{seen}"
        )
    sha = hashlib.sha256(path.read_bytes()).hexdigest()

    def describe(_: ExtractedTable) -> tuple[str, dict[str, Any]]:
        return "OCR of an image", {
            "engine": engine.info.label,
            "ocr": engine.info.to_dict(),
            "source_sha256": sha,
            "image_sha256": layout.image_sha256,
        }

    raws = tables_to_raw(
        tables,
        file_name=path.name,
        stem=path.stem,
        name=name,
        source_type="image",
        describe=describe,
    )
    profile = extract_profile([layout], path.name, tables)
    return [replace(r, metadata={**r.metadata, "document": profile}) for r in raws]
