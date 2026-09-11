"""Plain-text (terminal) rendering of the canonical report."""

from __future__ import annotations

import textwrap

from openfactsheet.interpretation.glossary import CONFIDENCE_DISCLAIMER
from openfactsheet.models.report import FactsheetReport
from openfactsheet.policy.applicability import NO_BENCHMARK_REASON
from openfactsheet.report.tables import (
    FACTOR_SECTION_TEXT,
    STATISTICAL_SECTION_TEXT,
    Footnotes,
    confidence_counts,
    format_value,
    ordered_categories,
    result_notes,
    status_label,
)

WIDTH = 100


def _indent(text: str, prefix: str = "  ") -> str:
    return "\n".join(prefix + line if line else line for line in text.splitlines())


def _wrap(text: str, prefix: str = "  ") -> str:
    return textwrap.fill(text, WIDTH, initial_indent=prefix, subsequent_indent=prefix)


def _heading(number: int, title: str) -> str:
    return f"\n{number}. {title.upper()}\n" + "-" * WIDTH


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
    out.append(_wrap(f"Annualization: {p.annualization}"))
    out.append(_wrap("Risk-free rate: 0% in methodology 0.1.0 (see section 14)."))

    out.append(_heading(2, "Data-quality diagnostics"))
    out.append(_indent(report.diagnostics.to_text()))

    number = 3
    for cat, title, rows in ordered_categories(report):
        out.append(_heading(number, title))
        number += 1
        if cat == "benchmark":
            if report.benchmark_summary is None:
                out.append(_wrap("Not applicable: " + NO_BENCHMARK_REASON))
                out.append(_wrap("Metrics: " + ", ".join(r.name for r in rows) + "."))
                continue
            out.append(_indent(report.benchmark_summary.to_text()))
            out.append("")
        out.append(f"  {'Metric':<44}{'Value':>14}  {'Confidence / status':<22}Notes")
        for r in rows:
            refs = [notes.ref(t) for t in result_notes(r)]
            ref_text = " ".join(f"[{i}]" for i in refs)
            out.append(f"  {r.name:<44}{format_value(r):>14}  {status_label(r):<22}{ref_text}")

    out.append(_heading(number, "Factor analysis"))
    number += 1
    out.append(_wrap(FACTOR_SECTION_TEXT))

    out.append(_heading(number, "Statistical confidence"))
    number += 1
    counts = confidence_counts(report)
    out.append(_wrap(", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in sorted(counts.items()))))
    out.append(_wrap(CONFIDENCE_DISCLAIMER + " " + STATISTICAL_SECTION_TEXT))

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
