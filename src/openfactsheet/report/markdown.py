"""Markdown rendering of the canonical report."""

from __future__ import annotations

from openfactsheet.interpretation.glossary import CONFIDENCE_DISCLAIMER
from openfactsheet.models.metric import MetricResult
from openfactsheet.models.report import FactsheetReport
from openfactsheet.policy.applicability import NO_BENCHMARK_REASON
from openfactsheet.report.tables import (
    EPISODE_TABLE_HEADER,
    FACTOR_SECTION_TEXT,
    LOADING_TABLE_HEADER,
    STATISTICAL_SECTION_TEXT,
    Footnotes,
    confidence_counts,
    data_quality_metrics,
    drawdown_episode_table,
    extraction_summary,
    factor_fit_summary,
    factor_loading_rows,
    factor_metrics,
    format_value,
    ordered_categories,
    result_notes,
    statistical_metrics,
    status_label,
)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _kv_block(text: str) -> list[str]:
    return ["```text", text, "```"]


def _metric_table(rows: list[MetricResult], notes: Footnotes) -> list[str]:
    out = ["| Metric | Value | Confidence / status | Notes |", "|---|---:|---|---|"]
    for r in rows:
        refs = " ".join(f"[{notes.ref(t)}]" for t in result_notes(r))
        out.append(f"| {_cell(r.name)} | {format_value(r)} | {status_label(r)} | {refs} |")
    return out


def _extraction_block(report: FactsheetReport) -> list[str]:
    extraction = extraction_summary(report)
    if extraction is None:
        return []
    text, table = extraction
    return [
        "**Source document**",
        "",
        *_kv_block(text),
        "",
        "Reconstructed table (as read):",
        "",
        *_kv_block(table),
        "",
    ]


def _episode_table(report: FactsheetReport) -> list[str]:
    table = drawdown_episode_table(report)
    if table is None:
        return []
    out = ["", "**Drawdown episodes**", ""]
    if table.rows:
        out.append("| " + " | ".join(EPISODE_TABLE_HEADER) + " |")
        out.append("|---:|---|---|---|---:|---:|---:|---:|")
        out += ["| " + " | ".join(_cell(c) for c in row) + " |" for row in table.rows]
        out.append("")
    out.append(table.note)
    return out


def _factor_section(report: FactsheetReport, notes: Footnotes) -> list[str]:
    rows = factor_metrics(report)
    fa = report.factor_analysis
    if fa is None:
        return [FACTOR_SECTION_TEXT, "", "Metrics: " + ", ".join(r.name for r in rows) + "."]
    out = [*_kv_block(fa.to_text()), ""]
    loadings = factor_loading_rows(report)
    if loadings:
        out.append("| " + " | ".join(LOADING_TABLE_HEADER) + " |")
        out.append("|---|---:|---:|---:|---:|---|")
        out += ["| " + " | ".join(_cell(c) for c in row) + " |" for row in loadings]
        out += ["", factor_fit_summary(report), ""]
    out += _metric_table(rows, notes)
    return out


def render_markdown(report: FactsheetReport) -> str:
    notes = Footnotes([])
    p = report.provenance
    out: list[str] = [
        f"# OpenFactsheet — {_cell(report.name)}",
        "",
        f"*Canonical report · {report.assumptions.name} · openfactsheet {p.package_version}*",
        "",
        "Canonical charts (growth of 1, drawdowns, calendar years, monthly returns, "
        "distribution, rolling one-year statistics) are in the HTML report "
        "(`report.to_html()`) and available as SVG from `report.charts()`.",
        "",
        "## 1. Input & methodology",
        "",
        *_kv_block(report.input_summary.to_text()),
        "",
        *_extraction_block(report),
        f"**Annualization:** {p.annualization}  ",
        "**Risk-free rate:** 0% in methodology 0.1.0 (see section 14).",
        "",
        "## 2. Data-quality diagnostics",
        "",
        *_kv_block(report.diagnostics.to_text()),
        "",
        "**Serial dependence & smoothing**",
        "",
        *_metric_table(data_quality_metrics(report), notes),
    ]

    number = 3
    for cat, title, rows in ordered_categories(report):
        out += ["", f"## {number}. {title}", ""]
        number += 1
        if cat == "benchmark":
            if report.benchmark_summary is None:
                out.append("Not applicable: " + NO_BENCHMARK_REASON)
                out += ["", "Metrics: " + ", ".join(r.name for r in rows) + "."]
                continue
            out += [*_kv_block(report.benchmark_summary.to_text()), ""]
        out += _metric_table(rows, notes)
        if cat == "drawdown":
            out += _episode_table(report)

    counts = confidence_counts(report)
    out += [
        "",
        f"## {number}. Factor analysis",
        "",
        *_factor_section(report, notes),
        "",
        f"## {number + 1}. Statistical confidence",
        "",
        ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in sorted(counts.items())),
        "",
        CONFIDENCE_DISCLAIMER + " " + STATISTICAL_SECTION_TEXT,
        "",
        *_metric_table(statistical_metrics(report), notes),
        "",
        f"## {number + 2}. Metric catalog",
        "",
        "Definitions, formulas, assumptions and references: `ofs.metric_catalog()` or "
        "`docs/metric_catalog.md`.",
        "",
        f"## {number + 3}. Assumptions & caveats",
        "",
        *_kv_block(report.assumptions.describe()),
    ]
    material = [f for f in report.diagnostics.findings if f.severity != "info"]
    if material:
        out += ["", "**Material data-quality findings:**", ""]
        out += [f"- *{f.severity}*: {_cell(f.message)}" for f in material]
    out += ["", "OpenFactsheet explains measurements; it does not give investment advice."]
    if notes.texts:
        out += ["", "## Notes", ""]
        out += [f"{i}. {_cell(t)}" for i, t in enumerate(notes.texts, start=1)]
    return "\n".join(out) + "\n"
