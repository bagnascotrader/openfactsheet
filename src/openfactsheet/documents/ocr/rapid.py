"""RapidOCR adapter (Apache-2.0; PaddleOCR models, Apache-2.0).

The models used are the ones shipped inside the installed ``rapidocr`` wheel. They
are passed to RapidOCR as explicit file paths, so its automatic model download is
never triggered: recognition is fully local. Every model file is fingerprinted
(SHA-256) and recorded with the engine version.
"""

from __future__ import annotations

from functools import cached_property
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Any

from openfactsheet.documents.layout import Word
from openfactsheet.documents.ocr.base import EngineInfo, file_sha256
from openfactsheet.exceptions import OCRExtractionError

if TYPE_CHECKING:
    from PIL import Image

_ROLES = ("det", "rec", "cls")


def _bundled_models() -> dict[str, Path]:
    try:
        import rapidocr
    except ImportError as exc:
        raise OCRExtractionError(
            'OCR needs the optional dependency RapidOCR: pip install "openfactsheet[ocr]" '
            '(or use the Tesseract engine: ocr_engine="tesseract").'
        ) from exc
    folder = Path(rapidocr.__file__).parent / "models"
    found: dict[str, Path] = {}
    for role in _ROLES:
        matches = sorted(folder.glob(f"*_{role}_*.onnx"))
        if len(matches) != 1:
            raise OCRExtractionError(
                f"Expected exactly one bundled RapidOCR {role} model in {folder}, found "
                f"{len(matches)}. OpenFactsheet never downloads models; reinstall rapidocr."
            )
        found[role] = matches[0]
    return found


class RapidOCREngine:
    """Word-level recognition with RapidOCR 3.x and its bundled ONNX models."""

    def __init__(self) -> None:
        self._models = _bundled_models()

    @cached_property
    def info(self) -> EngineInfo:
        return EngineInfo(
            name="rapidocr",
            version=version("rapidocr"),
            models=tuple((p.name, file_sha256(p)) for p in self._models.values()),
        )

    @cached_property
    def _engine(self) -> Any:
        from rapidocr import RapidOCR

        params: dict[str, Any] = {
            "Global.return_word_box": True,
            "Global.log_level": "warning",
            "Det.model_path": str(self._models["det"]),
            "Rec.model_path": str(self._models["rec"]),
            "Cls.model_path": str(self._models["cls"]),
        }
        return RapidOCR(params=params)

    def recognize(self, image: Image.Image) -> list[Word]:
        import numpy as np

        result = self._engine(np.asarray(image.convert("RGB")))
        words: list[Word] = []
        if result.boxes is None:  # nothing detected (e.g. a blank page)
            return words
        for line in result.word_results or ():
            for item in line:
                if not isinstance(item, tuple | list) or len(item) != 3 or item[2] is None:
                    continue
                text, score, box = item
                xs = [float(p[0]) for p in box]
                ys = [float(p[1]) for p in box]
                words.append(Word(str(text), min(xs), max(xs), min(ys), max(ys), float(score)))
        return words
