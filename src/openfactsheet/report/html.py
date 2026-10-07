"""Self-contained HTML rendering of the canonical report, with charts (decision 0026).

The page is a single file with no external resources (local-first: it can be
opened offline and never calls out to a CDN). Canonical sections and charts
cannot be removed by a flag (CLAUDE.md section 43). Colors are theme tokens
(light and dark), validated for color-vision deficiency; every chart has a
caption and a data table, and tooltips only repeat values that are also shown.
Every metric name links to the topic of the reference manual that defines it
(decision 0035).
"""

from __future__ import annotations

from html import escape

from openfactsheet.interpretation.glossary import CONFIDENCE_DISCLAIMER
from openfactsheet.models.metric import MetricResult
from openfactsheet.models.report import FactsheetReport
from openfactsheet.policy.applicability import NO_BENCHMARK_REASON
from openfactsheet.report.charts import Chart, build_charts
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

# Fixed, methodology-chosen headline figures: return, risk, drawdown and tail
# together, never a hand-picked subset. Every metric is also in the tables below.
HEADLINE_METRICS = (
    "cumulative_return",
    "cagr",
    "annualized_volatility",
    "max_drawdown",
    "expected_shortfall_historical_95",
    "sharpe_ratio",
)

_CSS = """
.ofs{color-scheme:light;
--surface:#fcfcfb;--page:#f9f9f7;--ink:#0b0b0b;--ink-2:#52514e;--muted:#898781;
--grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);
--series-1:#2a78d6;--series-2:#eb6834;--gain:#2a78d6;--loss:#e34948;--neutral:#f0efec;
--low:#8a5a00}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])) .ofs{
color-scheme:dark;--surface:#1a1a19;--page:#0d0d0d;--ink:#fff;--ink-2:#c3c2b7;--muted:#898781;
--grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);
--series-1:#3987e5;--series-2:#d95926;--gain:#3987e5;--loss:#e66767;--neutral:#383835;
--low:#fab219}}
:root[data-theme="dark"] .ofs{color-scheme:dark;--surface:#1a1a19;--page:#0d0d0d;--ink:#fff;
--ink-2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);
--series-1:#3987e5;--series-2:#d95926;--gain:#3987e5;--loss:#e66767;--neutral:#383835;
--low:#fab219}
body{margin:0;background:var(--page,#f9f9f7)}
.ofs{background:var(--page);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",
Roboto,sans-serif;padding:2rem 1rem 4rem}
.ofs main{max-width:62rem;margin:0 auto}
.ofs header{border-bottom:1px solid var(--border);padding-bottom:1rem;margin-bottom:1.5rem}
.ofs .brand{font-size:.8rem;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-2)}
.ofs h1{font-size:1.9rem;margin:.2rem 0 .3rem;font-weight:650}
.ofs .sub{color:var(--ink-2);margin:0}
.ofs h2{font-size:1.15rem;margin:2.4rem 0 .8rem;padding-bottom:.35rem;
border-bottom:1px solid var(--border)}
.ofs h3{font-size:1rem;margin:1.4rem 0 .5rem}
.ofs pre{background:var(--surface);border:1px solid var(--border);border-radius:8px;
padding:.8rem 1rem;overflow-x:auto;font-size:.82rem;color:var(--ink-2)}
.ofs table{border-collapse:collapse;width:100%;font-size:.88rem;background:var(--surface);
border:1px solid var(--border);border-radius:8px}
.ofs th,.ofs td{padding:.4rem .6rem;border-bottom:1px solid var(--grid);text-align:left;
vertical-align:top}
.ofs th{color:var(--ink-2);font-weight:600}
.ofs td.v{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ofs tr.low td{color:var(--low)}.ofs tr.na td{color:var(--muted)}
.ofs a{color:var(--series-1)}
.ofs a.doc{color:inherit;text-decoration:none;border-bottom:1px dotted var(--axis)}
.ofs a.doc:hover,.ofs a.doc:focus{border-bottom-color:currentColor;
text-decoration:underline}
.ofs .manual{font-size:.82rem;color:var(--ink-2);margin:.2rem 0 0}
@media print{.ofs a.doc{border-bottom:none}}
.ofs .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(9.5rem,1fr));gap:.6rem;
margin:1rem 0 .4rem}
.ofs .tile{background:var(--surface);border:1px solid var(--border);border-radius:10px;
padding:.7rem .8rem}
.ofs .tile .l{font-size:.78rem;color:var(--ink-2)}
.ofs .tile .n{font-size:1.35rem;font-weight:600;margin:.1rem 0}
.ofs .tile .c{font-size:.72rem;color:var(--muted)}
.ofs .tiles-note{font-size:.78rem;color:var(--muted);margin:0 0 .5rem}
.ofs figure{margin:1rem 0 1.4rem;background:var(--surface);border:1px solid var(--border);
border-radius:10px;padding:1rem 1rem .6rem}
.ofs figcaption{font-size:.82rem;color:var(--ink-2);margin-bottom:.6rem}
.ofs figcaption strong{display:block;font-size:.95rem;color:var(--ink);margin-bottom:.15rem}
.ofs .legend{display:flex;gap:1rem;font-size:.8rem;color:var(--ink-2);margin:.2rem 0 .4rem}
.ofs .legend i{display:inline-block;width:14px;height:2px;margin-right:.35rem;
vertical-align:middle}
.ofs details{margin-top:.4rem;font-size:.8rem}
.ofs details summary{cursor:pointer;color:var(--ink-2)}
.ofs details .scroll{max-height:18rem;overflow:auto;margin-top:.4rem}
.ofs .na-chart{font-size:.85rem;color:var(--muted);font-style:italic}
.ofs ol.notes{font-size:.82rem;color:var(--ink-2)}
.ofs-chart{width:100%;height:auto;display:block;overflow:visible}
.ofs-chart .grid{stroke:var(--grid);stroke-width:1}
.ofs-chart .axis{stroke:var(--axis);stroke-width:1}
.ofs-chart .baseline{stroke:var(--axis);stroke-width:1.2}
.ofs-chart .marker{stroke:var(--ink-2);stroke-width:1}
.ofs-chart .tick,.ofs-chart .note{fill:var(--muted);font-size:11px;
font-variant-numeric:tabular-nums}
.ofs-chart .note{fill:var(--ink-2)}
.ofs-chart .value,.ofs-chart .endlabel{fill:var(--ink-2);font-size:11px;font-weight:600}
.ofs-chart .line{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.ofs-chart .line.thin{stroke-width:1.2;opacity:.8}
.ofs-chart .area{opacity:.12;stroke:none}
.ofs-chart .dot{stroke:var(--surface);stroke-width:2}
.ofs-chart .bar{fill:var(--c)}
.ofs-chart .bar.partial{fill:var(--surface);stroke:var(--c);stroke-width:1.5}
.ofs-chart .bar:hover,.ofs-chart .bar:focus{opacity:.8;outline:none}
.ofs-chart .cell{stroke:none}.ofs-chart .cell:hover,.ofs-chart .cell:focus{
stroke:var(--ink);stroke-width:1.5;outline:none}
.ofs-chart .cell.missing{fill:none;stroke:var(--grid);stroke-width:1}
.ofs-chart .yearcell{fill:var(--page)}
.ofs-chart .yearcell.partial{fill:none;stroke:var(--axis);stroke-width:1}
.ofs-chart .celltext{fill:var(--ink);font-size:10.5px;font-variant-numeric:tabular-nums;
text-anchor:middle;pointer-events:none}
.ofs-chart .celltext.strong{fill:#fff}
.ofs-chart .xhair{stroke:var(--muted);stroke-width:1;visibility:hidden;pointer-events:none}
.ofs-tip{position:fixed;z-index:10;pointer-events:none;background:var(--surface,#fff);
color:var(--ink-2,#333);border:1px solid var(--border,#ccc);border-radius:6px;
padding:.35rem .55rem;font:12px/1.35 system-ui,sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.12)}
.ofs-tip .v{color:var(--ink,#000);font-weight:600}
@media print{.ofs{background:#fff;padding:0}.ofs figure,.ofs table{break-inside:avoid}
.ofs details{display:none}}
"""

