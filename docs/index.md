# OpenFactsheet documentation

OpenFactsheet answers one question: *what does this investment's performance
actually look like under one transparent, standardized methodology?*

## Start here

- [Getting started](getting_started.md) — install, analyze, read a report.
- [Methodology](methodology.md) — the pipeline, the policy layer and the
  anti-cherry-picking rules.
- [Assumptions](assumptions.md) — every canonical convention of methodology
  0.1.0, with links to the reasoning.

## Reference

Exact, auditable specification of everything OpenFactsheet computes and decides:

- [Exact formulas](reference/formulas.md) — the precise mathematical definition
  of every metric, as implemented (generated from the registry).
- [Notation](reference/notation.md) — symbols, wealth/drawdown and quantile
  definitions used by all formulas.
- [Decision criteria](reference/criteria.md) — every rule, in evaluation order:
  input parsing, validation, missing data, frequency inference, percent/decimal
  detection, data-quality findings, applicability, confidence and status,
  benchmark alignment, comparison, interpretation, report structure,
  determinism.
- [Policies, thresholds and constants](reference/policies.md) — every numeric
  threshold and canonical constant, read directly from the code (generated).
- [JSON report schema](reference/report_schema.md) — every field of the report.
- [Metric catalog](metric_catalog.md) — all canonical metrics (generated from
  the registry). Each metric links to a page in [`interpretation/`](interpretation/)
  answering the twelve documentation questions: what it measures, formula,
  inputs, direction, plain and professional interpretation, assumptions, when it
  misleads, minimum data, reference implementations, sources and the
  OpenFactsheet convention — followed by its calculation criteria: when a value
  is produced, exactly when it is undefined, the confidence rules that apply to
  it, and the assumptions recorded on every result.
- [Methodology decisions](methodology/decisions/README.md) — one note per
  convention where definitions vary.
- [Reference implementations & validation](validation/reference_implementations.md)
  — how results are cross-checked against PerformanceAnalytics, empyrical and
  QuantStats, and every known convention difference.
- [Reference manual (PDF)](manual/openfactsheet-manual.pdf) — all of the above as
  one CRAN-style PDF, generated from the code, with a link target for every
  metric, function and decision ([how it is built](manual/README.md)). Every
  result in every report links to the topic that defines it
  ([decision 0035](methodology/decisions/0035-linking-results-to-the-manual.md)).

## Principles in one paragraph

Compute broadly and never hide an unfavorable metric; never tune periods,
thresholds or confidence levels per fund; make every assumption deterministic,
versioned and visible; never return an unexplained NaN; separate calculation
from applicability, confidence and presentation; and distinguish what was
observed from what is estimated or model-dependent. OpenFactsheet explains
measurements — it does not give investment advice.
