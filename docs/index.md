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

- [Metric catalog](metric_catalog.md) — all canonical metrics (generated from
  the registry). Each metric links to a page in [`interpretation/`](interpretation/)
  answering the twelve documentation questions: what it measures, formula,
  inputs, direction, plain and professional interpretation, assumptions, when it
  misleads, minimum data, reference implementations, sources and the
  OpenFactsheet convention.
- [Methodology decisions](methodology/decisions/README.md) — one note per
  convention where definitions vary.
- [Reference implementations & validation](validation/reference_implementations.md)
  — how results are cross-checked against PerformanceAnalytics, empyrical and
  QuantStats, and every known convention difference.

## Principles in one paragraph

Compute broadly and never hide an unfavorable metric; never tune periods,
thresholds or confidence levels per fund; make every assumption deterministic,
versioned and visible; never return an unexplained NaN; separate calculation
from applicability, confidence and presentation; and distinguish what was
observed from what is estimated or model-dependent. OpenFactsheet explains
measurements — it does not give investment advice.
