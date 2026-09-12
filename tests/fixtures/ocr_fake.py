"""A deterministic stand-in OCR engine for engine-independent tests (decision 0031).

It turns the text items of :mod:`tests.fixtures.pdf_writer` pages into pixel word
boxes (as a 300-DPI scan would place them) and lets tests inject the errors real
engines make: low confidence, character confusions, dropped minus signs.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from tests.fixtures.pdf_writer import PAGE_SIZE, TextItem

from openfactsheet.documents.layout import Word
from openfactsheet.documents.ocr.base import EngineInfo

SCALE = 300 / 72  # points -> pixels at 300 DPI
CHAR_WIDTH = 4.6  # points per character, as assumed by pdf_writer
FONT_HEIGHT = 9.0


def items_to_words(
    items: Sequence[TextItem],
    confidence: float = 0.99,
    alter: Callable[[str], tuple[str, float]] | None = None,
) -> list[Word]:
    words = []
    for x, y, text in items:
        conf = confidence
        if alter is not None:
            text, conf = alter(text)
        for k, token in enumerate(text.split(" ")):
            offset = sum(len(t) + 1 for t in text.split(" ")[:k]) * CHAR_WIDTH
            x0 = (x + offset) * SCALE
            top = (PAGE_SIZE[1] - y - FONT_HEIGHT) * SCALE
            words.append(
                Word(
                    token,
                    x0,
                    x0 + len(token) * CHAR_WIDTH * SCALE,
                    top,
                    top + FONT_HEIGHT * SCALE,
                    conf,
                )
            )
    return words


@dataclass
class FakeEngine:
    """Returns prepared words for any image."""

    words: list[Word] = field(default_factory=list)

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(name="fake", version="1", models=(("fake.onnx", "0" * 64),))

    def recognize(self, image: object) -> list[Word]:
        return list(self.words)
