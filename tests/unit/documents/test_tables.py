"""Shared table reconstruction on source-independent layouts (decisions 0030, 0031)."""

from __future__ import annotations

import numpy as np

from openfactsheet.documents.layout import Line, PageLayout, Word
from openfactsheet.documents.tables import MONTH_LABELS, find_monthly_tables
from openfactsheet.documents.text_pdf import tokenize

CELLS_2023 = ["0.10%", "0.20%", "-2.50%", "1.00%", "1.50%", "0.30%",
              "-0.40%", "0.80%", "0.90%", "-1.10%", "2.20%", "0.60%"]  # fmt: skip


def _ytd(cells: list[str]) -> str:
    total = (np.prod([1 + float(c.rstrip("%")) / 100 for c in cells]) - 1) * 100
    return f"{total:.2f}%"


def _pixel_layout(x0: float = 120.0, col: float = 95.0) -> PageLayout:
    """A table laid out in pixels, as OCR would report it (word boxes, no char grid)."""

    def word(text: str, center: float, y: float, conf: float | None = 0.99) -> Word:
        half = 4.0 * len(text)
        return Word(text, center - half, center + half, y, y + 18.0, conf)

    header = Line(
        (
            *(word(m, x0 + col * (j + 1), 40.0) for j, m in enumerate(MONTH_LABELS)),
            word("YTD", x0 + col * 13, 40.0),
        )
    )
    # The 2022 row starts in April: three leading empty cells.
    y2022 = CELLS_2023[3:]
    row_2022 = Line(
        (
            word("2022", 40.0, 70.0),
            *(word(c, x0 + col * (j + 4), 70.0) for j, c in enumerate(y2022)),
            word(_ytd(y2022), x0 + col * 13, 70.0),
        )
    )
    row_2023 = Line(
        (
            word("2023", 40.0, 100.0),
            *(word(c, x0 + col * (j + 1), 100.0) for j, c in enumerate(CELLS_2023)),
            word(_ytd(CELLS_2023), x0 + col * 13, 100.0),
        )
    )
    title = Line((word("Monthly", 40.0, 5.0), word("returns", 110.0, 5.0)))
    return PageLayout(page=1, lines=(title, header, row_2022, row_2023), source="ocr", engine="x")


def test_pixel_coordinates_reconstruct_like_text() -> None:
    (table,) = find_monthly_tables(_pixel_layout())
    assert table.confidence == "high"
    assert sorted(table.cells[2022]) == list(range(4, 13))  # positions, not order
    assert table.cells[2023][3] == "-2.50%"
    assert len(table.checks) == 2
    assert table.cell_confidence[(2023, 1)] == 0.99
    assert table.source == "ocr"


def test_unit_is_reported_in_problems() -> None:
    layout = _pixel_layout()
    stray = Line((*layout.lines[3].words, Word("9.9", 2000.0, 2010.0, 100.0, 118.0, 0.99)))
    bad = PageLayout(1, (*layout.lines[:3], stray), "ocr", "x")
    (table,) = find_monthly_tables(bad)
    assert table.confidence == "low"
    assert any("pixels" in p for p in table.problems)


def test_tokenize_merges_detached_percent_and_keeps_offsets() -> None:
    line = tokenize("2023     1.2 %    -0.5%")
    assert [w.text for w in line.words] == ["2023", "1.2%", "-0.5%"]
    assert line.words[1].x0 == 9.0
    assert line.words[1].confidence is None  # embedded text is never given a made-up score
