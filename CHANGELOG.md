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

### Added — Phase 2, first increment (16 metrics; 64 in total)
- Risk-adjusted: Kappa 3, upside potential ratio, Burke, Sterling, Pain ratio.
- Returns / dispersion: payoff ratio, semi-deviation, downside potential (LPM 1),
  mean absolute deviation.
- Tail (supplementary, model-dependent): Gaussian and Cornish-Fisher VaR.
- Distribution (supplementary): Jarque-Bera p-value.
- New **Statistical confidence** category, rendered in report section 12:
  Probabilistic Sharpe Ratio, Sharpe standard error with 95% interval, Minimum
  Track Record Length, standard error of the mean with t-interval and t-test.
- Two interpretation rules state whether the Sharpe ratio is statistically
  distinguishable from zero and whether the track record is long enough.
- Every new metric cross-validated against PerformanceAnalytics, R `t.test`,
  SciPy or QuantStats; decision notes 0016–0020.

### Documentation
- Complete specification under `docs/reference/`: exact LaTeX formulas for every
  metric (stored in the registry), notation, every decision criterion in
  evaluation order, all thresholds and constants (generated from the code), and
  the JSON report schema. Metric pages include calculation criteria
  (applicability, undefined conditions, confidence rules, recorded assumptions).
- Tests fail if a metric lacks an exact formula, if a runtime "undefined"
  condition is undocumented, or if a diagnostic finding or interpretation rule
  is missing from the criteria reference.

### Changed (pre-release)
- `InputDiagnostics.duplicate_dates` renamed `duplicate_periods` (it counts
  observations sharing a calendar period).
- A declared frequency is accepted for a single dated observation.
- Numeric (integer or float) indexes are treated as positions, never dates.
- `max_drawdown` warns when the deepest drawdown has not recovered.
- Benchmark-coverage and short-annualization confidence thresholds moved into
  the canonical methodology (`confidence.*`); values unchanged.

### Methodology 0.1.0
- Initial canonical conventions; see `docs/methodology/decisions/0001`–`0015`.
