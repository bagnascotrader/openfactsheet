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

### Added — Phase 4: canonical charts
- The HTML report now contains eight canonical charts rendered as static,
  self-contained SVG (no external resources): growth of 1, calendar-year returns,
  monthly heatmap, rolling one-year volatility, underwater chart, return
  distribution, rolling one-year return and growth over the benchmark overlap.
  Each has a caption and a data table; light and dark themes.
- Presentation rules fixed by the methodology (decision 0026, `charts.*`
  conventions): full history, linear scales, zero baselines for bars, symmetric
  heatmap scale, partial years outlined and labelled, benchmark on the aligned
  overlap only, every return counted in the histogram.
- Drawdown-episode table (the 10 deepest episodes, deepest first) in terminal,
  Markdown and HTML reports.
- `FactsheetReport.charts()` returns the SVG strings keyed by chart id;
  `FactsheetReport.benchmark_returns` keeps the supplied benchmark series.

### Added — Phase 2, third increment (8 metrics; 90 in total)
- Benchmark-relative: capture ratio (upside / downside capture), batting average
  (with up- and down-market components), residual (specific) volatility,
  appraisal ratio, M-squared, bull- and bear-market beta, timing ratio.
- Validated against PerformanceAnalytics (`CAPM.beta.bull` / `.bear`,
  `TimingRatio`, `Modigliani`, `UpDownRatios(method = "Percent")`, R `lm`) and
  empyrical (`up_down_capture`); documented differences from `SpecificRisk` and
  `AppraisalRatio` pinned by tests. Decision note 0027.

### Fixed (pre-release, third increment)
- A constant fund against a varying benchmark produced rounding-noise betas
  (e.g. 1e-17) and therefore absurd Treynor ratios (about -8.6e15). The
  single-index regression is now solved exactly for a constant fund (beta 0,
  zero residuals), so ratios dividing by beta or residual risk are
  `not_applicable` with a reason.
- R-squared for a constant fund was reported with status `error` (NaN); it is now
  `not_applicable` (no variance to explain).

### Added — Phase 2, second increment (18 metrics; 82 in total)
- Drawdown tail: Drawdown-at-Risk, Conditional Drawdown-at-Risk, Entropic
  Drawdown-at-Risk (95%); entropic VaR of returns; modified (Cornish-Fisher)
  Expected Shortfall.
- Episode summaries: median drawdown, average drawdown duration, longest
  peak-to-trough decline, average recovery time; recovery factor.
- Complete-calendar-year statistics (best, worst, share positive; partial years
  excluded and disclosed) and rolling one-year windows over every start date
  (best, worst, share positive).
- Geometric mean return per period; interquartile range.
- Validated against PerformanceAnalytics (episode table, calendar years,
  rolling windows, modified ES, geometric mean), R `IQR`, skfolio 1.0.6
  (DaR/CDaR/EDaR/EVaR; added to the `validation` extra) and QuantStats.

### Changed (pre-release, second increment)
- A metric result of plus or minus infinity (a denominator below floating-point
  resolution) is reported as `not_applicable` with an explanation; NaN remains
  `error`. Found by property-based testing.
- Shape statistics are undefined for numerically constant returns (variance
  below floating-point resolution), instead of returning rounding noise.

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
