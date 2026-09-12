# 0034 — The reference manual

**Status:** Accepted — methodology 0.1.0 (documentation only; no reported number changes)

## Problem

A reader of an OpenFactsheet result needs to know what every number means, how it
was computed, what it assumes, when it misleads and where the definition comes
from. The Markdown pages answer this, but they are many files, change with the
`main` branch, and cannot be cited or archived as the documentation of the exact
version that produced a result. R packages solve this with the reference manual
CRAN builds for every release: one PDF, one topic per function, a fixed layout.
Few Python packages offer an equivalent.

## Known definitions

- **CRAN reference manual**: generated from the package's Rd files; a title page
  with the DESCRIPTION fields, a table of contents, one topic per documented
  object (Description, Usage, Arguments, Details, Value, References, See Also,
  Examples) and an index.
- **Sphinx PDF output**: generated from reStructuredText through LaTeX; needs a
  TeX installation and is not reproducible byte for byte.

## PerformanceAnalytics behavior

Ships the standard CRAN reference manual (one topic per function, with the
formulas and the papers they come from).

## QuantStats behavior

No reference manual; the documentation is the README and docstrings.

## Empyrical behavior

No reference manual; docstrings only.

## Academic sources

None; this is a documentation decision.

## OpenFactsheet decision

- **One PDF per version**, generated from the code, never edited by hand. It is
  laid out like a CRAN manual:
  - a title page with the package description;
  - contents;
  - **Overview and usage**;
  - **Functions and classes**: one topic per name in `openfactsheet.__all__` (plus
    `Comparison`), taken from signatures and Google-style docstrings;
  - **Metrics**: one topic per registered metric, grouped by report section. Each
    topic has the formula, usage, direction, whether it is annualized, inputs,
    interpretation, assumptions, when it misleads, minimum data, the exact
    calculation and confidence criteria, reference implementations, references
    and the decisions that discuss it;
  - **Methodology**: the methodology, assumptions, criteria, notation, policies
    and JSON schema documents;
  - **Methodology decisions**: every decision note;
  - **Validation**;
  - a bibliography with the metrics citing each source;
  - an index.
- **Single source.** Each metric's documentation is one record
  (`metrics/catalog_docs.metric_record`) from which both its Markdown page and its
  manual topic are rendered. The hand-written documents are included as they are;
  links between them become links between manual topics. The data the manual is
  built from is committed in `docs/manual/data/`, and
  `scripts/generate_docs.py --check` fails when it is stale.
- **Toolchain: Typst** from PyPI (`pip install openfactsheet[docs]`). It needs no
  TeX installation, no network and no system fonts:
  - The two Typst packages used are vendored in `docs/manual/packages`: MiTeX
    (Apache-2.0) turns the registry's LaTeX formulas into Typst math, and cmarker
    (MIT) renders the Markdown.
  - Fonts are the ones embedded in Typst.
  - The timestamp is the last commit's (or `SOURCE_DATE_EPOCH`), so the same
    sources give the same bytes.
  - The PDF conforms to PDF/A-2b for archiving.
- **Nothing is skipped.** A formula MiTeX cannot translate, an internal link to a
  missing topic, or a missing named destination fails the build and CI; the build
  never falls back to plain text.
- **Stable link targets.** Every topic is a PDF named destination:
  - `metric-<id>` for metrics;
  - `api-<name>` for functions and classes;
  - `decision-<nnnn>` for decisions;
  - `doc-<name>` for documents;
  - `ref-<key>` for sources;
  - `category-<id>` for metric groups.

  `…/openfactsheet-manual.pdf#nameddest=metric-sharpe_ratio` opens a metric's
  topic.
- **The PDF itself is not committed.** CI builds it on every change and keeps it
  as a build artifact.

## Rationale

A manual built from the same records as the code cannot drift from it, and one
versioned PDF can be cited, archived and linked to from a result. Typst gives a
reproducible, dependency-light build that runs anywhere Python runs. Failing on
anything that does not compile keeps the manual complete instead of silently
degraded.

## Consequences

- **Docstrings are now user documentation.** A test requires every argument of
  every public function and method to be documented.
- **Formulas must be written in the LaTeX subset MiTeX supports.** One formula
  (`factor_alpha_t_statistic`) changed `\big\lfloor` to `\left\lfloor`; the
  rendered formula is the same.
- The manual documents the version it was built from. Linking results to the
  manual of their own version, bundling it with the package and publishing it
  per version are follow-up work.
