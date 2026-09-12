"""OCR engine interface and line grouping (decision 0031)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from openfactsheet.documents.layout import Line, PageLayout, Word

if TYPE_CHECKING:
    from PIL import Image


@dataclass(frozen=True)
class EngineInfo:
    """What produced an OCR result: recorded in every extraction's provenance."""

    name: str
    version: str
    models: tuple[tuple[str, str], ...] = ()  # (file name, SHA-256)

    @property
    def label(self) -> str:
        return f"{self.name} {self.version}"

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "models": [{"file": f, "sha256": h} for f, h in self.models],
        }


class OCREngine(Protocol):
    """Recognizes words with pixel boxes and a confidence in [0, 1]; never uses the network."""

    @property
    def info(self) -> EngineInfo: ...

    def recognize(self, image: Image.Image) -> list[Word]: ...


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_sha256(image: Image.Image) -> str:
    """Fingerprint of the pixels that were recognized (mode, size and raw bytes)."""
    digest = hashlib.sha256(f"{image.mode}:{image.size[0]}x{image.size[1]}:".encode())
    digest.update(image.tobytes())
    return digest.hexdigest()


def group_lines(words: list[Word]) -> tuple[Line, ...]:
    """Group words into lines, top to bottom, left to right.

    A word joins a line when it overlaps the line's vertical band by at least half
    of the smaller of the two heights; otherwise it starts a new line.
    """
    lines: list[list[Word]] = []
    bands: list[tuple[float, float]] = []
    for word in sorted(words, key=lambda w: (w.middle, w.x0)):
        placed = False
        for i, (top, bottom) in enumerate(bands):
            overlap = min(bottom, word.y1) - max(top, word.y0)
            if overlap >= 0.5 * min(bottom - top, word.height):
                lines[i].append(word)
                bands[i] = (min(top, word.y0), max(bottom, word.y1))
                placed = True
                break
        if not placed:
            lines.append([word])
            bands.append((word.y0, word.y1))
    order = sorted(range(len(lines)), key=lambda i: (bands[i][0] + bands[i][1]) / 2)
    return tuple(Line(tuple(sorted(lines[i], key=lambda w: w.x0))) for i in order)


def ocr_layout(image: Image.Image, engine: OCREngine, page: int = 1) -> PageLayout:
    """Recognize one image and return its page layout."""
    words = [w for w in engine.recognize(image) if w.text.strip()]
    return PageLayout(
        page=page,
        lines=group_lines(words),
        source="ocr",
        engine=engine.info.label,
        image_sha256=image_sha256(image),
    )