# Hover/focus layer. Tooltips repeat values that are also in captions, labels or
# the data tables (they never gate a value). Text is inserted with textContent.
_SCRIPT = """
(function(){
var tip=document.createElement('div');tip.className='ofs-tip';tip.hidden=true;
(document.querySelector('.ofs')||document.body).appendChild(tip);
function show(lines,x,y){tip.replaceChildren();lines.forEach(function(t,i){
var d=document.createElement('div');d.textContent=t;if(i===0){d.className='v';}
tip.appendChild(d);});tip.hidden=false;var w=tip.offsetWidth,h=tip.offsetHeight;
var left=Math.min(x+14,window.innerWidth-w-8),top=Math.max(8,y-h-10);
tip.style.left=left+'px';tip.style.top=top+'px';}
function hide(){tip.hidden=true;}
document.querySelectorAll('.ofs-chart [data-tip]').forEach(function(el){
var lines=el.getAttribute('data-tip').split('\\n');
el.addEventListener('pointermove',function(e){show(lines,e.clientX,e.clientY);});
el.addEventListener('pointerleave',hide);
el.addEventListener('focus',function(){var r=el.getBoundingClientRect();
show(lines,r.left+r.width/2,r.top);});
el.addEventListener('blur',hide);});
document.querySelectorAll('svg.ofs-chart[data-points]').forEach(function(svg){
var pts=JSON.parse(svg.getAttribute('data-points'));var xh=svg.querySelector('.xhair');
if(!pts.length||!xh){return;}
svg.addEventListener('pointermove',function(e){var m=svg.getScreenCTM();if(!m){return;}
var p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;var loc=p.matrixTransform(m.inverse());
var lo=0,hi=pts.length-1;while(hi-lo>1){var mid=(lo+hi)>>1;if(pts[mid][0]<loc.x){lo=mid;}
else{hi=mid;}}var k=Math.abs(pts[lo][0]-loc.x)<=Math.abs(pts[hi][0]-loc.x)?lo:hi;
xh.setAttribute('x1',pts[k][0]);xh.setAttribute('x2',pts[k][0]);
xh.style.visibility='visible';show(pts[k][1],e.clientX,e.clientY);});
svg.addEventListener('pointerleave',function(){xh.style.visibility='hidden';hide();});});
})();
"""


