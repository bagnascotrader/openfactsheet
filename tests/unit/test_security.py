"""Security regression tests (docs/audits/security_alpha_review.md).

Resource limits on untrusted input files and escaping of untrusted text in
rendered reports. Limits are lowered with ``monkeypatch`` so that no test needs
a huge file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import openfactsheet as ofs
from openfactsheet.exceptions import InputError, OCRExtractionError
from openfactsheet.input import limits
from openfactsheet.report import markdown

CSV = "date,ret\n2020-01-31,0.01\n2020-02-29,0.02\n2020-03-31,-0.01\n2020-04-30,0.0\n"


def test_limits_are_far_above_real_inputs() -> None:
    # Safety limits must never bind on a real return history or factsheet.
    assert limits.MAX_INPUT_FILE_BYTES >= 16 * 1024 * 1024
    assert limits.MAX_IMAGE_PIXELS >= 3 * 2480 * 3508  # three A4 pages at 300 dpi
    assert limits.MAX_PDF_PAGES >= 50


def test_oversized_file_is_refused_before_parsing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "returns.csv"
    path.write_text(CSV, encoding="utf-8")
    assert ofs.load(path).n == 4
    monkeypatch.setattr(limits, "MAX_INPUT_FILE_BYTES", 16)
    with pytest.raises(InputError, match="safety limit"):
        ofs.load(path)


def test_directory_is_not_read_as_a_file(tmp_path: Path) -> None:
    folder = tmp_path / "returns.csv"
    folder.mkdir()
    with pytest.raises(InputError, match="Not a regular file"):
        ofs.load(folder)


def test_oversized_pasted_text_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(limits, "MAX_INPUT_FILE_BYTES", 16)
    with pytest.raises(InputError, match="safety limit"):
        ofs.load(CSV)


def test_excel_package_expanding_beyond_limit_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("openpyxl")
    path = tmp_path / "returns.xlsx"
    pd.DataFrame(
        {"date": pd.date_range("2020-01-31", periods=4, freq="ME"), "r": [0.01] * 4}
    ).to_excel(path, index=False)
    assert ofs.load(path).n == 4
    monkeypatch.setattr(limits, "MAX_EXCEL_UNCOMPRESSED_BYTES", 100)
    with pytest.raises(InputError, match="expands to"):
        ofs.load(path)


def test_oversized_image_is_refused_before_decoding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_mod = pytest.importorskip("PIL.Image")
    path = tmp_path / "table.png"
    image_mod.new("RGB", (100, 100), "white").save(path)
    monkeypatch.setattr(limits, "MAX_IMAGE_PIXELS", 1_000)
    with pytest.raises(OCRExtractionError, match="image safety limit"):
        ofs.load(path)


def test_pillow_decompression_bomb_becomes_extraction_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_mod = pytest.importorskip("PIL.Image")
    path = tmp_path / "table.png"
    image_mod.new("RGB", (100, 100), "white").save(path)
    # Pillow raises DecompressionBombError above twice its own limit.
    monkeypatch.setattr(image_mod, "MAX_IMAGE_PIXELS", 1_000)
    with pytest.raises(OCRExtractionError, match="Could not open"):
        ofs.load(path)


def test_pdf_with_too_many_pages_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("pypdf")
    from tests.fixtures.pdf_writer import write_pdf

    path = write_pdf(tmp_path / "long.pdf", [[], [], []])
    monkeypatch.setattr(limits, "MAX_PDF_PAGES", 2)
    with pytest.raises(OCRExtractionError, match="3 pages"):
        ofs.load(path)


def test_oversized_pdf_page_render_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("pypdfium2")
    pytest.importorskip("PIL")
    from openfactsheet.documents.raster import render_pages
    from tests.fixtures.pdf_writer import write_pdf

    path = write_pdf(tmp_path / "scan.pdf", [[]])
    assert render_pages(path, [1], dpi=10)  # within the limit: rendered
    monkeypatch.setattr(limits, "MAX_IMAGE_PIXELS", 1_000)
    with pytest.raises(OCRExtractionError, match="page 1"):
        render_pages(path, [1], dpi=300)


def test_tesseract_timeout_becomes_extraction_error() -> None:
    pytest.importorskip("PIL")
    from PIL import Image

    from openfactsheet.documents.ocr.tesseract import TesseractEngine

    seen: dict[str, Any] = {}

    class _Hanging:
        class Output:
            DICT = "dict"

        @staticmethod
        def image_to_data(*args: Any, **kwargs: Any) -> Any:
            seen.update(kwargs)
            raise RuntimeError("Tesseract process timeout")

    engine = TesseractEngine.__new__(TesseractEngine)
    engine._tess = _Hanging()
    engine._lang = "eng"
    with pytest.raises(OCRExtractionError, match="did not finish"):
        engine.recognize(Image.new("RGB", (10, 10)))
    assert seen["timeout"] == limits.TESSERACT_TIMEOUT_SECONDS


HOSTILE = "<img src=x onerror=alert(1)>"


def _hostile_report() -> ofs.FactsheetReport:
    returns = pd.Series(
        [0.01, -0.02, 0.015, 0.005, -0.01, 0.03],
        index=pd.date_range("2025-01-31", periods=6, freq="ME"),
        name=HOSTILE,
    )
    return ofs.analyze(returns)


def test_untrusted_names_are_escaped_in_html() -> None:
    html = _hostile_report().to_html()
    assert HOSTILE not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html


def test_untrusted_names_are_escaped_in_markdown() -> None:
    md = _hostile_report().to_markdown()
    assert HOSTILE not in md
    assert "&lt;img src=x onerror=alert(1)&gt;" in md


def test_terminal_report_drops_control_sequences() -> None:
    returns = pd.Series(
        [0.01, -0.02, 0.015, 0.005, -0.01, 0.03],
        index=pd.date_range("2025-01-31", periods=6, freq="ME"),
        name="Fund\x1b]0;title\x07\x1b[2J\x9b31m",
    )
    text = ofs.analyze(returns).summary()
    assert not any(ch in text for ch in ("\x1b", "\x07", "\x9b"))
    assert "Fund" in text


def test_document_text_cannot_close_a_markdown_code_block() -> None:
    block = markdown._kv_block("cell ``` <b>raw</b> ```` end")
    fence = block[0].removesuffix("text")
    assert set(fence) == {"`"}
    assert len(fence) == 5
    assert block[-1] == fence
