"""Table roles, benchmark rows and share-class attribution (decision 0033)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import openfactsheet as ofs
from openfactsheet.documents.layout import PageLayout
from openfactsheet.documents.share_classes import ShareClass, attribute, detect_share_classes
from openfactsheet.documents.tables import classify_role
from openfactsheet.documents.text_pdf import tokenize
from tests.fixtures.pdf_writer import MONTHS, TextItem, monthly_table_page, write_pdf

pytest.importorskip("pypdf")

FUND = ["0.10%", "0.20%", "-2.50%", "1.00%", "1.50%", "0.30%",
        "-0.40%", "0.80%", "0.90%", "-1.10%", "2.20%", "0.60%"]  # fmt: skip
BENCH = ["0.30%", "0.10%", "-2.00%", "0.80%", "1.20%", "0.10%",
         "-0.60%", "0.90%", "0.70%", "-0.90%", "1.80%", "0.40%"]  # fmt: skip


def _ytd(cells: list[str]) -> str:
    return f"{(np.prod([1 + float(c.rstrip('%')) / 100 for c in cells]) - 1) * 100:.2f}%"


def _diff(a: list[str], b: list[str]) -> list[str]:
    return [
        f"{float(x.rstrip('%')) - float(y.rstrip('%')):.2f}%" for x, y in zip(a, b, strict=True)
    ]


def _labelled_table(
    rows: list[tuple[int | None, str, list[str], str]],
    *,
    top: float = 400.0,
    title: str = "Monthly net returns (%)",
    extra: list[TextItem] | None = None,
) -> list[TextItem]:
    """A table whose rows carry a series label between the year and January."""
    x0, col, rh = 60.0, 52.0, 16.0

    def right(x: float, text: str) -> float:
        return x - 4.6 * len(text)

    items: list[TextItem] = [(x0, top + 40, title), *(extra or [])]
    items += [(right(x0 + col * (j + 2), m), top, m) for j, m in enumerate(MONTHS)]
    items.append((right(x0 + col * 14, "YTD"), top, "YTD"))
    for i, (year, label, cells, total) in enumerate(rows):
        y = top - rh * (i + 1)
        if year is not None:
            items.append((x0 - 30, y, str(year)))
        items.append((x0 + 2, y, label))
        items += [(right(x0 + col * (j + 2), c), y, c) for j, c in enumerate(cells)]
        items.append((right(x0 + col * 14, total), y, total))
    return items


def _pdf(tmp_path: Path, items: list[TextItem], name: str = "sheet.pdf") -> Path:
    return write_pdf(tmp_path / name, [items])


def test_fund_and_benchmark_rows(tmp_path: Path) -> None:
    items = _labelled_table(
        [(2023, "Fund", FUND, _ytd(FUND)), (None, "Benchmark", BENCH, _ytd(BENCH))]
    )
    path = _pdf(tmp_path, items)
    rep = ofs.analyze(path)
    assert rep.returns_frame().iloc[2] == pytest.approx(-0.025)  # the fund row, not the index
    assert any("benchmark returns" in w and "not used" in w for w in rep.input_summary.warnings)
    assert rep.benchmark_summary is None  # never used automatically
    loaded = ofs.load(path)
    assert isinstance(loaded, ofs.ReturnTable)
    names = list(loaded.series)
    assert names == ["sheet", "Benchmark (benchmark, from document)"]
    bench = loaded.series[names[1]]
    assert bench.values[2] == pytest.approx(-0.02)
    explicit = ofs.analyze(loaded.series["sheet"], benchmark=bench)
    assert explicit.metrics["beta"].value is not None


def test_relative_row_is_ignored(tmp_path: Path) -> None:
    rel = _diff(FUND, BENCH)
    items = _labelled_table(
        [
            (2023, "Fund", FUND, _ytd(FUND)),
            (None, "Index", BENCH, _ytd(BENCH)),
            (None, "Relative", rel, "0.90%"),
        ]
    )
    rep = ofs.analyze(_pdf(tmp_path, items))
    assert rep.input_summary.observations == 12
    assert any("relative returns" in w for w in rep.input_summary.warnings)


def test_benchmark_only_table_is_not_analyzed_as_the_fund(tmp_path: Path) -> None:
    page = monthly_table_page(
        [(2023, list(BENCH), _ytd(BENCH))], title="Benchmark monthly returns (%)"
    )
    path = write_pdf(tmp_path / "bench.pdf", [page])
    with pytest.raises(ofs.InputError, match="labelled as benchmark returns"):
        ofs.analyze(path)
    loaded = ofs.load(path)
    assert isinstance(loaded, ofs.ReturnSeries)  # still available explicitly


def test_unreliable_benchmark_row_is_left_out_with_a_note(tmp_path: Path) -> None:
    items = _labelled_table([(2023, "Fund", FUND, _ytd(FUND)), (None, "Benchmark", BENCH, "9.99%")])
    rep = ofs.analyze(_pdf(tmp_path, items))
    assert rep.input_summary.observations == 12
    assert any("could not be read reliably" in w for w in rep.input_summary.warnings)


@pytest.mark.parametrize(
    ("label", "role"),
    [
        ("Fund", "fund"),
        ("Class A EUR", "fund"),
        ("Benchmark", "benchmark"),
        ("MSCI World", "benchmark"),
        ("Index", "benchmark"),
        ("Relative", "relative"),
        ("Difference", "relative"),
        ("Peers", "unknown"),
    ],
)
def test_classify_role(label: str, role: str) -> None:
    assert classify_role(label, (), 2)[0] == role


def _layout(*lines: str) -> PageLayout:
    return PageLayout(1, tuple(tokenize(line) for line in lines), "text", "test")


CLASS_TABLE = (
    "Share class           ISIN            Currency",
    "A EUR Acc             LU0048578792    EUR",
    "I USD Dist            LU0011963245    USD",
    "",
)


def test_detect_classes_from_class_table() -> None:
    classes = detect_share_classes([_layout(*CLASS_TABLE)])
    assert [(c.label, c.isins, c.currency) for c in classes] == [
        ("A EUR Acc", ("LU0048578792",), "EUR"),
        ("I USD Dist", ("LU0011963245",), "USD"),
    ]


def test_detect_classes_from_labelled_lines() -> None:
    classes = detect_share_classes(
        [_layout("Class B CHF Hedged  ISIN: LU0011963245", "Share class C", "ISIN LU0048578792")]
    )
    assert {c.label for c in classes} == {"B CHF Hedged", "C"}


def _classes() -> list[ShareClass]:
    return detect_share_classes([_layout(*CLASS_TABLE)])


def test_caption_names_the_class() -> None:
    att = attribute(_classes(), ["Performance of Class I USD Dist (%)"], [], [])
    assert (att.status, att.share_class, att.rule) == (
        "attributed",
        "I USD Dist",
        "caption or footnote names the class",
    )


def test_footnote_isin_names_the_class() -> None:
    att = attribute(_classes(), ["Monthly returns"], ["Returns of ISIN LU0048578792, net."], [])
    assert att.share_class == "A EUR Acc"


def test_currency_rule() -> None:
    att = attribute(_classes(), ["Monthly returns in USD"], [], [])
    assert (att.share_class, att.rule) == ("I USD Dist", "only class in USD")


def test_no_evidence_is_ambiguous_never_a_guess() -> None:
    att = attribute(_classes(), ["Monthly returns"], [], [])
    assert att.status == "ambiguous"
    assert att.share_class is None
    assert att.candidates == ("A EUR Acc", "I USD Dist")


def test_conflicting_rules_are_ambiguous() -> None:
    att = attribute(
        _classes(), ["Monthly returns, class A EUR Acc"], [], ["Performance of class I USD Dist"]
    )
    assert att.status == "ambiguous"
    assert set(att.candidates) == {"A EUR Acc", "I USD Dist"}


def test_single_class_and_no_class() -> None:
    one = detect_share_classes([_layout("Class A  ISIN LU0048578792")])
    assert attribute(one, [], [], []).rule == "single share class in the document"
    assert attribute([], [], [], []).status == "no_share_classes"


def test_attribution_in_report(tmp_path: Path) -> None:
    extra = [(60.0, 540.0 - 14 * i, line) for i, line in enumerate(CLASS_TABLE[:3])]
    page = monthly_table_page(
        [(2023, list(FUND), _ytd(FUND))],
        top=300.0,
        title="Performance of Class A EUR Acc (%)",
        extra=extra,
    )
    rep = ofs.analyze(write_pdf(tmp_path / "classes.pdf", [page]))
    assert rep.document is not None
    att = rep.document.attribution
    assert att is not None
    assert att.share_class == "A EUR Acc"
    text = rep.summary()
    assert "Returns table shows:       class A EUR Acc" in text
    assert "I USD Dist (LU0011963245)" in text
