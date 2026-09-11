"""Static HTML rendering (tables only; charts are roadmap phase 4).

Canonical sections cannot be removed by a flag (CLAUDE.md section 43).
"""

from __future__ import annotations

from html import escape

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

_CSS = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:60rem;
margin:2rem auto;padding:0 1rem;color:#1b1f24;line-height:1.45}
h1{font-size:1.6rem;margin-bottom:.2rem}h2{font-size:1.15rem;margin-top:2rem;
border-bottom:1px solid #d0d7de;padding-bottom:.25rem}
.sub{color:#57606a;margin-top:0}pre{background:#f6f8fa;padding:.75rem;overflow-x:auto;
font-size:.85rem}table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{padding:.35rem .5rem;border-bottom:1px solid #eaeef2;text-align:left;vertical-align:top}
td.v{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.low{color:#9a6700}.na{color:#6e7781}ol.notes{font-size:.85rem;color:#424a53}
"""


def _pre(text: str) -> str:
    return f"<pre>{escape(text)}</pre>"


def render_html(report: FactsheetReport) -> str:
    notes = Footnotes([])
    p = report.provenance
    parts: list[str] = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>OpenFactsheet — {escape(report.name)}</title><style>{_CSS}</style></head><body>",
        f"<h1>OpenFactsheet — {escape(report.name)}</h1>",
        f"<p class='sub'>Canonical report · {escape(report.assumptions.name)} · "
        f"openfactsheet {escape(p.package_version)}</p>",
        "<h2>1. Input &amp; methodology</h2>",
        _pre(report.input_summary.to_text()),
        f"<p><strong>Annualization:</strong> {escape(p.annualization)}<br>"
        "<strong>Risk-free rate:</strong> 0% in methodology 0.1.0.</p>",
        "<h2>2. Data-quality diagnostics</h2>",
        _pre(report.diagnostics.to_text()),
    ]
    number = 3
    for cat, title, rows in ordered_categories(report):
        parts.append(f"<h2>{number}. {escape(title)}</h2>")
        number += 1
        if cat == "benchmark":
            if report.benchmark_summary is None:
                parts.append(f"<p>Not applicable: {escape(NO_BENCHMARK_REASON)}</p>")
                continue
            parts.append(_pre(report.benchmark_summary.to_text()))
        parts.append(
            "<table><thead><tr><th>Metric</th><th>Value</th><th>Confidence / status</th>"
            "<th>Notes</th></tr></thead><tbody>"
        )
        for r in rows:
            refs = " ".join(f"[{notes.ref(t)}]" for t in result_notes(r))
            css = "na" if r.value is None else ("low" if r.confidence == "low" else "")
            parts.append(
                f"<tr class='{css}'><td>{escape(r.name)}</td><td class='v'>"
                f"{escape(format_value(r))}</td><td>{escape(status_label(r))}</td>"
                f"<td>{escape(refs)}</td></tr>"
            )
        parts.append("</tbody></table>")
    counts = confidence_counts(report)
    parts += [
        f"<h2>{number}. Factor analysis</h2><p>{escape(FACTOR_SECTION_TEXT)}</p>",
        f"<h2>{number + 1}. Statistical confidence</h2><p>"
        + escape(", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in sorted(counts.items())))
        + f"</p><p>{escape(CONFIDENCE_DISCLAIMER + ' ' + STATISTICAL_SECTION_TEXT)}</p>",
        f"<h2>{number + 2}. Metric catalog</h2><p>Definitions: <code>ofs.metric_catalog()</code> "
        "or docs/metric_catalog.md.</p>",
        f"<h2>{number + 3}. Assumptions &amp; caveats</h2>",
        _pre(report.assumptions.describe()),
    ]
    material = [f for f in report.diagnostics.findings if f.severity != "info"]
    if material:
        parts.append("<ul>")
        parts += [f"<li><em>{f.severity}</em>: {escape(f.message)}</li>" for f in material]
        parts.append("</ul>")
    parts.append("<p>OpenFactsheet explains measurements; it does not give investment advice.</p>")
    if notes.texts:
        parts.append("<h2>Notes</h2><ol class='notes'>")
        parts += [f"<li>{escape(t)}</li>" for t in notes.texts]
        parts.append("</ol>")
    parts.append("</body></html>")
    return "\n".join(parts)