def _pre(text: str) -> str:
    return f"<pre>{escape(text)}</pre>"


def _doc_link(result: MetricResult) -> str:
    """The metric's name, linked to the manual topic that defines it (decision 0035)."""
    return (
        f"<a class='doc' href='{escape(result.documentation)}' target='_blank' rel='noopener' "
        f"title='{escape(result.name)} in the OpenFactsheet reference manual: formula, "
        f"assumptions, interpretation and references'>{escape(result.name)}</a>"
    )


def _doc_link_list(rows: list[MetricResult]) -> str:
    """Names of metrics that have no table in this section, each linked to its topic."""
    return ", ".join(_doc_link(r) for r in rows)


def _metric_table(rows: list[MetricResult], notes: Footnotes) -> list[str]:
    parts = [
        "<table><thead><tr><th>Metric</th><th>Value</th><th>Confidence / status</th>"
        "<th>Notes</th></tr></thead><tbody>"
    ]
    for r in rows:
        refs = " ".join(f"[{notes.ref(t)}]" for t in result_notes(r))
        css = "na" if r.value is None else ("low" if r.confidence == "low" else "")
        parts.append(
            f"<tr class='{css}'><td>{_doc_link(r)}</td><td class='v'>"
            f"{escape(format_value(r))}</td><td>{escape(status_label(r))}</td>"
            f"<td>{escape(refs)}</td></tr>"
        )
    parts.append("</tbody></table>")
    return parts


