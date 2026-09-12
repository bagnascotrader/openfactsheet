// Page style and shared helpers of the OpenFactsheet reference manual.
#import "@preview/mitex:0.2.7": mitex
#import "@preview/cmarker:0.1.10"

#let accent = rgb("#1f4e79")
#let muted = luma(90)
#let rule-color = luma(160)

// Markdown (CommonMark + GitHub tables) with LaTeX math through MiTeX.
// Raw Typst in Markdown is disabled: documents are data, not code.
#let md(text, prefix: none, h1: 2) = {
  set heading(outlined: false)
  show raw.where(lang: "math", block: true): it => mitex(it.text)
  cmarker.render(
    text,
    math: mitex,
    raw-typst: false,
    h1-level: h1,
    set-document-title: false,
    label-prefix: if prefix == none { "" } else { prefix },
    prefix-label-uses: false,
    heading-labels: if prefix == none { none } else { "github" },
  )
}

// A link target (PDF named destination) at this position. Typst writes named
// destinations only for headings, so an anchor is an empty heading that the
// show rule in `setup` hides (it stays out of the outline and bookmarks).
#let anchor-marker = [ofs-anchor]
#let anchor(name) = [#heading(
    level: 6,
    outlined: false,
    bookmarked: false,
    numbering: none,
    supplement: anchor-marker,
  )[]#label(name)]

// A CRAN-style section inside a topic ("Description", "Usage", ...).
#let section(title, body) = block(breakable: true, above: 1.1em, below: 0.6em)[
  #block(below: 0.45em, sticky: true, text(weight: "bold", size: 10.5pt, fill: accent, title))
  #pad(left: 1.2em, body)
]

#let code(text) = block(
  width: 100%,
  fill: luma(245),
  inset: (x: 0.6em, y: 0.5em),
  radius: 2pt,
  raw(text, lang: "python", block: true),
)

// Two-column "term  definition" table (arguments, fields, DESCRIPTION fields).
#let deflist(rows, term-width: 9em) = {
  set par(justify: false)
  grid(
    columns: (term-width, 1fr),
    column-gutter: 1em,
    row-gutter: 0.65em,
    ..rows.map(((term, body)) => (term, body)).flatten(),
  )
}

// Topic header: name on the left, title on the right, a rule below (as in CRAN manuals).
#let topic-header(level, name, title, anchor, mono: false) = [
  #heading(level: level, if mono { raw(name) } else { name }) #label(anchor)
  #if title != none and title != "" {
    block(above: 0.2em, below: 0.8em, text(style: "italic", fill: muted, title))
  }
]

// The text of simple content (strings, raw, sequences), for running headers.
#let plain(c) = {
  if type(c) == str { c } else if c.has("text") {
    if type(c.text) == str { c.text } else { plain(c.text) }
  } else if c.has("children") { c.children.map(plain).join() } else if c.has("body") {
    plain(c.body)
  } else if c == [ ] { " " } else { "" }
}

#let setup(doc, package: none, date: none) = {
  set document(
    title: "OpenFactsheet reference manual",
    author: package.authors,
    keywords: ("investment performance", "methodology", "reference manual"),
    date: auto, // the fixed build timestamp, so the PDF is reproducible
  )
  set page(
    paper: "a4",
    margin: (x: 2.3cm, top: 2.6cm, bottom: 2.4cm),
    header: context {
      if counter(page).get().first() > 1 {
        let here-page = here().page()
        let on-page = query(heading.where(outlined: true)).filter(h => h.location().page() == here-page)
        let before = query(selector(heading.where(outlined: true)).before(here()))
        let current = if on-page.len() > 0 { on-page.first() } else if before.len() > 0 { before.last() } else { none }
        set text(size: 8.5pt, fill: muted)
        let title = if current == none { "" } else { plain(current.body) }
        // One line at most: long topic titles are shortened, not wrapped.
        if title.clusters().len() > 60 { title = title.clusters().slice(0, 57).join() + "…" }
        grid(
          columns: (auto, 1fr),
          column-gutter: 2em,
          [OpenFactsheet reference manual #sym.dot.c version #package.version],
          align(right, title),
        )
        v(-0.5em)
        line(length: 100%, stroke: 0.4pt + rule-color)
      }
    },
    footer: context {
      if counter(page).get().first() > 1 {
        set text(size: 8.5pt, fill: muted)
        align(center, counter(page).display())
      }
    },
  )
  set text(font: "Libertinus Serif", size: 10pt, lang: "en")
  set par(justify: true, leading: 0.62em, spacing: 0.9em)
  show raw: set text(font: "DejaVu Sans Mono", size: 0.84em)
  show math.equation: set text(font: "New Computer Modern Math")
  show link: set text(fill: accent)
  set table(stroke: 0.4pt + rule-color, inset: 0.45em)
  show table: set text(size: 8.8pt)
  show table: set par(justify: false)
  // Long identifiers in narrow table columns may break after an underscore.
  show table: it => {
    // The replacement is text in the raw style (a new raw would be styled twice).
    show raw.where(block: false): r => if r.text.len() > 16 and "_" in r.text {
      text(font: "DejaVu Sans Mono", r.text.replace("_", "_\u{200B}"))
    } else { r }
    it
  }
  set list(indent: 0.6em)
  set enum(indent: 0.6em)

  // Parts: a new page, a large title.
  show heading.where(level: 1): it => {
    pagebreak(weak: true)
    block(below: 1.4em, above: 0pt)[
      #text(size: 20pt, weight: "bold", fill: accent, it.body)
      #v(-0.4em)
      #line(length: 100%, stroke: 1pt + accent)
    ]
  }
  // Topics (and metric categories): a rule above, bold name.
  show heading.where(level: 2, outlined: true): it => block(above: 2.2em, below: 0.35em, sticky: true)[
    #line(length: 100%, stroke: 0.6pt + rule-color)
    #v(-0.25em)
    #text(size: 13.5pt, weight: "bold", it.body)
  ]
  show heading.where(level: 3, outlined: true): it => block(above: 2em, below: 0.35em, sticky: true)[
    #line(length: 100%, stroke: 0.5pt + rule-color)
    #v(-0.25em)
    #text(size: 12pt, weight: "bold", it.body)
  ]
  // Headings inside documents; anchors are invisible.
  show heading.where(outlined: false): it => if it.supplement == anchor-marker { [] } else {
    block(above: 1.3em, below: 0.6em, sticky: true, text(
      size: if it.level <= 3 { 11pt } else { 10pt },
      weight: "bold",
      style: if it.level >= 5 { "italic" } else { "normal" },
      it.body,
    ))
  }
  doc
}
