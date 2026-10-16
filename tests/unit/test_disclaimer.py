"""Snapshot tests for the canonical disclaimer and metric attribution.

DISCLAIMER.md is the single source of the disclosure. These tests fail when the
README, the documentation, the reports or the comparison output stop carrying
the identical short notice, or when the full text changes without this snapshot
being updated deliberately.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import openfactsheet as ofs
from openfactsheet.interpretation.glossary import DISCLAIMER_PATH, SHORT_DISCLAIMER
from openfactsheet.manual.export import package_data
from openfactsheet.metrics.attribution import ATTRIBUTIONS, short_citation
from openfactsheet.metrics.references import MARTIN_MCCANN_1989
from openfactsheet.metrics.registry import all_metrics

ROOT = Path(__file__).resolve().parents[2]

SHORT_NOTICE = (
    "For information and education only — not investment advice. Investing involves risk; "
    "past performance does not predict future results. Verify results and consult a qualified "
    "financial adviser."
)

FULL_TEXT = (
    "**Important information — educational analytics only; not financial advice.** "
    "OpenFactsheet and OpenFactsheet.org provide general-purpose, informational and educational "
    "software and investment performance analytics. The content, calculations, comparisons, "
    "examples, reports, and other outputs are not personalized investment, financial, legal, "
    "tax, or accounting advice; they are not a recommendation, solicitation, endorsement, or "
    "offer to buy, sell, or hold any security, commodity interest, fund, or other financial "
    "product. OpenFactsheet does not evaluate your individual financial circumstances, "
    "objectives, risk tolerance, or suitability. Consult an appropriately qualified and, where "
    "applicable, licensed financial adviser before making investment decisions.",
    "**Investing involves risk, including possible loss of principal. Past performance is not "
    "indicative of future results.** Historical returns, statistical measures, rankings, "
    "comparisons and risk-adjusted performance figures do not predict future outcomes. "
    "Backtested, simulated, modeled or hypothetical results are not actual trading records and "
    "may differ materially from actual results. Results depend on the quality, completeness, "
    "timing, methodology, assumptions, benchmarks, fees, taxes, currencies, and other "
    "characteristics of the supplied data. Neither accuracy nor completeness is guaranteed; "
    "independently verify all inputs and outputs.",
    "**Use at your own risk.** The software and website are provided on an **“as is” and “as "
    "available”** basis, without warranties to the extent permitted by applicable law. Users "
    "are responsible for their use and interpretation of the software and results. Nothing in "
    "this notice excludes or restricts liability that cannot lawfully be excluded, or overrides "
    "the applicable open-source license or consumer-protection law.",
    "**References and attribution.** OpenFactsheet seeks to identify and appropriately credit "
    "the originators of financial metrics and methodologies, academic papers, books, data "
    "sources, and third-party libraries used or referenced. Attribution is not an endorsement, "
    "affiliation, license grant, or permission to reproduce protected content. If you believe "
    "an attribution, copyright notice, license, or reference is incomplete or incorrect, please "
    "contact the project using its published contact channel so the issue can be reviewed and "
    "corrected.",
)


def _flat(text: str) -> str:
    """Whitespace-normalized text, so that wrapped lines compare equal."""
    return " ".join(text.split())


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def report() -> ofs.FactsheetReport:
    returns = pd.Series(
        [0.01, -0.02, 0.015, 0.005, -0.01, 0.03],
        index=pd.date_range("2025-01-31", periods=6, freq="ME"),
    )
    return ofs.analyze(returns)


def test_constant_is_the_canonical_short_notice() -> None:
    assert SHORT_DISCLAIMER == SHORT_NOTICE


def test_disclaimer_file_holds_full_text_and_short_notice() -> None:
    text = _read("DISCLAIMER.md")
    paragraphs = {p.strip() for p in text.split("\n\n")}
    for paragraph in FULL_TEXT:
        assert paragraph in paragraphs
    assert SHORT_NOTICE in text


@pytest.mark.parametrize("rel", ["README.md", "docs/index.md", "docs/reference/report_schema.md"])
def test_documents_carry_the_identical_short_notice_and_link(rel: str) -> None:
    text = _read(rel)
    assert SHORT_NOTICE in _flat(text)
    assert "DISCLAIMER.md" in text


def test_readme_states_public_alpha_and_creator() -> None:
    text = _read("README.md")
    assert "**Status: Public alpha** · Methodology 0.1.0" in text
    assert (
        "Public alpha: interfaces, metrics and documentation may evolve; validate results "
        "before investment decisions." in text
    )
    assert "[Connect on LinkedIn](https://www.linkedin.com/in/andres-bagnasco/)" in text


@pytest.mark.parametrize("fmt", ["terminal", "markdown", "html"])
def test_reports_show_the_notice_with_a_link(report: ofs.FactsheetReport, fmt: str) -> None:
    text = {
        "terminal": report.summary,
        "markdown": report.to_markdown,
        "html": report.to_html,
    }[fmt]()
    assert SHORT_NOTICE in _flat(text)
    assert report.documentation.source(DISCLAIMER_PATH) in text


def test_json_report_schema_is_not_changed_by_the_notice(report: ofs.FactsheetReport) -> None:
    assert SHORT_NOTICE not in report.to_json()


def test_comparison_shows_the_notice() -> None:
    dates = pd.date_range("2025-01-31", periods=6, freq="ME")
    a = pd.Series([0.01, -0.02, 0.015, 0.005, -0.01, 0.03], index=dates)
    b = pd.Series([0.02, -0.01, 0.0, 0.01, 0.005, -0.015], index=dates)
    text = ofs.compare({"A": a, "B": b}).summary()
    assert SHORT_NOTICE in text
    assert DISCLAIMER_PATH in text


def test_manual_title_page_uses_the_constant() -> None:
    assert package_data(ROOT)["short_disclaimer"] == SHORT_NOTICE
    assert "package.short_disclaimer" in _read("docs/manual/openfactsheet-manual.typ")


def test_every_registered_metric_has_a_curated_attribution() -> None:
    missing = [d.id for d in all_metrics() if d.id not in ATTRIBUTIONS]
    assert not missing, f"Add these metrics to metrics/attribution.py: {missing}"


def test_short_citation_labels() -> None:
    assert short_citation(MARTIN_MCCANN_1989) == "Martin & McCann (1989)"
