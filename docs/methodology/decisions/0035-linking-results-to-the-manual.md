# 0035 — Linking a result to its documentation

**Status:** Accepted — methodology 0.1.0 (presentation and metadata only; no reported number changes)

## Problem

Decision 0034 built the reference manual and gave every topic a stable named
destination, precisely so that "a result can link to exactly the page that
documents it". Nothing used them: a report said what a number was called and
what it was worth, and left the reader to find the definition. A factsheet that
travels — pasted into an email, committed as JSON, opened months later — then
arrives without its methodology, which is the opposite of what OpenFactsheet
exists for (CLAUDE.md sections 1.4 and 43).

Two things have to be decided: **what** a result links to, and **which version**
of it.

## Known definitions

- **CRAN / R help**: `?SharpeRatio` opens the topic of the installed version.
  The documentation is bound to the version in use, not to a web page.
- **Sphinx / `__doc__` links**: HTML docs point at "latest" or "stable"; a
  result printed by an older version links to documentation that no longer
  describes it.
- **DOIs and permalinks**: a reference is pinned to an immutable version.

## PerformanceAnalytics behavior

Prints numbers; the manual is consulted separately. Charts and tables carry no
links.

## QuantStats behavior

Tear sheets carry no links to documentation.

## Empyrical behavior

Returns bare floats.

## Academic sources

None; this is a documentation and provenance decision.

## OpenFactsheet decision

- **Every result carries a link to the topic that defines it.**
  `MetricResult.documentation` is the URL of its manual topic
  (`…/openfactsheet-manual.pdf#nameddest=metric-sharpe_ratio`), and it is part
  of the JSON of every metric. A metric that could *not* be computed links to
  its definition too: the reason is only understandable next to it.
- **The report carries the links of its own version.**
  `FactsheetReport.documentation` is a `DocumentationLinks` object (the manual,
  the metric catalog, the documentation tree, and a topic by metric, category,
  API name, decision, document or bibliography key), and the JSON has a
  `documentation` block with the manual, the tag, the source ref and whether the
  version is released.
- **Links are pinned to the version that produced the result**, never to
  "latest". A released version links to its own release assets and to its
  sources at `v<version>`; before release there is no such tag, so results link
  to the rolling `manual-latest` pre-release built from `main` and say so in
  words. The two constants that express this (`MANUAL_TAG`, `SOURCE_REF`) are
  checked against `CHANGELOG.md` by the test suite, so a release cannot ship
  links to a manual that was never published for it.
- **Anchors have one source.** `openfactsheet.manual` builds every named
  destination (`metric_anchor`, `category_anchor`, `api_anchor`,
  `decision_anchor`, `document_anchor`, `reference_anchor`); no renderer, export
  or test spells one out.
- **Every renderer links what it can.** The HTML and Markdown reports link each
  metric name, including the names listed in sections whose metrics are not
  applicable (no benchmark supplied, no factors supplied) — all 97 in both.
  Plain text cannot carry a link per row, so the terminal report gives the
  manual of its version and the destination pattern, on one unwrapped line so
  that it stays copyable.
- **A link may not point at a topic that does not exist.** The test suite
  resolves every metric's and category's destination against the named
  destinations the committed manual data declares, and decision 0034's build
  already fails on a missing destination.

## Rationale

The manual is the deliverable that explains the numbers; a result that does not
reach it leaves the explanation optional. Pinning the link to the version that
computed the number is what makes it an audit trail rather than a convenience:
conventions change between methodology versions, and a reader checking an old
report must see the definition that was actually used. Keeping the link
derivable from a metric's id (one anchor function, no table of URLs) means the
links cannot drift from the registry as metrics are added.

## Consequences

- The JSON report gains a `documentation` block and one `documentation` key per
  metric; the schema document and the golden reports record it. Schema version
  0.1 is unchanged: the keys are additions.
- Reports are no longer self-contained with respect to the manual: the link is
  only resolvable online. The number, its status, its warnings and the
  assumptions it used remain in the report itself, as before.
- Bundling the manual with the package, so that a result can be read next to its
  documentation offline, remains follow-up work.
