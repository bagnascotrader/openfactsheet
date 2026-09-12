# 0033 — Share classes, table roles and benchmark returns in documents

**Status:** Accepted — methodology 0.1.0

## Problem

Factsheets often list several share classes (currencies, fee levels,
distribution policies) but show one monthly-return table, and they frequently
print the benchmark's returns next to the fund's: as a second table, or as a
second row per year ("2023 Fund …", "Benchmark …"), sometimes with a third
"Relative" row. Reading the wrong row as the fund, attributing the table to the
wrong class, or silently using the printed benchmark would all misstate the
analysis. CLAUDE.md §23 forbids fabricating or inferring a benchmark.

## Known definitions

None are standard; layouts vary by issuer. The evidence a reader uses:

- the table's caption or footnote ("Performance of the A EUR Acc class", an ISIN
  in the footnote);
- the performance section heading;
- the number of classes;
- the currency the returns are stated in.

## PerformanceAnalytics behavior

Not applicable.

## QuantStats behavior

Not applicable.

## Empyrical behavior

Not applicable.

## Academic sources

None; this is a data-provenance decision.

## OpenFactsheet decision

- **Series-labelled rows.** A table row may carry a label left of the January
  column. A labelled line without a year continues the previous year. Each
  distinct label becomes its own series, validated separately (positions, YTD
  reconciliation).
- **Roles.** Each series is `fund`, `benchmark`, `relative` or `unknown`:
  - A row label decides first: relative/difference words → relative; benchmark or
    index-provider words → benchmark (unless it also says fund); fund, class or
    portfolio words → fund; anything else → unknown.
  - The unlabelled series of a labelled table is the fund.
  - A single-series table is a benchmark only when its caption says so without
    naming the fund.
  - The role and its evidence are recorded in `provenance.extraction`.
- **Relative series** are not return series and are ignored, with a note.
- **Benchmark series are never used automatically:**
  - `ofs.load()` returns them as "`<label>` (benchmark, from document)" in a
    `ReturnTable`.
  - `ofs.analyze(document)` uses the single fund series and states that the
    benchmark returns were not used; benchmark-relative metrics need
    `benchmark=...` passed explicitly.
  - A benchmark series that cannot be read reliably is left out with a note, never
    refusing the fund.
  - A document whose only table is a benchmark is not analyzed as the fund.
  - Several fund tables (e.g. one per class) are left for the caller to choose.
- **Share classes** are detected from a class table (a header with a class word
  and "ISIN", then rows up to the first row without an ISIN) or from a line naming
  a class next to an ISIN (same or next line). Each class records its label,
  ISINs, currency and evidence.
- **Attribution rules**, in fixed order:
  1. the caption or footnote mentions exactly one class (label or ISIN);
  2. the performance heading above the table mentions exactly one class;
  3. the document has exactly one class;
  4. the caption states exactly one currency and exactly one class has it.

  The first deciding rule wins. Rules deciding differently, or no deciding rule
  with several classes, give `ambiguous` with the candidates. There is no fallback
  such as "the first class listed". Attribution describes the report and never
  changes a metric.

## Rationale

Every rule uses evidence printed in the document, and the result carries that
evidence, so a reader can check it. Refusing to guess keeps the report honest
when a factsheet leaves the class unclear. Treating printed benchmark returns as
data the user may choose to supply, rather than an automatic input, preserves the
explicit-benchmark rule while still making them available.

## Consequences

- Row labels outside the vocabularies are `unknown`; such series are returned by
  `ofs.load()` but `analyze()` then asks the caller to choose.
- The planned `share_class=` declaration was not added: ambiguity never affects
  the metrics, and the candidates are shown. It can be added later if needed.
- Class tables whose rows lack ISINs (identifiers only in other columns or pages)
  are not detected as classes.
