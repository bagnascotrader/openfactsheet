"""Markdown rendering of the canonical report."""

from __future__ import annotations

from openfactsheet.interpretation.glossary import CONFIDENCE_DISCLAIMER
from openfactsheet.models.metric import MetricResult
from openfactsheet.models.report import FactsheetReport
from openfactsheet.policy.applicability import NO_BENCHMARK_REASON
from openfactsheet.report.tables import (
    FACTOR_SECTION_TEXT,
    STATISTICAL_SECTION_TEXT,
    Footnotes,
    confidence_counts,
    data_quality_metrics,
    format_value,
    ordered_categories,
    result_notes,
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


def render_markdown(report: FactsheetReport) -> str:
    notes = Footnotes([])
    p = report.provenance
    out: list[str] = [
        f"# OpenFactsheet — {_cell(report.name)}",
        "",
        f"*Canonical report · {report.assumptions.name} · openfactsheet {p.package_version}*",
        "",
        "## 1. Input & methodology",
        "",
        *_kv_block(report.input_summary.to_text()),
        "",
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

    counts = confidence_counts(report)
    out += [
        "",
        f"## {number}. Factor analysis",
        "",
        FACTOR_SECTION_TEXT,
        "",
        f"## {number + 1}. Statistical confidence",
        "",
        ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in sorted(counts.items())),
        "",
        CONFIDENCE_DISCLAIMER + " " + STATISTICAL_SECTION_TEXT,
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
