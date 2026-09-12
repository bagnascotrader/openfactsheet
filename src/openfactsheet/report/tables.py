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


# Serial-dependence metrics are data-quality evidence, so renderers show them inside
# section 2 (data-quality diagnostics); the canonical report keeps the 14 sections of
# CLAUDE.md section 30.
DATA_QUALITY_CATEGORY = "dependence"
# Statistical-confidence metrics are rendered in section 12, after factor analysis.
STATISTICAL_CATEGORY = "statistical"
# Factor-model metrics are rendered in section 11 with the factor loadings.
FACTOR_CATEGORY = "factors"


def data_quality_metrics(report: FactsheetReport) -> list[MetricResult]:
    return list(report.metrics.by_category(DATA_QUALITY_CATEGORY))


def statistical_metrics(report: FactsheetReport) -> list[MetricResult]:
    return list(report.metrics.by_category(STATISTICAL_CATEGORY))


def factor_metrics(report: FactsheetReport) -> list[MetricResult]:
    return list(report.metrics.by_category(FACTOR_CATEGORY))


def ordered_categories(report: FactsheetReport) -> list[tuple[str, str, list[MetricResult]]]:
    """Metric categories rendered as their own sections (3 to 10), in canonical order."""
    out: list[tuple[str, str, list[MetricResult]]] = []
    for cat in CATEGORY_ORDER:
        if cat in (DATA_QUALITY_CATEGORY, STATISTICAL_CATEGORY, FACTOR_CATEGORY):
            continue
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


def document_benchmark_note(report: FactsheetReport) -> str | None:
    """When the document names a benchmark whose returns were not supplied (decision 0032)."""
    doc = report.document
    if doc is None or not doc.benchmarks or report.benchmark_summary is not None:
        return None
    names = "; ".join(b.value for b in doc.benchmarks)
    return (
        f"The source document names its benchmark ({names}); its returns were not supplied, so "
        "benchmark-relative metrics are not computed. Pass them explicitly with benchmark=... ."
    )


def extraction_summary(report: FactsheetReport) -> tuple[str, str] | None:
    """Key/value text and the reconstructed table for document inputs (PDF, OCR), else None."""
    ex = report.provenance.extraction
    if not ex:
        return None
    lines = [report.document.to_text()] if report.document is not None else []
    lines += [
        f"Extracted by:              {ex.get('engine', 'unknown')} (page {ex.get('page', '?')})",
        f"Extraction confidence:     {ex.get('confidence', 'unknown')}",
        f"Monthly values read:       {ex.get('monthly_values', '?')}",
    ]
    if ex.get("min_cell_confidence") is not None:
        lines.append(f"Lowest OCR cell score:     {float(ex['min_cell_confidence']):.2f}")
    lines += [f"  - check: {c}" for c in ex.get("checks", [])]
    lines += [f"  - {w}" for w in ex.get("warnings", [])]
    return "\n".join(lines), str(ex.get("reconstructed_table", ""))


EPISODE_TABLE_HEADER = (
    "#",
    "Peak",
    "Trough",
    "Recovered",
    "Depth",
    "To trough",
    "To recover",
    "Underwater",
)


@dataclass(frozen=True)
class EpisodeTable:
    """The deepest drawdown episodes, deepest first (decision 0026)."""

    rows: tuple[tuple[str, ...], ...]
    total: int  # number of episodes in the full history
    note: str


def _episode_point(label: str | None, index: int, dated: bool) -> str:
    if index == 0:
        return "inception"
    if label is not None:
        return label
    return f"period {index}" if not dated else "—"


