"""Real OCR engine tests (marker ``ocr``; need ``pip install "openfactsheet[ocr]"``).

CLAUDE.md acceptance test 4: a screenshot of a monthly-return table gives the same
metrics as the same series supplied directly; recognition never uses the network.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

import numpy as np
import pytest

import openfactsheet as ofs
from tests.fixtures.pdf_writer import monthly_table_page, write_pdf

pytestmark = pytest.mark.ocr
if os.environ.get("OFS_REQUIRE_OCR"):  # the CI OCR job must not skip silently
    import pypdfium2 as pdfium
    import rapidocr  # noqa: F401
    from PIL import Image as PIL
else:
    pytest.importorskip("rapidocr")
    pdfium = pytest.importorskip("pypdfium2")
    PIL = pytest.importorskip("PIL.Image")

Row = tuple[int, list[str | None], str | None]
FULL = ["0.10%", "0.20%", "-2.50%", "1.00%", "1.50%", "0.30%",
        "-0.40%", "0.80%", "0.90%", "-1.10%", "2.20%", "0.60%"]  # fmt: skip


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


def _screenshot(tmp_path: Path, dpi: int = 300) -> Path:
    pdf = write_pdf(tmp_path / "table.pdf", [monthly_table_page(_rows())])
    doc = pdfium.PdfDocument(str(pdf))
    image = doc[0].render(scale=dpi / 72).to_pil().convert("RGB")
    doc.close()
    path = tmp_path / "table.png"
    image.save(path)
    return path


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("OCR attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def test_screenshot_gives_identical_metrics(tmp_path: Path, no_network: None) -> None:
    rep = ofs.analyze(_screenshot(tmp_path))
    truth = [
        *[float(c.rstrip("%")) / 100 for c in FULL[3:]],
        *[float(c.rstrip("%")) / 100 for c in FULL],
    ]
    truth += [0.01, -0.005, 0.007]
    np.testing.assert_allclose(rep.returns_frame().to_numpy(), truth, rtol=0, atol=1e-12)
    manual = ofs.analyze(rep.returns_frame(), name=rep.name)
    for m in manual.metrics:
        assert rep.metrics[m.id].value == m.value, m.id
    ex = rep.provenance.extraction
    assert ex is not None
    assert ex["ocr"]["name"] == "rapidocr"
    assert all(len(m["sha256"]) == 64 for m in ex["ocr"]["models"])
    assert ex["confidence"] in ("high", "moderate")


def test_scanned_pdf_is_recognized(tmp_path: Path, no_network: None) -> None:
    png = _screenshot(tmp_path)
    scanned = tmp_path / "scanned.pdf"
    with PIL.open(png) as image:
        image.save(scanned, "PDF", resolution=300.0)
    rep = ofs.analyze(scanned)
    assert rep.input_summary.observations == 24
    assert "OCR of a scanned PDF page" in rep.input_summary.to_text()
    ex = rep.provenance.extraction
    assert ex is not None
    assert ex["renderer"].startswith("pypdfium2")
    assert ex["dpi"] == 300


def test_low_resolution_is_refused_or_exact(tmp_path: Path) -> None:
    """A poor scan may be refused, but an accepted one must carry the printed values."""
    path = _screenshot(tmp_path, dpi=60)
    refusal: str | None = None
    try:
        rep = ofs.analyze(path)
    except ofs.OCRExtractionError as err:
        refusal = str(err)
    if refusal is not None:
        assert "Reconstructed table" in refusal or "No monthly-return table" in refusal
        return
    assert rep.input_summary.observations == 24
    assert rep.returns_frame().iloc[5] == pytest.approx(-0.004)
