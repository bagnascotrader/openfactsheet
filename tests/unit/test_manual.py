"""The reference manual (decision 0034): complete, linked, reproducible."""

from __future__ import annotations

import inspect
import os
import re
from pathlib import Path
from typing import Any

import pytest

import openfactsheet as ofs
from openfactsheet.manual import api_anchor, decision_anchor, metric_anchor
from openfactsheet.manual.export import manual_data, parse_docstring, prepare_markdown
from openfactsheet.metrics.registry import all_metrics

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def data() -> dict[str, Any]:
    return manual_data(ROOT)


def test_every_metric_is_a_topic_with_its_documentation(data: dict[str, Any]) -> None:
    records = {m["id"]: m for m in data["metrics"]["metrics"]}
    assert set(records) == {d.id for d in all_metrics()}
    for d in all_metrics():
        r = records[d.id]
        assert r["anchor"] == metric_anchor(d.id)
        assert r["formula_latex"] == d.docs.formula_latex
        assert r["annualized"] is d.annualized
        assert r["references"], d.id
        assert "When a value is produced" in r["criteria"]
    in_categories = [m for c in data["metrics"]["categories"] for m in c["metrics"]]
    assert sorted(in_categories) == sorted(records)


def test_decisions_that_discuss_a_metric_are_linked(data: dict[str, Any]) -> None:
    records = {m["id"]: m for m in data["metrics"]["metrics"]}
    assert "0008" in records["sharpe_ratio"]["decisions"]
    assert "0010" in records["var_historical_95"]["decisions"]


def test_every_public_name_is_documented(data: dict[str, Any]) -> None:
    anchors = {t["anchor"] for t in data["api"]["topics"]}
    for t in data["api"]["topics"]:
        anchors |= {c["anchor"] for c in t.get("classes", []) + t.get("constants", [])}
    for name in ofs.__all__:
        assert api_anchor(name) in anchors, name


def test_every_argument_of_every_public_function_and_method_is_documented(
    data: dict[str, Any],
) -> None:
    for t in data["api"]["topics"]:
        callables = [t] if t["kind"] == "function" else t.get("members", [])
        for c in callables:
            assert c["description"], (t["name"], c["name"])
            documented = {a["name"] for a in c["arguments"]}
            for p in c.get("parameters", []):
                assert p["name"] in documented, (t["name"], c["name"], p["name"])


def test_every_decision_note_is_in_the_manual(data: dict[str, Any]) -> None:
    numbers = {
        m.group(1)
        for p in (ROOT / "docs/methodology/decisions").glob("*.md")
        if (m := re.match(r"(\d{4})-", p.name))
    }
    anchors = {d["anchor"] for d in data["documents"]["documents"]}
    assert {decision_anchor(n) for n in numbers} <= anchors


def test_bibliography_is_deduplicated_and_cites_back(data: dict[str, Any]) -> None:
    entries = data["bibliography"]["entries"]
    keys = [e["key"] for e in entries]
    assert len(keys) == len(set(keys))
    citations = {e["citation"]: e for e in entries}
    for m in data["metrics"]["metrics"]:
        for ref in m["references"]:
            assert m["id"] in citations[ref["citation"]]["cited_by"]
    sharpe = next(e for e in entries if e["citation"].startswith("Sharpe, W. F. (1966)"))
    assert (sharpe["key"], sharpe["year"]) == ("sharpe1966", "1966")


def test_package_fields_come_from_pyproject(data: dict[str, Any]) -> None:
    pkg = data["package"]
    assert pkg["version"] == ofs.__version__
    assert pkg["methodology_version"] == ofs.METHODOLOGY_VERSION
    assert pkg["license"] == "Apache-2.0"
    assert "dev" not in pkg["extras"]
    assert pkg["urls"]["Homepage"].startswith("https://github.com/")


def test_google_docstrings_become_manual_sections() -> None:
    doc = inspect.cleandoc(
        """Short summary of :func:`load`.

        Longer ``details`` about :class:`Unknown`.

        Args:
            x: First line of a Benchmark-
                relative explanation.
            y (int): Second.

        Returns:
            The value.

        Examples:
            >>> f(1)
        """
    )
    parsed = parse_docstring(doc, {"load"})
    assert parsed["description"] == "Short summary of [`load()`](#api-load)."
    assert parsed["details"] == "Longer `details` about `Unknown`."
    assert parsed["arguments"] == [
        {"name": "x", "text": "First line of a Benchmark-relative explanation."},
        {"name": "y", "text": "Second."},
    ]
    assert parsed["value"] == "The value."
    assert parsed["examples"] == ">>> f(1)"


def _doc(data: dict[str, Any], anchor: str) -> dict[str, Any]:
    return next(d for d in data["documents"]["documents"] if d["anchor"] == anchor)


def test_links_between_documents_become_links_between_topics(data: dict[str, Any]) -> None:
    repo = data["package"]["urls"]["Homepage"]
    index = prepare_markdown(ROOT, _doc(data, "doc-index"), repo)
    assert not index.startswith("# ")  # the manual prints its own heading
    assert "](#doc-getting_started)" in index
    assert "](#doc-decisions)" in index
    assert "](#part-metrics)" in index  # generated catalog pages are part III
    assert not re.findall(r"\]\((?!https://)[^)]*\.md", index)  # no relative file links
    assumptions = prepare_markdown(ROOT, _doc(data, "doc-assumptions"), repo)
    assert "](#decision-0003)" in assumptions
    notation = prepare_markdown(ROOT, _doc(data, "doc-notation"), repo)
    # A heading anchor in another document keeps its target through the label prefix.
    assert "](#doc-policies-annualization-factors)" in notation


def test_other_repository_paths_link_to_github_and_code_is_untouched(
    data: dict[str, Any],
) -> None:
    repo = data["package"]["urls"]["Homepage"]
    getting_started = prepare_markdown(ROOT, _doc(data, "doc-getting_started"), repo)
    for target in re.findall(r"\]\(([^)]+)\)", getting_started):
        assert target.startswith(("#", "https://")), target
    criteria = prepare_markdown(ROOT, _doc(data, "doc-criteria"), repo)
    # A regex in a code span is not a link.
    assert "`^[+-]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][+-]?\\d+)?$`" in criteria


@pytest.mark.manual
def test_manual_compiles_with_a_named_destination_for_every_topic(tmp_path: Path) -> None:
    if not os.environ.get("OFS_REQUIRE_TYPST"):  # the manual CI job must not skip
        pytest.importorskip("typst")
    from pypdf import PdfReader

    from openfactsheet.manual.build import build_manual, expected_anchors

    out = tmp_path / "manual.pdf"
    result = build_manual(ROOT, out)  # raises if any expected anchor is missing
    assert expected_anchors(manual_data(ROOT)) <= result.anchors
    assert result.pages > 100
    reader = PdfReader(out)
    page = reader.get_destination_page_number(reader.named_destinations["metric-sharpe_ratio"])
    text = reader.pages[page].extract_text() + reader.pages[page + 1].extract_text()
    assert "sharpe_ratio@v1" in text
    assert "Sharpe" in text
    # Reproducible: the same sources give the same bytes.
    again = build_manual(ROOT, tmp_path / "again.pdf")
    assert again.path.read_bytes() == out.read_bytes()
