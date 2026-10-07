"""The OpenFactsheet reference manual (decision 0034).

A CRAN-style PDF manual is generated from the code: one topic per public
function or class, one per metric, every methodology document and decision
note, a bibliography and an index. ``scripts/build_manual.py`` compiles it with
Typst; ``openfactsheet.manual.export`` produces the data it is built from.

Every topic has a stable named destination, so a result can link to exactly the
page that documents it (``...pdf#nameddest=metric-sharpe_ratio``).
:mod:`openfactsheet.manual.links` turns those destinations into the URLs that
every report carries (decision 0035).
"""

from __future__ import annotations

__all__ = [
    "api_anchor",
    "category_anchor",
    "decision_anchor",
    "document_anchor",
    "metric_anchor",
    "reference_anchor",
]


def metric_anchor(metric_id: str) -> str:
    """Named destination of a metric's topic, e.g. ``metric-sharpe_ratio``."""
    return f"metric-{metric_id}"


def api_anchor(name: str) -> str:
    """Named destination of a public function or class, e.g. ``api-analyze``."""
    return f"api-{name}"


def decision_anchor(number: str) -> str:
    """Named destination of a methodology decision note, e.g. ``decision-0008``."""
    return f"decision-{number}"


def category_anchor(category: str) -> str:
    """Named destination of a metric group's topic, e.g. ``category-drawdown``."""
    return f"category-{category}"


def document_anchor(name: str) -> str:
    """Named destination of a methodology document, e.g. ``doc-assumptions``."""
    return f"doc-{name}"


def reference_anchor(key: str) -> str:
    """Named destination of a bibliography entry, e.g. ``ref-sharpe1994``."""
    return f"ref-{key}"
