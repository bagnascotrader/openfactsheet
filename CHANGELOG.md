# Changelog

All notable changes are recorded here. OpenFactsheet versions the **package**
and the **methodology** separately: a methodology version change means reported
numbers, statuses or conventions changed.

## [0.1.0] — unreleased

Package 0.1.0 · Methodology 0.1.0

### Added
- Canonical pipeline: input → normalization → data-quality diagnostics →
  metrics → applicability/confidence policy → interpretation → reports.
- Inputs: lists, tuples, NumPy arrays, pandas Series/DataFrames, CSV, Excel
  (optional extra), wide monthly-return tables, pasted table text.
- Deterministic percent/decimal classifier; calendar-based frequency inference.
- 48 canonical metrics (returns, volatility, drawdowns, risk-adjusted, tail,
  distribution, consistency, serial dependence, benchmark-relative) with full
  registry documentation and generated per-metric pages.
- Data-quality diagnostics: missing values/periods, stale and repeated returns,
  outliers, impossible returns, serial correlation, smoothing risk.
- Reports: terminal, Markdown, HTML, deterministic JSON; `ofs.compare()` with
  common-period analysis and no ranking.
- Tests: unit, property-based, golden reports, CLAUDE.md acceptance tests 1–3,
  cross-library validation against PerformanceAnalytics, empyrical, QuantStats.

### Methodology 0.1.0
- Initial canonical conventions; see `docs/methodology/decisions/0001`–`0015`.
