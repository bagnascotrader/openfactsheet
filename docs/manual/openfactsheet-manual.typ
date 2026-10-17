// OpenFactsheet reference manual (decision 0034).
//
// Built by scripts/build_manual.py, which generates data/*.json from the code and
// md/*.md from the repository's documents. Every topic carries a label that
// becomes a PDF named destination (metric-<id>, api-<name>, decision-<nnnn>, ...).
#import "lib/style.typ": *
#import "lib/topics.typ": *

#let package = json("/data/package.json")
#let metrics = json("/data/metrics.json")
#let api = json("/data/api.json")
#let bib = json("/data/bibliography.json")
#let documents = json("/data/documents.json").documents
#let date = sys.inputs.at("date", default: "unreleased")
#let compiler = sys.inputs.at("typst", default: "")
#let digest = sys.inputs.at("digest", default: "none")

#let citations = (:)
#for e in bib.entries { citations.insert(e.citation, e) }
#let decision-titles = (:)
#for d in documents.filter(d => "number" in d) { decision-titles.insert(d.number, d.title) }
#let metric-names = (:)
#for m in metrics.metrics { metric-names.insert(m.id, m.name) }
#let docs-in(part) = documents.filter(d => d.part == part)

#show: setup.with(package: package, date: date, digest: digest)

// --- Title page (the DESCRIPTION of an R package) ----------------------------
#page(header: none, footer: none)[
  #v(3cm)
  #text(size: 26pt, weight: "bold")[Package '#package.name']
  #v(0.2em)
  #text(size: 12pt, fill: muted)[Reference manual #sym.dot.c version #package.version #sym.dot.c #date]
  #v(1.2cm)
  #let dep(d) = d.replace(regex("^([A-Za-z0-9_.\-]+(?:\[[^\]]*\])?)(.*)$"), m => {
    let (name, spec) = m.captures
    if spec == "" { name } else { name + " (" + spec.replace(",", ", ") + ")" }
  })
  #let url(u) = link(u, raw(u))
  #set par(justify: false)
  #deflist(term-width: 8.5em, (
    ([*Type*], [Python package]),
    ([*Title*], [#package.description]),
    ([*Version*], [#package.version]),
    ([*Methodology*], [OpenFactsheet Methodology #package.methodology_version]),
    ([*Depends*], [Python (#package.requires_python)]),
    ([*Imports*], [#package.dependencies.map(dep).join(", ")]),
    ([*Suggests*], [#package.extras.pairs().map(((k, v)) => [#raw("[" + k + "]"): #v.map(dep).join(", ")]).join([; ])]),
    ([*License*], [#package.license]),
    ([*URL*], [#url(package.urls.Homepage)]),
    ([*BugReports*], [#url(package.urls.Issues)]),
    ([*Author*], [#package.authors.join(", ")]),
    ([*Contents*], [#api.topics.len() API topics, #metrics.metrics.len() metrics in #metrics.categories.len() categories, #docs-in("decisions").filter(d => "number" in d).len() methodology decisions, #bib.entries.len() references]),
    ([*Built with*], [Typst #compiler, from the source code of this version; do not edit by hand]),
  ))
  #v(1fr)
  #text(size: 9pt, fill: muted)[
    Every metric, function and decision in this manual has a stable link target, e.g.
    #raw("openfactsheet-manual.pdf#nameddest=metric-sharpe_ratio"). OpenFactsheet
    explains measurements; it does not give investment advice.
  ]
  #v(0.6em)
  #block(stroke: 0.5pt + muted, inset: 8pt, width: 100%)[
    #text(size: 9pt)[
      *Release #package.version.* #package.short_disclaimer
      See #link(<doc-disclaimer>)[Important information and disclaimers].
    ]
  ]
]

#outline(title: [Contents], depth: 3, indent: 1.2em)

= Overview and usage <part-overview>
#for d in docs-in("overview") { document-topic(d) }

= Functions and classes <part-api>
#text(fill: muted)[
  The public interface of `import openfactsheet as ofs`. Each topic lists the
  usage, arguments, value and examples, taken from the docstrings of the code.
]
#for t in api.topics { api-topic(t) }

= Metrics <part-metrics>
#[
  Every canonical metric of methodology #metrics.methodology_version, grouped by report
  section. Every report computes all of them; one that cannot be computed is reported
  with a status and a reason, never omitted. For each metric: what it measures, the
  exact formula, how to read the value, the assumptions, when it misleads, the
  minimum data, the exact calculation and confidence criteria, reference
  implementations and sources. Symbols are defined in #link(<doc-notation>)[Notation];
  thresholds in #link(<doc-policies>)[Policies, thresholds and constants].
]
#metrics-part(metrics, citations, decision-titles)

= Methodology <part-methodology>
#for d in docs-in("methodology") { document-topic(d) }

= Methodology decisions <part-decisions>
#for d in docs-in("decisions") { document-topic(d) }

= Validation <part-validation>
#for d in docs-in("validation") { document-topic(d) }

= Bibliography <bibliography>
#bibliography-part(bib, metric-names)

= Index <topic-index>
#{
  let entries = ()
  for m in metrics.metrics {
    entries.push((key: m.name, text: m.name, anchor: m.anchor))
    entries.push((key: m.id, text: raw(m.id), anchor: m.anchor))
  }
  for t in api.topics {
    entries.push((key: t.name, text: if t.kind in ("exceptions", "constants") { t.name } else { raw(t.name) }, anchor: t.anchor))
    for m in t.at("members", default: ()) {
      entries.push((key: t.name + "." + m.name, text: raw(t.name + "." + m.name), anchor: t.anchor))
    }
    for c in t.at("classes", default: ()) + t.at("constants", default: ()) {
      entries.push((key: c.name.trim("_"), text: raw(c.name), anchor: c.anchor))
    }
  }
  for d in documents {
    let text = if "number" in d { d.title + " (decision " + d.number + ")" } else { d.title }
    entries.push((key: text, text: text, anchor: d.anchor))
  }
  for c in metrics.categories {
    entries.push((key: c.title, text: [#c.title (metrics)], anchor: "category-" + c.id))
  }
  index-part(entries)
}
