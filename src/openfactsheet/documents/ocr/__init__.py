"""Pluggable OCR engines (decision 0031).

``rapidocr`` (default; optional extra ``openfactsheet[ocr]``) and ``tesseract``
(``openfactsheet[tesseract]`` plus the Tesseract program). Engines run locally
and never download anything during analysis.
"""

from __future__ import annotations

from openfactsheet.documents.ocr.base import EngineInfo, OCREngine, group_lines, ocr_layout
from openfactsheet.exceptions import InputError

ENGINES = ("rapidocr", "tesseract")


def get_engine(name: str | None = None) -> OCREngine:
    """The named OCR engine, or the methodology's default engine."""
    from openfactsheet.policy.defaults import canonical_methodology

    choice = (name or str(canonical_methodology().get("ocr.default_engine"))).lower()
    if choice == "rapidocr":
        from openfactsheet.documents.ocr.rapid import RapidOCREngine

        return RapidOCREngine()
    if choice == "tesseract":
        from openfactsheet.documents.ocr.tesseract import TesseractEngine

        return TesseractEngine()
    raise InputError(f"Unknown OCR engine {name!r}; available: {', '.join(ENGINES)}.")


__all__ = ["ENGINES", "EngineInfo", "OCREngine", "get_engine", "group_lines", "ocr_layout"]
