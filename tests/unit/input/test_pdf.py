"""Monthly-return tables from text PDFs (decision 0030)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import openfactsheet as ofs
from openfactsheet.exceptions import InputError, OCRExtractionError
from tests.fixtures.pdf_writer import MONTHS, monthly_table_page, write_pdf

pytest.importorskip("pypdf")

Row = tuple[int, list[str | None], str | None]

FULL_2023 = ["0.10%", "0.20%", "-2.50%", "1.00%", "1.50%", "0.30%",
             "-0.40%", "0.80%", "0.90%", "-1.10%", "2.20%", "0.60%"]  # fmt: skip


def _ytd(cells: list[str | None], decimals: int = 2, pct: bool = True) -> str:
    vals = [float(c.rstrip("%")) for c in cells if c]
    total = (np.prod([1 + v / 100 for v in vals]) - 1) * 100
    return f"{total:.{decimals}f}" + ("%" if pct else "")


def _rows() -> list[Row]:
    y2022: list[str | None] = [None, None, None, "1.20%", "-0.30%", "0.50%", "2.10%", "-1.00%",
                               "0.00%", "1.10%", "0.40%", "-0.20%"]  # fmt: skip
    y2024: list[str | None] = ["1.00%", "-0.50%", "0.70%", *[None] * 9]
    return [
        (2022, y2022, _ytd(y2022)),
        (2023, list(FULL_2023), _ytd(list(FULL_2023))),
        (2024, y2024, _ytd(y2024)),
    ]


def _pdf(tmp_path: Path, rows: list[Row], name: str = "fund.pdf", **kwargs: object) -> Path:
    return write_pdf(tmp_path / name, [monthly_table_page(rows, **kwargs)])  # type: ignore[arg-type]


def test_reconstructs_chronology_from_column_positions(tmp_path: Path) -> None:
    rep = ofs.analyze(_pdf(tmp_path, _rows()))
    s = rep.returns_frame()
    assert s.index[0] == pd.Timestamp("2022-04-30")  # first value sits under April
    assert s.index[-1] == pd.Timestamp("2024-03-31")
    assert len(s) == 24
    assert s.iloc[0] == pytest.approx(0.012)
    assert rep.input_summary.return_scale == "detected_percent"
    assert rep.input_summary.source_type == "pdf (monthly table)"
    assert rep.name == "fund"
    ex = rep.provenance.extraction
    assert ex is not None
    assert ex["confidence"] == "high"
    assert ex["page"] == 1
    assert ex["engine"].startswith("pypdf ")
    assert len(ex["source_sha256"]) == 64
    assert len(ex["checks"]) == 3
    assert "extracted from embedded PDF text" in rep.input_summary.to_text()
    for text in (rep.summary(), rep.to_markdown(), rep.to_html()):
        assert "Reconstructed table" in text
        assert "-2.50%" in text  # the table exactly as read is shown in every renderer
    assert json.loads(rep.to_json())["provenance"]["extraction"]["monthly_values"] == 24


def test_same_metrics_as_manually_supplied_series(tmp_path: Path) -> None:
    """CLAUDE.md acceptance test 4: identical metrics to the same series supplied directly."""
    rep_pdf = ofs.analyze(_pdf(tmp_path, _rows()))
    manual = rep_pdf.returns_frame().rename("fund")
    rep_manual = ofs.analyze(manual, name="fund")
    for m in rep_manual.metrics:
        assert rep_pdf.metrics[m.id].value == m.value, m.id
        assert rep_pdf.metrics[m.id].status == m.status, m.id


def test_newest_year_first_is_sorted(tmp_path: Path) -> None:
    rep = ofs.analyze(_pdf(tmp_path, list(reversed(_rows()))))
    assert rep.returns_frame().index.is_monotonic_increasing
    assert rep.input_summary.observations == 24


def test_ytd_mismatch_is_refused_with_the_reconstructed_table(tmp_path: Path) -> None:
    rows = _rows()
    rows[1] = (2023, rows[1][1], "9.99%")
    with pytest.raises(OCRExtractionError) as err:
        ofs.analyze(_pdf(tmp_path, rows))
    text = str(err.value)
    assert "could not be read reliably" in text
    assert "9.99%" in text
    assert "Reconstructed table" in text


def test_value_outside_any_column_is_refused(tmp_path: Path) -> None:
    rows = _rows()
    # A stray number far to the right of the last column (no YTD column), on a data row.
    page = monthly_table_page(rows, ytd_header=None, extra=[(800.0, 480.0 - 16.0 * 2, "1.5")])
    with pytest.raises(OCRExtractionError, match="not under any column header"):
        ofs.analyze(write_pdf(tmp_path / "x.pdf", [page]))


def test_without_ytd_column_confidence_is_moderate(tmp_path: Path) -> None:
    rep = ofs.analyze(_pdf(tmp_path, _rows(), ytd_header=None))
    ex = rep.provenance.extraction
    assert ex is not None
    assert ex["confidence"] == "moderate"
    assert any("could not be cross-checked" in w for w in rep.input_summary.warnings)


def test_interior_gap_is_missing_never_zero(tmp_path: Path) -> None:
    cells = list(FULL_2023)
    cells[5] = None  # June 2023 blank
    rows: list[Row] = [(2023, cells, _ytd(cells)), (2024, ["1.00%", *[None] * 11], "1.00%")]
    rep = ofs.analyze(_pdf(tmp_path, rows))
    assert pd.Timestamp("2023-06-30") not in rep.returns_frame().index
    assert rep.input_summary.observations == 12
    assert any("Jun 2023" in w for w in rep.input_summary.warnings)


def test_percent_label_in_title_without_percent_signs(tmp_path: Path) -> None:
    cells = [c.rstrip("%") if c else None for c in FULL_2023]
    rows: list[Row] = [(2023, cells, _ytd(cells, pct=False))]
    rep = ofs.analyze(_pdf(tmp_path, rows, title="Monthly returns (%)"))
    assert rep.input_summary.return_scale == "detected_percent"
    assert rep.returns_frame().iloc[2] == pytest.approx(-0.025)


def test_decimal_values_without_labels(tmp_path: Path) -> None:
    cells: list[str | None] = [f"{float(c.rstrip('%')) / 100:.4f}" for c in FULL_2023]
    total = np.prod([1 + float(c) for c in cells if c]) - 1
    rows: list[Row] = [(2023, cells, f"{total:.4f}")]
    rep = ofs.analyze(_pdf(tmp_path, rows, title="Monthly returns"))
    assert rep.input_summary.return_scale == "detected_decimal"
    assert rep.provenance.extraction["confidence"] == "high"  # type: ignore[index]


def test_accounting_negatives(tmp_path: Path) -> None:
    cells: list[str | None] = [f"({c[1:]})" if c and c.startswith("-") else c for c in FULL_2023]
    rows: list[Row] = [(2023, cells, _ytd(list(FULL_2023)))]
    rep = ofs.analyze(_pdf(tmp_path, rows))
    assert rep.returns_frame().iloc[2] == pytest.approx(-0.025)


def test_two_tables_become_two_series(tmp_path: Path) -> None:
    fund = monthly_table_page(_rows(), top=480.0, title="Fund (%)")
    bench = monthly_table_page(_rows()[1:], top=250.0, title="Benchmark (%)")
    path = write_pdf(tmp_path / "two.pdf", [[*fund, *bench]])
    loaded = ofs.load(path)
    assert isinstance(loaded, ofs.ReturnTable)
    assert len(loaded.series) == 2
    # Decision 0033: the benchmark table is recognized by its caption, so analyze() uses the
    # fund table and says the benchmark returns were not used.
    rep = ofs.analyze(path)
    assert rep.input_summary.observations == 24
    assert any("not used" in w for w in rep.input_summary.warnings)
    # Two fund tables (e.g. two share classes) are still for the caller to choose.
    other = monthly_table_page(_rows()[1:], top=250.0, title="Class I (%)")
    two_funds = write_pdf(tmp_path / "two_funds.pdf", [[*fund, *other]])
    with pytest.raises(InputError, match="contains 2 return series"):
        ofs.analyze(two_funds)


def test_table_on_a_later_page(tmp_path: Path) -> None:
    cover = [(60.0, 500.0, "Example Fund Factsheet"), (60.0, 480.0, "For professional investors")]
    path = write_pdf(tmp_path / "multi.pdf", [cover, monthly_table_page(_rows())])
    rep = ofs.analyze(path)
    assert rep.provenance.extraction["page"] == 2  # type: ignore[index]


def test_full_month_names(tmp_path: Path) -> None:
    names = ["January", "February", "March", "April", "May", "June", "July", "August",
             "September", "October", "November", "December"]  # fmt: skip
    page = monthly_table_page(_rows(), col=62.0)
    page = [(x, y, names[MONTHS.index(t)] if t in MONTHS else t) for x, y, t in page]
    rep = ofs.analyze(write_pdf(tmp_path / "long.pdf", [page]))
    assert rep.input_summary.observations == 24


def test_pdf_without_table_or_text(tmp_path: Path) -> None:
    no_table = write_pdf(tmp_path / "text.pdf", [[(60.0, 500.0, "Quarterly letter")]])
    with pytest.raises(OCRExtractionError, match="No monthly-return table"):
        ofs.analyze(no_table)
    scanned = write_pdf(tmp_path / "scan.pdf", [[]])
    with pytest.raises(OCRExtractionError, match="no embedded text"):
        ofs.analyze(scanned)


def test_not_a_pdf(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf at all")
    with pytest.raises(OCRExtractionError, match="Could not open"):
        ofs.analyze(bad)
