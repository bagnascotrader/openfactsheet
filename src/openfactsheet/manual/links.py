"""Links from a result to the documentation of its own version (decision 0035).

Every number OpenFactsheet reports can be traced to the page that defines it:
what it measures, the exact formula, the assumptions it used, when it misleads
and where the definition comes from. :class:`DocumentationLinks` builds those
URLs, and every report carries them, so a result does not have to be read next
to the repository to be understood.

The links point at the documentation of the version that produced the result,
never at whatever ``main`` happens to say later. A released version links to
its own release assets and sources; before release there is no such tag, so
results link to the rolling manual built from ``main``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openfactsheet.manual import (
    api_anchor,
    category_anchor,
    decision_anchor,
    document_anchor,
    metric_anchor,
    reference_anchor,
)
from openfactsheet.version import __version__

REPOSITORY = "https://github.com/bagnascotrader/openfactsheet"
MANUAL_FILENAME = "openfactsheet-manual.pdf"

# The release whose assets carry this version's manual, and the ref its sources
# live at. ``manual-latest``/``main`` is the rolling pre-release built from main
# (.github/workflows/manual.yml); at release both become ``v<version>``, which
# ``tests/unit/test_links.py`` checks against CHANGELOG.md.
ROLLING_MANUAL_TAG = "manual-latest"
ROLLING_SOURCE_REF = "main"
MANUAL_TAG = "v0.1.0a1"
SOURCE_REF = "v0.1.0a1"


@dataclass(frozen=True)
class DocumentationLinks:
    """Where the documentation of one report's version lives.

    Attributes:
        package_version: The ``openfactsheet`` version the links document.
        manual_tag: Release tag whose assets carry that version's PDF manual.
        source_ref: Git ref the documentation sources are read at.
    """

    package_version: str
    manual_tag: str
    source_ref: str

    @property
    def released(self) -> bool:
        """Whether these links point at a released version rather than ``main``."""
        return self.manual_tag != ROLLING_MANUAL_TAG

    @property
    def manual(self) -> str:
        """URL of the PDF reference manual for this version."""
        return f"{REPOSITORY}/releases/download/{self.manual_tag}/{MANUAL_FILENAME}"

    def topic(self, anchor: str) -> str:
        """URL of one manual topic, by its named destination."""
        return f"{self.manual}#nameddest={anchor}"

    def metric(self, metric_id: str) -> str:
        """URL of a metric's manual topic, e.g. for ``sharpe_ratio``."""
        return self.topic(metric_anchor(metric_id))

    def category(self, category: str) -> str:
        """URL of a metric group's manual topic, e.g. for ``drawdown``."""
        return self.topic(category_anchor(category))

    def api(self, name: str) -> str:
        """URL of a public function or class topic, e.g. for ``analyze``."""
        return self.topic(api_anchor(name))

    def decision(self, number: str) -> str:
        """URL of a methodology decision note, e.g. for ``"0035"``."""
        return self.topic(decision_anchor(number))

    def document(self, name: str) -> str:
        """URL of a methodology document topic, e.g. for ``assumptions``."""
        return self.topic(document_anchor(name))

    def reference(self, key: str) -> str:
        """URL of a bibliography entry, e.g. for ``sharpe1994``."""
        return self.topic(reference_anchor(key))

    @property
    def docs(self) -> str:
        """URL of the documentation tree at this version."""
        return f"{REPOSITORY}/tree/{self.source_ref}/docs"

    @property
    def catalog(self) -> str:
        """URL of the metric catalog at this version."""
        return self.source("docs/metric_catalog.md")

    def source(self, path: str) -> str:
        """URL of one repository file at this version, by repository-relative path."""
        return f"{REPOSITORY}/blob/{self.source_ref}/{path}"

    def metric_page(self, metric_id: str) -> str:
        """URL of a metric's Markdown page at this version."""
        return self.source(f"docs/interpretation/{metric_id}.md")

    def to_dict(self) -> dict[str, Any]:
        """The links as JSON-compatible Python objects."""
        return {
            "package_version": self.package_version,
            "released": self.released,
            "repository": REPOSITORY,
            "manual": self.manual,
            "manual_tag": self.manual_tag,
            "source_ref": self.source_ref,
            "docs": self.docs,
            "catalog": self.catalog,
            # How a result's own link is formed, for readers of the JSON.
            "metric_topic": self.topic("metric-<id>"),
        }


def documentation_links() -> DocumentationLinks:
    """Documentation links for the running version of OpenFactsheet."""
    return DocumentationLinks(
        package_version=__version__, manual_tag=MANUAL_TAG, source_ref=SOURCE_REF
    )


def metric_documentation(metric_id: str) -> str:
    """URL of the manual topic documenting one metric, for the running version."""
    return documentation_links().metric(metric_id)