def _figure(chart: Chart) -> list[str]:
    if not chart.svg:
        return [
            f"<p class='na-chart'>Chart not shown ({escape(chart.title)}): "
            f"{escape(chart.unavailable_reason or 'not available')}</p>"
        ]
    parts = [
        f"<figure id='chart-{escape(chart.id)}'><figcaption><strong>{escape(chart.title)}</strong>"
        f"{escape(chart.caption)}</figcaption>"
    ]
    if len(chart.legend) >= 2:
        parts.append("<div class='legend'>")
        parts += [
            f"<span><i style='background:var({css})'></i>{escape(label)}</span>"
            for css, label in chart.legend
        ]
        parts.append("</div>")
    parts.append(chart.svg)
    if chart.table_rows:
        head = "".join(f"<th>{escape(h)}</th>" for h in chart.table_header)
        body = "".join(
            "<tr>" + "".join(
                f"<td class='v'>{escape(c)}</td>" if i else f"<td>{escape(c)}</td>"
                for i, c in enumerate(row)
            ) + "</tr>"
            for row in chart.table_rows
        )  # fmt: skip
        parts.append(
            f"<details><summary>Data table ({len(chart.table_rows)} rows)</summary>"
            f"<div class='scroll'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody>"
            "</table></div></details>"
        )
    parts.append("</figure>")
    return parts


def _extraction_block(report: FactsheetReport) -> list[str]:
    extraction = extraction_summary(report)
    if extraction is None:
        return []
    text, table = extraction
    return [
        "<h3>Source document</h3>",
        _pre(text),
        "<p class='tiles-note'>Reconstructed table, exactly as read:</p>",
        _pre(table),
    ]


def _episode_table(report: FactsheetReport) -> list[str]:
    table = drawdown_episode_table(report)
    if table is None:
        return []
    parts = ["<h3>Drawdown episodes</h3>"]
    if table.rows:
        head = "".join(f"<th>{escape(h)}</th>" for h in EPISODE_TABLE_HEADER)
        body = "".join(
            "<tr>" + "".join(
                f"<td class='v'>{escape(c)}</td>" if i in (0, 4, 5, 6, 7)
                else f"<td>{escape(c)}</td>"
                for i, c in enumerate(row)
            ) + "</tr>"
            for row in table.rows
        )  # fmt: skip
        parts.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
    parts.append(f"<p class='tiles-note'>{escape(table.note)}</p>")
    return parts


def _factor_section(report: FactsheetReport, notes: Footnotes) -> list[str]:
    rows = factor_metrics(report)
    fa = report.factor_analysis
    if fa is None:
        return [f"<p>{escape(FACTOR_SECTION_TEXT)}</p><p>Metrics: {_doc_link_list(rows)}.</p>"]
    parts = [_pre(fa.to_text())]
    loadings = factor_loading_rows(report)
    if loadings:
        head = "".join(f"<th>{escape(h)}</th>" for h in LOADING_TABLE_HEADER)
        body = "".join(
            "<tr>" + "".join(
                f"<td class='v'>{escape(c)}</td>" if i else f"<td>{escape(c)}</td>"
                for i, c in enumerate(row)
            ) + "</tr>"
            for row in loadings
        )  # fmt: skip
        parts.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
        parts.append(f"<p class='tiles-note'>{escape(factor_fit_summary(report))}</p>")
    parts += _metric_table(rows, notes)
    return parts


def _headline(report: FactsheetReport) -> list[str]:
    parts = ["<div class='tiles'>"]
    for mid in HEADLINE_METRICS:
        m = report.metrics.get(mid)
        if m is None:
            continue
        status = status_label(m) if m.value is not None else m.status.replace("_", " ")
        parts.append(
            f"<div class='tile'><div class='l'>{escape(m.name)}</div>"
            f"<div class='n'>{escape(format_value(m))}</div>"
            f"<div class='c'>{escape(status)}</div></div>"
        )
    years = report.input_summary.years
    history = f"{years:.1f} years" if years is not None else "undated"
    parts.append(
        f"<div class='tile'><div class='l'>Track record</div><div class='n'>{escape(history)}"
        f"</div><div class='c'>{report.input_summary.observations} observations</div></div>"
    )
    parts.append(
        f"<div class='tile'><div class='l'>Smoothing risk</div>"
        f"<div class='n'>{escape(report.diagnostics.smoothing_risk.replace('_', ' '))}</div>"
        f"<div class='c'>lag-1 autocorrelation</div></div>"
    )
    parts.append("</div>")
    parts.append(
        "<p class='tiles-note'>Fixed headline set chosen by the methodology (return, risk, "
        "drawdown, tail, risk-adjusted, track record, data quality). Every canonical metric is "
        "reported below with its confidence and caveats.</p>"
    )
    return parts


