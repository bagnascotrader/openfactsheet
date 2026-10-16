"""Markdown rendering of the canonical report.

Every metric name is a link to the topic of the reference manual that defines
it (decision 0035).
"""

from __future__ import annotations

import re

from openfactsheet.interpretation.glossary import (
    CONFIDENCE_DISCLAIMER,
    DISCLAIMER_PATH,
    SHORT_DISCLAIMER,
)
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
    document_benchmark_note,
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
    # Names and labels can come from untrusted files (column headers, PDF text):
    # angle brackets are written as entities so a renderer that allows raw HTML
    # never sees a tag.
    return text.replace("|", "\\|").replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;")


def _kv_block(text: str) -> list[str]:
    # The fence is longer than any backtick run in the text (CommonMark), so text
    # read from a document can never close the code block early.
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return [f"{fence}text", text, fence]


def _doc_link(result: MetricResult) -> str:
    """The metric's name, linked to the manual topic that defines it (decision 0035)."""
    return f"[{_cell(result.name)}]({result.documentation})"


def _doc_link_list(rows: list[MetricResult]) -> str:
    """Names of metrics that have no table in this section, each linked to its topic."""
    return ", ".join(_doc_link(r) for r in rows)


def _metric_table(rows: list[MetricResult], notes: Footnotes) -> list[str]:
    out = ["| Metric | Value | Confidence / status | Notes |", "|---|---:|---|---|"]
    for r in rows:
        refs = " ".join(f"[{notes.ref(t)}]" for t in result_notes(r))
        out.append(f"| {_doc_link(r)} | {format_value(r)} | {status_label(r)} | {refs} |")
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
        return [FACTOR_SECTION_TEXT, "", "Metrics: " + _doc_link_list(rows) + "."]
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
    docs = report.documentation
    out: list[str] = [
        f"# OpenFactsheet — {_cell(report.name)}",
        "",
        f"*Canonical report · {report.assumptions.name} · openfactsheet {p.package_version}*",
        "",
        f"> {SHORT_DISCLAIMER} [Full disclaimer]({docs.source(DISCLAIMER_PATH)}).",
        "",
        f"Every metric below links to its topic in the [reference manual]({docs.manual})"
        + ("" if docs.released else " built from the development branch")
        + ": formula, assumptions, interpretation and references.",
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
                if (note := document_benchmark_note(report)) is not None:
                    out += ["", note]
                out += ["", "Metrics: " + _doc_link_list(rows) + "."]
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
        "Definitions, formulas, assumptions and references for every metric: the "
        f"[reference manual]({docs.manual}) of openfactsheet {docs.package_version} "
        f"(one topic per metric), the [metric catalog]({docs.catalog}), or "
        "`ofs.metric_catalog()`.",
        "",
        f"## {number + 3}. Assumptions & caveats",
        "",
        *_kv_block(report.assumptions.describe()),
    ]
    material = [f for f in report.diagnostics.findings if f.severity != "info"]
    if material:
        out += ["", "**Material data-quality findings:**", ""]
        out += [f"- *{f.severity}*: {_cell(f.message)}" for f in material]
    out += ["", f"{SHORT_DISCLAIMER} [Full disclaimer]({docs.source(DISCLAIMER_PATH)})."]
    if notes.texts:
        out += ["", "## Notes", ""]
        out += [f"{i}. {_cell(t)}" for i, t in enumerate(notes.texts, start=1)]
    return "\n".join(out) + "\n"
