from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import openfactsheet as ofs
from openfactsheet.exceptions import InputError, OCRExtractionError
from openfactsheet.input.values import parse_cell, parse_cells

EXAMPLES = Path(__file__).parents[3] / "examples"


@pytest.mark.parametrize(
    ("cell", "value", "pct"),
    [
        (0.012, 0.012, False),
        ("1.2", 1.2, False),
        ("1.2%", 1.2, True),
        (" -1.2 % ", -1.2, True),
        ("(0.5)", -0.5, False),
        ("−0.3", -0.3, False),
        ("1,5%", 1.5, True),
        (3, 3.0, False),
    ],
)
def test_parse_cell(cell: object, value: float, pct: bool) -> None:
    assert parse_cell(cell) == (pytest.approx(value), pct)


@pytest.mark.parametrize("cell", ["", "-", "n/a", "NaN", None, "—"])
def test_missing_cells(cell: object) -> None:
    v, _ = parse_cell(cell)
    assert math.isnan(v)


def test_unparseable_cell() -> None:
    with pytest.raises(InputError):
        parse_cell("abc")
    with pytest.raises(InputError):
        parse_cell(True)


def test_percent_hint_only_from_strings() -> None:
    assert parse_cells([0.01, 0.02])[1] is None
    assert parse_cells(["1%", "2"])[1] is True
    assert parse_cells(["1", "2"])[1] is False


def test_numpy_and_tuple_inputs() -> None:
    a = ofs.load(np.array([0.01, 0.02, -0.01]))
    b = ofs.load((0.01, 0.02, -0.01))
    assert isinstance(a, ofs.ReturnSeries) and isinstance(b, ofs.ReturnSeries)
    np.testing.assert_array_equal(a.values, b.values)
    assert a.source_type == "numpy.ndarray"


def test_two_dimensional_array_rejected() -> None:
    with pytest.raises(InputError):
        ofs.load(np.zeros((3, 2)))


def test_monthly_table_csv_reconstruction() -> None:
    series = ofs.load(EXAMPLES / "monthly_table.csv")
    assert isinstance(series, ofs.ReturnSeries)
    assert series.n == 33  # three future months of 2024 are empty and trimmed
    assert series.dates is not None
    assert series.dates[0] == pd.Timestamp("2022-01-31")
    assert series.dates[-1] == pd.Timestamp("2024-09-30")
    assert series.return_scale == "detected_percent"
    diag = series.input_diagnostics
    assert diag is not None
    assert any("YTD" in t for t in diag.transformations)


def test_pasted_monthly_table_text() -> None:
    text = """
    Year  Jan   Feb   Mar   Apr   May   Jun   Jul   Aug   Sep   Oct   Nov   Dec
    2022  1.2% -0.3%  0.5%  2.0% -1.1%  0.4%  0.9%  1.1% -2.0%  0.3%  0.6%  1.0%
    2023  0.8%  0.2% -0.4%  1.5%  0.7% -0.9%  1.3%
    """
    series = ofs.load(text)
    assert isinstance(series, ofs.ReturnSeries)
    assert series.n == 19
    assert series.values[0] == pytest.approx(0.012)
    assert series.dates is not None and series.dates[-1] == pd.Timestamp("2023-07-31")


def test_dataframe_with_date_column_and_multiple_series() -> None:
    df = pd.DataFrame(
        {
            "Date": ["2020-01-31", "2020-02-29", "2020-03-31"],
            "Fund A": [0.01, 0.02, -0.01],
            "Fund B": [0.00, 0.01, 0.02],
        }
    )
    table = ofs.load(df)
    assert isinstance(table, ofs.ReturnTable)
    assert set(table.series) == {"Fund A", "Fund B"}
    with pytest.raises(InputError, match="compare"):
        ofs.analyze(df)


def test_percent_column_header() -> None:
    df = pd.DataFrame(
        {"date": ["2020-01-31", "2020-02-29", "2020-03-31"], "Return (%)": [0.1, 0.2, 0.1]}
    )
    series = ofs.load(df)
    assert isinstance(series, ofs.ReturnSeries)
    assert series.return_scale == "detected_percent"


def test_missing_file() -> None:
    with pytest.raises(InputError, match="not found"):
        ofs.load("does_not_exist.csv")


def test_images_and_pdfs_explain_roadmap(tmp_path: Path) -> None:
    img = tmp_path / "table.png"
    img.write_bytes(b"\x89PNG")
    with pytest.raises(OCRExtractionError, match="planned"):
        ofs.load(img)
    pdf = tmp_path / "factsheet.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    with pytest.raises(OCRExtractionError):
        ofs.load(pdf)


def test_excel_roundtrip(tmp_path: Path) -> None:
    pytest.importorskip("openpyxl")
    path = tmp_path / "returns.xlsx"
    pd.DataFrame(
        {"date": pd.date_range("2020-01-31", periods=4, freq="ME"), "ret": [0.01, 0.02, -0.01, 0.0]}
    ).to_excel(path, index=False)
    series = ofs.load(path)
    assert isinstance(series, ofs.ReturnSeries)
    assert series.frequency is ofs.ObservationFrequency.MONTHLY
    assert series.n == 4


def test_unsupported_type() -> None:
    with pytest.raises(InputError):
        ofs.load({1, 2, 3})
