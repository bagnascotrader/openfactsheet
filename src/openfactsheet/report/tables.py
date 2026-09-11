"""Presentation helpers shared by all renderers. Rounding happens only here."""

from __future__ import annotations

from dataclasses import dataclass

from openfactsheet.models.metric import CATEGORY_ORDER, CATEGORY_TITLES, MetricResult
from openfactsheet.models.report import FactsheetReport

STATUS_LABELS = {
    "applicable": "",
    "low_confidence": "low confidence",
    "supplementary": "supplementary",
    "not_applicable": "not applicable",
    "insufficient_data": "insufficient data",
    "error": "error",
}


def format_value(result: MetricResult) -> str:
    v = result.value
    if v is None:
        return "—"
    unit = result.unit
    if unit == "decimal_return":
        return f"{v:.2%}"
    if unit == "fraction":
        return f"{v:.1%}"
    if unit == "probability":
        return f"{v:.3f}"
    if unit in ("periods", "count"):
        text = f"{v:.0f}"
        years = result.details.get("years")
        if unit == "periods" and isinstance(years, float):
            text += f" ({years:.1f}y)"
        return text
    return f"{v:.2f}"


def status_label(result: MetricResult) -> str:
    if result.value is not None:
        if result.status == "supplementary":
            return f"supplementary ({result.confidence})"
        return result.confidence
    return STATUS_LABELS[result.status]


@dataclass
class Footnotes:
    """Deduplicated numbered notes so that long warnings are printed once."""

    texts: list[str]

    def ref(self, text: str) -> int:
        if text not in self.texts:
            self.texts.append(text)
        return self.texts.index(text) + 1


def result_notes(result: MetricResult) -> list[str]:
    notes: list[str] = []
    if result.value is None and result.reason:
        notes.append(result.reason)
    notes.extend(result.warnings)
    return notes


def ordered_categories(report: FactsheetReport) -> list[tuple[str, str, list[MetricResult]]]:
    out: list[tuple[str, str, list[MetricResult]]] = []
    for cat in CATEGORY_ORDER:
        rows = list(report.metrics.by_category(cat))
        if rows:
            out.append((cat, CATEGORY_TITLES[cat], rows))
    return out


def confidence_counts(report: FactsheetReport) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in report.metrics:
        key = r.confidence if r.value is not None else r.status
        counts[key] = counts.get(key, 0) + 1
    return counts


FACTOR_SECTION_TEXT = (
    "Not available in methodology 0.1.0. Factor models (CAPM with factor data, Fama-French, "
    "Carhart) are planned and will require explicitly supplied factor returns; OpenFactsheet "
    "never downloads factor data silently."
)

STATISTICAL_SECTION_TEXT = (
    "Confidence labels summarize estimation reliability from sample length, data quality and "
    "benchmark overlap. Confidence intervals, Probabilistic and Deflated Sharpe ratios are "
    "planned for a later methodology version."
)
