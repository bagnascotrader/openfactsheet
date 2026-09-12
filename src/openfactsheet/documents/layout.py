"""Source-independent page layout: lines of positioned words.

Coordinates are unit-free: character offsets for layout-preserving PDF text,
pixels for OCR. Algorithms that use them (column assignment) only compare
positions within one table, so the unit never matters; it is recorded for
messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Source = Literal["text", "ocr"]


@dataclass(frozen=True)
class Word:
    """A word (or number) with its horizontal extent and, for OCR, a confidence in [0, 1]."""

    text: str
    x0: float
    x1: float
    y0: float = 0.0
    y1: float = 0.0
    confidence: float | None = None  # None for embedded text (exact by construction)

    @property
    def center(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def middle(self) -> float:
        return (self.y0 + self.y1) / 2.0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass(frozen=True)
class Line:
    """One text line; an empty line keeps the vertical rhythm of layout text."""

    words: tuple[Word, ...]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def is_blank(self) -> bool:
        return not self.words


@dataclass(frozen=True)
class PageLayout:
    """The lines of one page, top to bottom, and how they were obtained."""

    page: int  # 1-based
    lines: tuple[Line, ...]
    source: Source
    engine: str
    image_sha256: str | None = None

    @property
    def unit(self) -> str:
        return "characters" if self.source == "text" else "pixels"

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)
