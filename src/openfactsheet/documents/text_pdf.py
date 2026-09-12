"""Embedded PDF text as page layouts (pypdf, layout-preserving extraction; decision 0030)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from openfactsheet.documents.layout import Line, PageLayout, Word
from openfactsheet.exceptions import OCRExtractionError

_TOKEN = re.compile(r"\S+")


def tokenize(line: str) -> Line:
    """Split a layout text line into words positioned by character offset."""
    words: list[Word] = []
    for m in _TOKEN.finditer(line):
        word = Word(m.group(0), float(m.start()), float(m.end()))
        # A detached "%" (e.g. "1.2 %") belongs to the number before it.
        if word.text == "%" and words:
            prev = words[-1]
            words[-1] = Word(prev.text + "%", prev.x0, word.x1)
            continue
        words.append(word)
    return Line(tuple(words))


def open_pdf(path: Path) -> Any:
    """A pypdf reader, or :class:`OCRExtractionError` explaining why not."""
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


def pypdf_engine() -> str:
    from importlib.metadata import version

    return f"pypdf {version('pypdf')}"


def text_layouts(reader: Any) -> list[PageLayout]:
    """One layout per page from the embedded text (pages without text have no lines)."""
    engine = pypdf_engine()
    layouts = []
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text(extraction_mode="layout") or ""
        lines = tuple(tokenize(line) for line in text.splitlines()) if text.strip() else ()
        layouts.append(PageLayout(page=number, lines=lines, source="text", engine=engine))
    return layouts