def render_html(report: FactsheetReport) -> str:
    notes = Footnotes([])
    p = report.provenance
    docs = report.documentation
    charts = build_charts(report)
    by_section: dict[str, list[Chart]] = {}
    for c in charts:
        by_section.setdefault(c.section, []).append(c)
    s = report.input_summary
    period = f"{s.start} to {s.end}" if s.start else "undated observations"
    parts: list[str] = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>OpenFactsheet — {escape(report.name)}</title><style>{_CSS}</style></head>",
        "<body><div class='ofs'><main>",
        "<header><div class='brand'>OpenFactsheet · canonical report</div>",
        f"<h1>{escape(report.name)}</h1>",
        f"<p class='sub'>{escape(period)} · {s.observations} {escape(s.frequency.value)} returns "
        f"· {escape(report.assumptions.name)} · openfactsheet {escape(p.package_version)}</p>",
        f"<p class='manual'>Every metric below links to its topic in the "
        f"<a href='{escape(docs.manual)}' target='_blank' rel='noopener'>reference manual</a>"
        f"{'' if docs.released else ' built from the development branch'}: formula, "
        "assumptions, interpretation and references.</p>",
        "</header>",
        *_headline(report),
        "<h2>1. Input &amp; methodology</h2>",
        _pre(report.input_summary.to_text()),
        *_extraction_block(report),
        f"<p><strong>Annualization:</strong> {escape(p.annualization)}<br>"
        "<strong>Risk-free rate:</strong> 0% in methodology 0.1.0.</p>",
        "<h2>2. Data-quality diagnostics</h2>",
        _pre(report.diagnostics.to_text()),
        "<h3>Serial dependence &amp; smoothing</h3>",
        *_metric_table(data_quality_metrics(report), notes),
    ]
    number = 3
    for cat, title, rows in ordered_categories(report):
        parts.append(f"<h2>{number}. {escape(title)}</h2>")
        number += 1
        if cat == "benchmark":
            if report.benchmark_summary is None:
                parts.append(f"<p>Not applicable: {escape(NO_BENCHMARK_REASON)}</p>")
                if (note := document_benchmark_note(report)) is not None:
                    parts.append(f"<p>{escape(note)}</p>")
                parts.append(f"<p>Metrics: {_doc_link_list(rows)}.</p>")
                continue
            parts.append(_pre(report.benchmark_summary.to_text()))
        for chart in by_section.get(cat, []):
            parts += _figure(chart)
        parts += _metric_table(rows, notes)
        if cat == "drawdown":
            parts += _episode_table(report)
    counts = confidence_counts(report)
    parts.append(f"<h2>{number}. Factor analysis</h2>")
    parts += _factor_section(report, notes)
    parts += [
        f"<h2>{number + 1}. Statistical confidence</h2><p>"
        + escape(", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in sorted(counts.items())))
        + f"</p><p>{escape(CONFIDENCE_DISCLAIMER + ' ' + STATISTICAL_SECTION_TEXT)}</p>",
        *_metric_table(statistical_metrics(report), notes),
        f"<h2>{number + 2}. Metric catalog</h2><p>Definitions, formulas, assumptions and "
        f"references for every metric: the <a href='{escape(docs.manual)}' target='_blank' "
        f"rel='noopener'>reference manual</a> of openfactsheet "
        f"{escape(docs.package_version)} (one topic per metric), the "
        f"<a href='{escape(docs.catalog)}' target='_blank' rel='noopener'>metric catalog</a>, "
        "or <code>ofs.metric_catalog()</code>.</p>",
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
    parts.append(f"</main></div><script>{_SCRIPT}</script></body></html>")
    return "\n".join(parts)
