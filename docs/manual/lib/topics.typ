// Topic renderers: API functions and classes, metrics, documents, bibliography, index.
#import "style.typ": *

#let yes-no(b) = if b { "yes" } else { "no" }

#let bullets(items, empty: "None beyond the general inputs.") = {
  if items.len() == 0 { md(empty) } else { list(..items.map(i => md(i))) }
}

// --- API --------------------------------------------------------------------

#let arguments(items, params: ()) = {
  let by-name = (:)
  for p in params { by-name.insert(p.name, p) }
  deflist(items.map(a => {
    let p = by-name.at(a.name.trim("*"), default: none)
    let kind = if p != none and p.annotation != "" { text(size: 8.5pt, fill: muted)[ #raw(p.annotation)] } else { [] }
    (raw(a.name), [#md(a.text) #kind])
  }))
}

#let doc-sections(t, params: ()) = {
  if t.at("arguments", default: ()).len() > 0 { section("Arguments", arguments(t.arguments, params: params)) }
  if t.at("value", default: "") != "" { section("Value", md(t.value)) }
  if t.at("raises", default: "") != "" { section("Raises", md(t.raises)) }
  if t.at("details", default: "") != "" { section("Details", md(t.details)) }
  if t.at("examples", default: "") != "" { section("Examples", code(t.examples)) }
}

#let api-topic(t) = {
  topic-header(2, t.name, none, t.anchor, mono: t.kind != "exceptions" and t.kind != "constants")
  if t.kind == "function" {
    section("Description", md(t.description))
    section("Usage", code(t.usage))
    doc-sections(t, params: t.parameters)
  } else if t.kind == "class" or t.kind == "enum" {
    section("Description", md(t.description))
    if t.details != "" { section("Details", md(t.details)) }
    if t.kind == "enum" {
      section("Values", deflist(t.values.map(v => (raw(v.name), raw(v.value)))))
    }
    if t.fields.len() > 0 { section("Fields", arguments(t.fields)) }
    let members = t.members
    if members.len() > 0 {
      section("Usage", code(members.map(m => (
        if m.kind == "property" { "x." + m.usage } else { "x." + m.usage }
      )).join("\n")))
      section("Methods and properties", {
        for m in members {
          block(breakable: true, above: 0.9em)[
            #raw("." + m.usage) #h(0.4em) #text(size: 8.5pt, fill: muted, m.kind)
            #pad(left: 1.2em)[
              #md(m.description)
              #if m.details != "" { md(m.details) }
              #if m.arguments.len() > 0 { arguments(m.arguments, params: m.parameters) }
              #if m.value != "" [_Value:_ #md(m.value)]
            ]
          ]
        }
      })
    }
    if t.examples != "" { section("Examples", code(t.examples)) }
  } else if t.kind == "exceptions" {
    section("Description", md(t.description))
    section("Classes", {
      for c in t.classes {
        block(above: 0.8em)[
          #anchor(c.anchor)#raw(c.name) #h(0.4em) #text(size: 8.5pt, fill: muted)[subclass of #raw(c.base)]
          #pad(left: 1.2em, md(c.description))
        ]
      }
    })
  } else if t.kind == "constants" {
    section("Description", md(t.description))
    section("Values", deflist(t.constants.map(c => ([#anchor(c.anchor)#raw(c.name)], raw(c.value)))))
  }
}

// --- metrics ----------------------------------------------------------------

#let needs(m) = if m.requires_benchmark { "benchmark" } else if m.requires_factors { "factor returns" } else { "returns only" }

#let metric-topic(m, citations, decisions) = {
  topic-header(3, m.name, none, m.anchor)
  block(above: 0.2em, below: 0.8em, text(size: 8.8pt, fill: muted)[
    #raw(m.id) #sym.dot.c #m.category_title #sym.dot.c #m.nature.replace("_", "-") #sym.dot.c
    unit #raw(m.unit) #sym.dot.c formula #raw(m.formula_id)
  ])
  section("Description", md(m.measures))
  section("Formula", {
    mitex(m.formula_latex)
    text(size: 9pt)[Plain text: #raw(m.formula). Symbols: see #link(<doc-notation>)[Notation].]
  })
  section("Usage", code("report.metrics[\"" + m.id + "\"]"))
  section("At a glance", table(
    columns: (auto, 1fr, auto, 1fr),
    [Direction], [#m.direction_text], [Annualized], [#yes-no(m.annualized)],
    [Needs], [#needs(m)], [Supplementary], [#yes-no(m.supplementary)],
    [Nature], [#m.nature.replace("_", "-")], [Minimum-data policy], raw(m.min_data_policy.key),
    [Canonical parameters], table.cell(colspan: 3, if m.canonical_parameters.len() == 0 { [—] } else { m.canonical_parameters.join(", ") }),
  ))
  section("Inputs", md(m.inputs))
  section("Value", md(m.unit_text + " " + m.direction_text + "."))
  section("Interpretation", {
    block(below: 0.7em)[_Plain language._ #md(m.retail)]
    block[_Professional._ #md(m.institutional)]
  })
  section("Assumptions", bullets(m.assumptions))
  section("When it can mislead", bullets(m.misleading_when))
  section("Minimum data", md(m.minimum_data + " (policy `" + m.min_data_policy.key + "`: " + m.min_data_policy.description + ")"))
  section("Calculation criteria", md(m.criteria, h1: 2))
  section("OpenFactsheet convention", md(m.convention))
  section("Reference implementations", if m.reference_implementations.len() == 0 {
    [No established library implementation was identified.]
  } else {
    table(
      columns: (auto, auto, auto, 1fr),
      table.header([*Library*], [*Function*], [*Agrees*], [*Note*]),
      ..m.reference_implementations.map(r => (
        r.library, raw(r.function), if r.agrees { "yes" } else { "no (documented difference)" }, md(r.note),
      )).flatten(),
    )
  })
  section("References", list(..m.references.map(r => {
    let entry = citations.at(r.citation)
    [#r.citation #if r.url != none [#link(r.url)[#r.url]] #h(0.3em) #link(label(entry.anchor))[\[bibliography\]]]
  })))
  let see = m.decisions.map(n => link(label("decision-" + n))[Decision #n: #decisions.at(n)])
  see.push(link(<doc-criteria>)[Decision criteria])
  section("See also", see.join([; ]))
}

#let metrics-part(data, citations, decisions) = {
  for c in data.categories {
    [#heading(level: 2, c.title) #label("category-" + c.id)]
    let ms = data.metrics.filter(m => m.category == c.id)
    for m in ms { metric-topic(m, citations, decisions) }
  }
}

// --- documents --------------------------------------------------------------

#let document-topic(d) = {
  let title = if "number" in d { "Decision " + d.number + ": " + d.title } else { d.title }
  topic-header(2, title, none, d.anchor)
  md(read("/md/" + d.anchor + ".md"), prefix: d.anchor + "-", h1: 2)
}

// --- bibliography -----------------------------------------------------------

#let bibliography-part(bib, metric-names) = {
  set par(justify: false)
  for e in bib.entries [
    #block(above: 0.9em, breakable: false)[
      #anchor(e.anchor)#text(weight: "bold", raw(e.key)) \
      #e.citation #if e.url != none [#link(e.url)[#e.url]] \
      #text(size: 8.8pt, fill: muted)[Cited by: #e.cited_by.map(id => link(label("metric-" + id))[#metric-names.at(id)]).join(", ")]
    ]
  ]
}

// --- index ------------------------------------------------------------------

#let index-part(entries) = {
  let sorted = entries.sorted(key: e => lower(e.key))
  set text(size: 9pt)
  set par(justify: false)
  columns(2, gutter: 1.5em, {
    let letter = ""
    for e in sorted {
      let first = upper(e.key.first())
      if first != letter {
        letter = first
        block(above: 1em, below: 0.4em, text(weight: "bold", fill: accent, letter))
      }
      block(above: 0.3em, below: 0.3em, context grid(
        columns: (1fr, auto),
        column-gutter: 0.3em,
        [#link(label(e.anchor), e.text) #box(width: 1fr, repeat(gap: 0.15em)[.])],
        align(bottom, str(locate(label(e.anchor)).page())),
      ))
    }
  })
}
