"""Plain-text (terminal) rendering of the canonical report."""

from __future__ import annotations

import textwrap

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

WIDTH = 100
_LABEL_WIDTH = 27  # width of the "Label:   " column in key/value blocks


def _indent(text: str, prefix: str = "  ") -> str:
    """Indent a key/value block, wrapping long values under their value column."""
    lines: list[str] = []
    for line in text.splitlines():
        if not line:
            lines.append(line)
            continue
        stripped = line.lstrip()
        if stripped.startswith(("[", "-")):  # list items: hang under the item text
            hang = " " * (len(line) - len(stripped) + 4)
        else:  # "Label:   value" rows: hang under the value column
            hang = " " * _LABEL_WIDTH
        lines.append(
            textwrap.fill(
                line,
                WIDTH,
                initial_indent=prefix,
                subsequent_indent=prefix + hang,
                break_on_hyphens=False,
            )
        )
    return "\n".join(lines)


def _wrap(text: str, prefix: str = "  ") -> str:
    return textwrap.fill(text, WIDTH, initial_indent=prefix, subsequent_indent=prefix)


def _heading(number: int, title: str) -> str:
    return f"\n{number}. {title.upper()}\n" + "-" * WIDTH


def _metric_table(rows: list[MetricResult], notes: Footnotes) -> list[str]:
    out = [f"  {'Metric':<44}{'Value':>14}  {'Confidence / status':<22}Notes"]
    for r in rows:
        ref_text = " ".join(f"[{notes.ref(t)}]" for t in result_notes(r))
        out.append(f"  {r.name:<44}{format_value(r):>14}  {status_label(r):<22}{ref_text}")
    return out


def _episode_table(report: FactsheetReport) -> list[str]:
    table = drawdown_episode_table(report)
    if table is None:
        return []
    out = ["", "  Drawdown episodes:"]
    if table.rows:
        widths = [
            max(len(h), *(len(r[i]) for r in table.rows))
            for i, h in enumerate(EPISODE_TABLE_HEADER)
        ]
        header = zip(EPISODE_TABLE_HEADER, widths, strict=True)
        out.append(("  " + "  ".join(h.ljust(w) for h, w in header)).rstrip())
        out.extend(
            ("  " + "  ".join(c.ljust(w) for c, w in zip(row, widths, strict=True))).rstrip()
            for row in table.rows
        )
    out.append(_wrap(table.note))
    return out


def _factor_section(report: FactsheetReport, notes: Footnotes) -> list[str]:
    rows = factor_metrics(report)
    fa = report.factor_analysis
    if fa is None:
        return [
            _wrap(FACTOR_SECTION_TEXT),
            _wrap("Metrics: " + ", ".join(r.name for r in rows) + "."),
        ]
    out = [_indent(fa.to_text()), ""]
    loadings = factor_loading_rows(report)
    if loadings:
        widths = [
            max(len(h), *(len(r[i]) for r in loadings)) for i, h in enumerate(LOADING_TABLE_HEADER)
        ]

        def line(cells: tuple[str, ...]) -> str:
            # Names left-aligned, numbers right-aligned.
            padded = (
                c.rjust(w) if i else c.ljust(w)
                for i, (c, w) in enumerate(zip(cells, widths, strict=True))
            )
            return ("  " + "  ".join(padded)).rstrip()

        out.append(line(LOADING_TABLE_HEADER))
        out.extend(line(row) for row in loadings)
        out.append(_wrap(factor_fit_summary(report)))
        out.append("")
    out.extend(_metric_table(rows, notes))
    return out


def render_terminal(report: FactsheetReport) -> str:
    notes = Footnotes([])
    p = report.provenance
    out: list[str] = [
        "=" * WIDTH,
        f"OPENFACTSHEET — {report.name}",
        f"Canonical report · {report.assumptions.name} · openfactsheet {p.package_version}",
        "=" * WIDTH,
    ]

    out.append(_heading(1, "Input & methodology"))
    out.append(_indent(report.input_summary.to_text()))
    extraction = extraction_summary(report)
    if extraction is not None:
        text, table = extraction
        out.append("\n  Source document:")
        out.append(_indent(text))
        out.append("  Reconstructed table (as read):")
        out.extend("    " + line for line in table.splitlines())
    out.append(_wrap(f"Annualization: {p.annualization}"))
    out.append(_wrap("Risk-free rate: 0% in methodology 0.1.0 (see section 14)."))

    out.append(_heading(2, "Data-quality diagnostics"))
    out.append(_indent(report.diagnostics.to_text()))
    out.append("\n  Serial dependence & smoothing:")
    out.extend(_metric_table(data_quality_metrics(report), notes))

    number = 3
    for cat, title, rows in ordered_categories(report):
        out.append(_heading(number, title))
        number += 1
        if cat == "benchmark":
            if report.benchmark_summary is None:
                out.append(_wrap("Not applicable: " + NO_BENCHMARK_REASON))
                if (note := document_benchmark_note(report)) is not None:
                    out.append(_wrap(note))
                out.append(_wrap("Metrics: " + ", ".join(r.name for r in rows) + "."))
                continue
            out.append(_indent(report.benchmark_summary.to_text()))
            out.append("")
        out.extend(_metric_table(rows, notes))
        if cat == "drawdown":
            out.extend(_episode_table(report))

    out.append(_heading(number, "Factor analysis"))
    number += 1
    out.extend(_factor_section(report, notes))

    out.append(_heading(number, "Statistical confidence"))
    number += 1
    counts = confidence_counts(report)
    out.append(_wrap(", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in sorted(counts.items()))))
    out.append(_wrap(CONFIDENCE_DISCLAIMER + " " + STATISTICAL_SECTION_TEXT))
    out.append("")
    out.extend(_metric_table(statistical_metrics(report), notes))

    out.append(_heading(number, "Metric catalog"))
    number += 1
    out.append(
        _wrap(
            "Definitions, formulas, assumptions and references for every metric: "
            "ofs.metric_catalog() or docs/metric_catalog.md."
        )
    )

    out.append(_heading(number, "Assumptions & caveats"))
    out.append(_indent(report.assumptions.describe()))
    material = [f for f in report.diagnostics.findings if f.severity != "info"]
    if material:
        out.append("  Material data-quality findings:")
        out.extend(_wrap(f"- [{f.severity}] {f.message}", "    ") for f in material)
    out.append(_wrap("OpenFactsheet explains measurements; it does not give investment advice."))

    if notes.texts:
        out.append("\nNOTES\n" + "-" * WIDTH)
        for i, text in enumerate(notes.texts, start=1):
            out.append(
                textwrap.fill(text, WIDTH, initial_indent=f"  [{i}] ", subsequent_indent="      ")
            )
    out.append("=" * WIDTH)
    return "\n".join(out)
