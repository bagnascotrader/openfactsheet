"""Render PDF pages to images for OCR (pypdfium2: Apache-2.0 / BSD-3; decision 0031)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from openfactsheet.exceptions import OCRExtractionError

if TYPE_CHECKING:
    from PIL import Image


def render_pages(path: Path, pages: Iterable[int], dpi: int) -> list[tuple[int, Image.Image]]:
    """Render the given 1-based pages at ``dpi`` as RGB images."""
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise OCRExtractionError(
            'Scanned PDF pages need OCR: pip install "openfactsheet[ocr]".'
        ) from exc
    doc = pdfium.PdfDocument(str(path))
    try:
        out = []
        for number in pages:
            bitmap = doc[number - 1].render(scale=dpi / 72.0)
            out.append((number, bitmap.to_pil().convert("RGB")))
        return out
    finally:
        doc.close()


def pdfium_version() -> str:
    from importlib.metadata import version

    return f"pypdfium2 {version('pypdfium2')}"
