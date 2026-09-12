"""OCR acceptance rules with a fake engine: no OCR library needed (decision 0031)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import openfactsheet as ofs
from openfactsheet.documents import ocr as ocr_module
from openfactsheet.documents.layout import Word
from openfactsheet.documents.ocr import group_lines
from openfactsheet.documents.tables import repair_numeric
from openfactsheet.exceptions import OCRExtractionError
from tests.fixtures.ocr_fake import FakeEngine, items_to_words
from tests.fixtures.pdf_writer import monthly_table_page

PIL = pytest.importorskip("PIL.Image")

Row = tuple[int, list[str | None], str | None]
FULL = ["0.10%", "0.20%", "-2.50%", "1.00%", "1.50%", "0.30%",
        "-0.40%", "0.80%", "0.90%", "-1.10%", "2.20%", "0.60%"]  # fmt: skip
REPAIRS = {"O": "0", "o": "0", "l": "1", "I": "1", "|": "1"}


def _ytd(cells: list[str | None]) -> str:
    vals = [float(c.rstrip("%")) for c in cells if c]
    return f"{(np.prod([1 + v / 100 for v in vals]) - 1) * 100:.2f}%"


def _rows() -> list[Row]:
    y2022: list[str | None] = [None, None, None, *FULL[3:]]
    y2024: list[str | None] = ["1.00%", "-0.50%", "0.70%", *[None] * 9]
    return [
        (2022, y2022, _ytd(y2022)),
        (2023, list(FULL), _ytd(list(FULL))),
        (2024, y2024, _ytd(y2024)),
    ]


def _image(tmp_path: Path) -> Path:
    path = tmp_path / "table.png"
    PIL.new("RGB", (40, 20), "white").save(path)
    return path


def _analyze(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, words: list[Word]
) -> ofs.FactsheetReport:
    monkeypatch.setattr(ocr_module, "get_engine", lambda name=None: FakeEngine(words))
    return ofs.analyze(_image(tmp_path))


def test_clean_recognition_is_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rep = _analyze(tmp_path, monkeypatch, items_to_words(monthly_table_page(_rows())))
    s = rep.returns_frame()
    assert len(s) == 24
    assert str(s.index[0].date()) == "2022-04-30"
    ex = rep.provenance.extraction
    assert ex is not None
    assert ex["confidence"] == "high"
    assert ex["engine"] == "fake 1"
    assert ex["ocr"]["models"][0]["sha256"] == "0" * 64
    assert len(ex["image_sha256"]) == 64
    assert ex["min_cell_confidence"] == pytest.approx(0.99)
    assert "OCR of an image" in rep.input_summary.to_text()


def test_same_metrics_as_manual_series(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rep = _analyze(tmp_path, monkeypatch, items_to_words(monthly_table_page(_rows())))
    manual = ofs.analyze(rep.returns_frame(), name=rep.name)
    for m in manual.metrics:
        assert rep.metrics[m.id].value == m.value, m.id


def test_low_confidence_cell_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    words = items_to_words(
        monthly_table_page(_rows()), alter=lambda t: (t, 0.6 if t == "-2.50%" else 0.99)
    )
    with pytest.raises(OCRExtractionError) as err:
        _analyze(tmp_path, monkeypatch, words)
    assert "confidence below 0.90" in str(err.value)
    assert "Mar 2023 (0.60)" in str(err.value)
    assert "Reconstructed table" in str(err.value)


def test_dropped_minus_sign_is_caught_by_the_total(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    words = items_to_words(
        monthly_table_page(_rows()), alter=lambda t: ("2.50%" if t == "-2.50%" else t, 0.99)
    )
    with pytest.raises(OCRExtractionError, match="compound to"):
        _analyze(tmp_path, monkeypatch, words)


def test_character_repair_is_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    words = items_to_words(
        monthly_table_page(_rows()), alter=lambda t: ("l.00%" if t == "1.00%" else t, 0.99)
    )
    rep = _analyze(tmp_path, monkeypatch, words)
    ex = rep.provenance.extraction
    assert ex is not None
    assert ex["confidence"] == "moderate"
    assert any("'l.00%' as '1.00%'" in r for r in ex["repairs"])
    assert any("repaired" in w for w in rep.input_summary.warnings)


def test_total_column_is_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    words = items_to_words(monthly_table_page(_rows(), ytd_header=None))
    with pytest.raises(OCRExtractionError, match="need a YTD / total column"):
        _analyze(tmp_path, monkeypatch, words)


def test_every_year_needs_a_total(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = _rows()
    rows[2] = (2024, rows[2][1], None)
    with pytest.raises(OCRExtractionError, match="2024 have no total cell"):
        _analyze(tmp_path, monkeypatch, items_to_words(monthly_table_page(rows)))


def test_misread_month_header_is_placed_by_spacing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    words = items_to_words(
        monthly_table_page(_rows()), alter=lambda t: ("lnf" if t == "Jul" else t, 0.99)
    )
    rep = _analyze(tmp_path, monkeypatch, words)
    assert any("Jul were not recognized" in w for w in rep.input_summary.warnings)
    assert rep.input_summary.observations == 24


def test_too_many_misread_headers_find_no_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = {"Jan", "Mar", "May", "Jul"}
    words = items_to_words(
        monthly_table_page(_rows()), alter=lambda t: ("xx" if t in bad else t, 0.99)
    )
    with pytest.raises(OCRExtractionError, match="No monthly-return table"):
        _analyze(tmp_path, monkeypatch, words)


def test_repair_numeric_only_changes_what_it_must() -> None:
    assert repair_numeric("1.20%", REPAIRS) == "1.20%"
    assert repair_numeric("O.5O%", REPAIRS) == "0.50%"
    assert repair_numeric("–1.5", REPAIRS) == "-1.5"
    assert repair_numeric("abc", REPAIRS) == "abc"  # left for validation to reject


def test_group_lines_tolerates_jitter() -> None:
    words = [
        Word("b", 50, 60, 102, 120),
        Word("a", 10, 20, 100, 118),
        Word("c", 10, 20, 140, 158),
    ]
    lines = group_lines(words)
    assert [line.text for line in lines] == ["a b", "c"]


def test_unknown_engine_name() -> None:
    with pytest.raises(ofs.InputError, match="Unknown OCR engine"):
        ocr_module.get_engine("nope")
