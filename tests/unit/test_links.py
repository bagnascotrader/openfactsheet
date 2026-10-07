"""Links from a result to its documentation (decision 0035).

Every metric in every renderer must point at a topic the manual really
contains, for the version that produced the result.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import openfactsheet as ofs
from openfactsheet.manual import (
    api_anchor,
    category_anchor,
    decision_anchor,
    document_anchor,
    metric_anchor,
    reference_anchor,
)
from openfactsheet.manual.build import expected_anchors, release_date
from openfactsheet.manual.export import manual_data
from openfactsheet.manual.links import (
    MANUAL_TAG,
    REPOSITORY,
    ROLLING_MANUAL_TAG,
    ROLLING_SOURCE_REF,
    SOURCE_REF,
    DocumentationLinks,
    documentation_links,
)
from openfactsheet.metrics.registry import all_metrics
from openfactsheet.models.metric import CATEGORY_ORDER

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def report() -> ofs.FactsheetReport:
    returns = pd.Series(
        [0.012, -0.021, 0.015, 0.004, -0.009, 0.028] * 6,
        index=pd.date_range("2021-01-31", periods=36, freq="ME"),
    )
    return ofs.analyze(returns)


def test_anchor_helpers_are_the_single_source_of_destinations() -> None:
    assert metric_anchor("sharpe_ratio") == "metric-sharpe_ratio"
    assert api_anchor("analyze") == "api-analyze"
    assert decision_anchor("0035") == "decision-0035"
    assert category_anchor("drawdown") == "category-drawdown"
    assert document_anchor("assumptions") == "doc-assumptions"
    assert reference_anchor("sharpe1994") == "ref-sharpe1994"


def test_links_address_the_manual_of_the_running_version() -> None:
    links = documentation_links()
    assert links.package_version == ofs.__version__
    assert links.manual == (f"{REPOSITORY}/releases/download/{MANUAL_TAG}/openfactsheet-manual.pdf")
    assert links.metric("sharpe_ratio") == f"{links.manual}#nameddest=metric-sharpe_ratio"
    assert links.category("tail") == f"{links.manual}#nameddest=category-tail"
    assert links.api("analyze") == f"{links.manual}#nameddest=api-analyze"
    assert links.decision("0035") == f"{links.manual}#nameddest=decision-0035"
    assert links.document("methodology") == f"{links.manual}#nameddest=doc-methodology"
    assert links.reference("sharpe1994") == f"{links.manual}#nameddest=ref-sharpe1994"
    assert links.catalog == f"{REPOSITORY}/blob/{SOURCE_REF}/docs/metric_catalog.md"
    assert links.metric_page("omega_ratio") == (
        f"{REPOSITORY}/blob/{SOURCE_REF}/docs/interpretation/omega_ratio.md"
    )
    assert links.docs == f"{REPOSITORY}/tree/{SOURCE_REF}/docs"


def test_the_release_a_result_links_to_matches_the_changelog() -> None:
    """A released version links to its own assets; before release, to the rolling manual."""
    released = release_date(ROOT, ofs.__version__) is not None
    version_tag = f"v{ofs.__version__}"
    if released:
        assert version_tag == MANUAL_TAG
        assert version_tag == SOURCE_REF
    else:
        assert MANUAL_TAG == ROLLING_MANUAL_TAG
        assert SOURCE_REF == ROLLING_SOURCE_REF
    assert documentation_links().released is released


def test_released_links_point_at_the_version_tag() -> None:
    links = DocumentationLinks(package_version="1.2.3", manual_tag="v1.2.3", source_ref="v1.2.3")
    assert links.released is True
    assert links.manual.endswith("/releases/download/v1.2.3/openfactsheet-manual.pdf")
    assert links.catalog == f"{REPOSITORY}/blob/v1.2.3/docs/metric_catalog.md"


def test_every_metric_links_to_a_destination_the_manual_contains() -> None:
    anchors = expected_anchors(manual_data(ROOT))
    for definition in all_metrics():
        assert metric_anchor(definition.id) in anchors, definition.id
    for category in CATEGORY_ORDER:
        assert category_anchor(category) in anchors, category
    assert decision_anchor("0035") in anchors


def test_every_result_carries_the_link_to_its_own_topic(report: ofs.FactsheetReport) -> None:
    manual = report.documentation.manual
    for result in report.metrics:
        assert result.documentation == f"{manual}#nameddest=metric-{result.id}"
        # A result that could not be computed still links to its definition.
        assert result.documentation in report.to_markdown()


def test_json_carries_the_links_and_one_per_metric(report: ofs.FactsheetReport) -> None:
    data = json.loads(report.to_json())
    docs = data["documentation"]
    assert docs["package_version"] == ofs.__version__
    assert docs["manual"] == report.documentation.manual
    assert docs["repository"] == REPOSITORY
    assert docs["released"] is report.documentation.released
    assert docs["metric_topic"].endswith("#nameddest=metric-<id>")
    for metric in data["metrics"]:
        assert metric["documentation"].endswith(f"#nameddest=metric-{metric['id']}")


@pytest.mark.parametrize("renderer", ["to_markdown", "to_html"])
def test_every_metric_name_is_linked_in_every_rich_renderer(
    report: ofs.FactsheetReport, renderer: str
) -> None:
    text = getattr(report, renderer)()
    linked = set(re.findall(r"nameddest=metric-([a-z0-9_]+)", text))
    assert linked == {m.id for m in report.metrics}


def test_the_terminal_report_keeps_the_address_in_one_piece(
    report: ofs.FactsheetReport,
) -> None:
    """Plain text has no links, so the address must at least stay copyable."""
    text = report.summary()
    assert report.documentation.manual in text
    assert "nameddest=metric-<id>" in text


def test_links_are_absolute_and_unduplicated(report: ofs.FactsheetReport) -> None:
    for url in [report.documentation.manual, report.metrics["sharpe_ratio"].documentation]:
        assert url.startswith("https://")
        assert url.count("#") <= 1
        assert "//releases" not in url


def test_the_manual_pdf_url_matches_the_workflow_that_publishes_it() -> None:
    """The rolling download the reports advertise is the one CI actually uploads."""
    workflow = (ROOT / ".github/workflows/manual.yml").read_text(encoding="utf-8")
    assert ROLLING_MANUAL_TAG in workflow
    pdf_name = documentation_links().manual.rsplit("/", 1)[-1]
    assert pdf_name in workflow


def _links(data: dict[str, Any]) -> set[str]:
    return {m["anchor"] for m in data["metrics"]["metrics"]}


def test_the_manual_data_uses_the_anchor_helper() -> None:
    assert _links(manual_data(ROOT)) == {metric_anchor(d.id) for d in all_metrics()}
