"""Fund profile extraction from factsheets (decision 0032)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import openfactsheet as ofs
from openfactsheet.documents.layout import PageLayout
from openfactsheet.documents.profile import extract_profile
from openfactsheet.documents.text_pdf import tokenize
from tests.fixtures.pdf_writer import TextItem, monthly_table_page, write_pdf

pytest.importorskip("pypdf")

FULL = ["0.10%", "0.20%", "-2.50%", "1.00%", "1.50%", "0.30%",
        "-0.40%", "0.80%", "0.90%", "-1.10%", "2.20%", "0.60%"]  # fmt: skip


def _ytd(cells: list[str]) -> str:
    return f"{(np.prod([1 + float(c.rstrip('%')) / 100 for c in cells]) - 1) * 100:.2f}%"


def _layout(*lines: str) -> PageLayout:
    return PageLayout(1, tuple(tokenize(line) for line in lines), "text", "test")


def _factsheet(tmp_path: Path, header: list[str]) -> Path:
    items: list[TextItem] = [(60.0, 560.0 - 14.0 * i, text) for i, text in enumerate(header)]
    rows = [(2023, list(FULL), _ytd(FULL))]
    page = monthly_table_page(rows, top=250.0, extra=items, title="Monthly net returns (%)")
    return write_pdf(tmp_path / "factsheet.pdf", [page])


def test_labelled_fields_with_evidence() -> None:
    profile = extract_profile(
        [
            _layout(
                "Example Global Equity Fund",
                "ISIN: LU0048578792    WKN: 986838",
                "Fund currency: EUR",
                "Launch date: 15.03.2011",
                "Benchmark: MSCI World Net Total Return EUR",
                "Investment objective",
                "The fund seeks long-term capital growth by investing",
                "in global equities.",
                "",
                "Risk indicator 4",
            )
        ],
        "factsheet.pdf",
    )
    assert profile.name is not None
    assert profile.name.value == "Example Global Equity Fund"
    assert profile.name.confidence == "moderate"  # a title line, not a label
    assert profile.name.evidence.rule == "title line"
    kinds = {(i.kind, i.value, i.valid) for i in profile.identifiers}
    assert ("ISIN", "LU0048578792", True) in kinds
    assert ("WKN", "986838", None) in kinds
    assert profile.currency is not None
    assert profile.currency.value == "EUR"
    assert profile.launch_date is not None
    assert profile.launch_date.value == "2011-03-15"  # dotted dates are day-first
    assert [b.value for b in profile.benchmarks] == ["MSCI World Net Total Return EUR"]
    assert profile.objective is not None
    assert profile.objective.value == (
        "The fund seeks long-term capital growth by investing in global equities."
    )
    assert profile.objective.evidence.line == 6


def test_fund_name_label_beats_title_and_other_languages() -> None:
    profile = extract_profile(
        [
            _layout(
                "Monatsbericht",
                "Fondsname: Beispiel Rentenfonds",
                "Anlageziel: Ertrag aus Anleihen.",
                "Vergleichsindex: Bloomberg Euro Aggregate",
                "Fondswährung: EUR",
                "ISIN DE0007164600 WKN 716460",
            )
        ],
        "x.pdf",
    )
    assert profile.name is not None
    assert (profile.name.value, profile.name.confidence) == ("Beispiel Rentenfonds", "high")
    assert profile.objective is not None
    assert profile.objective.value == "Ertrag aus Anleihen."
    assert [b.value for b in profile.benchmarks] == ["Bloomberg Euro Aggregate"]
    assert profile.currency is not None
    assert profile.currency.value == "EUR"
    wkn = next(i for i in profile.identifiers if i.kind == "WKN")
    assert wkn.linked_isin == "DE0007164600"  # the DE ISIN embeds the WKN


def test_invalid_labelled_isin_is_reported_not_corrected() -> None:
    profile = extract_profile([_layout("ISIN: LU0048578793")], "x.pdf")
    (ident,) = profile.identifiers
    assert ident.valid is False
    assert profile.valid_identifiers() == ()
    assert any("fails its check digit" in n for n in profile.notes)


def test_unlabelled_invalid_isin_shaped_text_is_ignored() -> None:
    profile = extract_profile([_layout("Ref AB1234567890 in the text")], "x.pdf")
    assert profile.identifiers == ()


def test_wkn_conflicting_with_isin_is_noted() -> None:
    profile = extract_profile([_layout("ISIN DE0007164600", "WKN 123456")], "x.pdf")
    assert any("does not match the WKN embedded" in n for n in profile.notes)


def test_ambiguous_slash_date_is_kept_as_printed() -> None:
    profile = extract_profile([_layout("Inception date: 03/04/2012")], "x.pdf")
    assert profile.launch_date is not None
    assert profile.launch_date.value == "03/04/2012"
    assert profile.launch_date.confidence == "low"
    unambiguous = extract_profile([_layout("Inception date: 25/04/2012")], "x.pdf")
    assert unambiguous.launch_date is not None
    assert unambiguous.launch_date.value == "2012-04-25"


def test_profile_in_every_renderer_and_json(tmp_path: Path) -> None:
    pdf = _factsheet(
        tmp_path,
        [
            "Example Global Equity Fund",
            "ISIN: LU0048578792",
            "Benchmark: MSCI World NR EUR",
            "Investment objective: long-term growth.",
        ],
    )
    rep = ofs.analyze(pdf)
    assert rep.document is not None
    assert rep.document.name is not None
    assert rep.document.name.value == "Example Global Equity Fund"
    for text in (rep.summary(), rep.to_markdown(), rep.to_html()):
        assert "Example Global Equity Fund" in text
        assert "LU0048578792" in text
        assert "MSCI World NR EUR" in text  # named, with the note that it was not used
        assert "its returns were not supplied" in text
    data = json.loads(rep.to_json())
    assert data["document"]["identifiers"][0]["value"] == "LU0048578792"
    assert data["document"]["name"]["evidence"]["page"] == 1
    # The profile never changes a metric.
    manual = ofs.analyze(rep.returns_frame(), name=rep.name)
    for m in manual.metrics:
        assert rep.metrics[m.id].value == m.value, m.id


def test_benchmark_note_absent_when_benchmark_supplied(tmp_path: Path) -> None:
    pdf = _factsheet(tmp_path, ["Benchmark: MSCI World NR EUR"])
    fund = ofs.load(pdf)
    assert isinstance(fund, ofs.ReturnSeries)
    bench = fund.to_pandas() * 0.9
    rep = ofs.analyze(fund, benchmark=bench)
    assert "its returns were not supplied" not in rep.summary()


def test_non_document_inputs_have_no_profile() -> None:
    rep = ofs.analyze([0.01, -0.02, 0.03])
    assert rep.document is None
    assert json.loads(rep.to_json())["document"] is None
