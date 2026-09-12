"""Tesseract adapter (Apache-2.0) via pytesseract; needs the Tesseract program installed.

Tesseract runs locally with its installed language data; its version is recorded.
Confidences (0-100) are divided by 100.
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any

from openfactsheet.documents.layout import Word
from openfactsheet.documents.ocr.base import EngineInfo
from openfactsheet.exceptions import OCRExtractionError

if TYPE_CHECKING:
    from PIL import Image


def _pytesseract() -> Any:
    try:
        import pytesseract
    except ImportError as exc:
        raise OCRExtractionError(
            "The Tesseract engine needs pytesseract and the Tesseract program: "
            'pip install "openfactsheet[tesseract]" and install Tesseract '
            "(https://github.com/tesseract-ocr/tesseract)."
        ) from exc
    try:
        pytesseract.get_tesseract_version()
    except Exception as exc:  # binary missing
        raise OCRExtractionError(
            "The Tesseract program was not found. Install it "
            "(https://github.com/tesseract-ocr/tesseract) or use the default engine."
        ) from exc
    return pytesseract


class TesseractEngine:
    """Word-level recognition with Tesseract (page segmentation for sparse text)."""

    def __init__(self, lang: str = "eng") -> None:
        self._tess = _pytesseract()
        self._lang = lang

    @cached_property
    def info(self) -> EngineInfo:
        return EngineInfo(
            name="tesseract",
            version=f"{self._tess.get_tesseract_version()} ({self._lang})",
        )

    def recognize(self, image: Image.Image) -> list[Word]:
        data = self._tess.image_to_data(
            image.convert("RGB"),
            lang=self._lang,
            config="--psm 11",
            output_type=self._tess.Output.DICT,
        )
        words: list[Word] = []
        for i, text in enumerate(data["text"]):
            conf = float(data["conf"][i])
            if not str(text).strip() or conf < 0:
                continue
            x, y = float(data["left"][i]), float(data["top"][i])
            w, h = float(data["width"][i]), float(data["height"][i])
            words.append(Word(str(text), x, x + w, y, y + h, conf / 100.0))
        return words