def drawdown_episode_table(report: FactsheetReport) -> EpisodeTable | None:
    """Rows for the canonical drawdown-episode table, or ``None`` when no path exists.

    The row count is methodology-defined (``charts.episode_table_rows``); episodes are
    ordered by depth (deepest first, ties by earliest peak), so the table can never
    omit a deeper episode in favour of a shallower one. Every episode is in the JSON.
    """
    if report.diagnostics.impossible_return_count:
        return None
    limit = int(report.assumptions.get("charts.episode_table_rows"))
    episodes = sorted(report.drawdown_episodes, key=lambda e: (e.depth, e.peak_index))
    dated = report.returns.dates is not None
    rows: list[tuple[str, ...]] = []
    for rank, e in enumerate(episodes[:limit], start=1):
        recovery = (
            _episode_point(e.recovery_date, e.recovery_index, dated)
            if e.recovery_index is not None
            else "not recovered"
        )
        rows.append(
            (
                str(rank),
                _episode_point(e.peak_date, e.peak_index, dated),
                _episode_point(e.trough_date, e.trough_index, dated),
                recovery,
                f"{e.depth:.2%}",
                str(e.peak_to_trough_periods),
                str(e.recovery_periods) if e.recovery_periods is not None else "—",
                str(e.total_underwater_periods) + ("" if e.recovered else " (open)"),
            )
        )
    total = len(episodes)
    if total == 0:
        note = "No drawdown episodes: wealth never fell below a previous peak."
    else:
        scope = (
            f"The {limit} deepest of {total} drawdown episodes, deepest first (the methodology "
            f"limits the table to {limit} rows)"
            if total > limit
            else f"All {total} drawdown episode{'s' if total > 1 else ''}, deepest first"
        )
        note = (
            scope + ". Durations (to trough, to recover, underwater) are counted in observation "
            "periods; an open episode had not recovered by the end of the data. Every episode "
            "is listed in the JSON report."
        )
    return EpisodeTable(rows=tuple(rows), total=total, note=note)


FACTOR_SECTION_TEXT = (
    "No factor returns were supplied. Factor models (CAPM, Fama-French, Carhart or custom "
    "factors) are estimated only from factor returns supplied explicitly, e.g. "
    "ofs.analyze(returns, factors=factor_frame); OpenFactsheet never downloads factor data."
)

LOADING_TABLE_HEADER = ("Coefficient", "Estimate", "Std. error (HAC)", "t", "p-value", "95% CI")


def _num(x: float | None, fmt: str) -> str:
    return "—" if x is None else format(x, fmt)


def factor_loading_rows(report: FactsheetReport) -> tuple[tuple[str, ...], ...]:
    """Alpha (per period) and every factor loading with Newey-West inference."""
    fa = report.factor_analysis
    if fa is None or fa.fit is None:
        return ()
    rows: list[tuple[str, ...]] = []
    fit = fa.fit
    for c in (fit.alpha, *fit.loadings):
        is_alpha = c.name == "alpha"
        fmt = ".3%" if is_alpha else ".3f"
        ci = (
            f"[{_num(c.ci_lower, fmt)}, {_num(c.ci_upper, fmt)}]"
            if c.ci_lower is not None and c.ci_upper is not None
            else "—"
        )
        rows.append(
            (
                "alpha (per period)" if is_alpha else c.name,
                _num(c.estimate, fmt),
                _num(c.standard_error, fmt),
                _num(c.t_statistic, ".2f"),
                _num(c.p_value, ".3f"),
                ci,
            )
        )
    return tuple(rows)


def factor_fit_summary(report: FactsheetReport) -> str:
    fa = report.factor_analysis
    if fa is None or fa.fit is None:
        return ""
    f = fa.fit
    parts = [
        f"R-squared {f.r_squared:.3f}" if f.r_squared is not None else "R-squared undefined",
        f"adjusted {f.adj_r_squared:.3f}" if f.adj_r_squared is not None else "",
        f"residual lag-1 autocorrelation {f.residual_autocorrelation_lag1:.2f}"
        if f.residual_autocorrelation_lag1 is not None
        else "",
        f"maximum VIF {f.max_vif:.1f}" if f.max_vif is not None else "",
    ]
    return (
        "; ".join(p for p in parts if p)
        + ". Loadings describe average sensitivity to each supplied factor over the aligned "
        "periods; they do not establish causality."
    )


STATISTICAL_SECTION_TEXT = (
    "Confidence labels summarize estimation reliability from sample length, data quality and "
    "benchmark overlap. The statistics below quantify sampling uncertainty under i.i.d. "
    "assumptions; the Deflated Sharpe Ratio is not computed because it requires the number of "
    "strategies tried, which a single return series does not reveal."
)
