# Canonical methodology

OpenFactsheet produces one standardized report for any return history. The
report is determined by a versioned methodology, not by the person supplying
the data. This page describes how that methodology is organized. The specific
conventions are listed in [assumptions.md](assumptions.md) and justified in the
[decision notes](methodology/decisions/README.md).

Current version: **OpenFactsheet Methodology 0.1.0** (`ofs.METHODOLOGY_VERSION`).

## Pipeline

```text
INPUT → NORMALIZATION → DATA QUALITY & FREQUENCY → METRIC CALCULATION
      → APPLICABILITY / CONFIDENCE POLICY → INTERPRETATION → REPORTING
```

| Stage | Module | What it does |
|---|---|---|
| Input | `openfactsheet.input` | Parses lists, arrays, pandas objects, CSV, Excel, pasted text and wide monthly tables into raw values and dates. Never mutates caller data. |
| Normalization | `openfactsheet.normalization` | Rejects infinite values and duplicate timestamps, sorts dates, trims and drops (never fills) missing values, infers frequency, detects percent vs decimal scale. Produces a `ReturnSeries` and `InputDiagnostics`. |
| Data quality | `openfactsheet.diagnostics` | Missing periods, stale and repeated returns, impossible and extreme returns, short history, serial correlation, smoothing risk. Produces a `DataQualityReport` before any metric is computed. |
| Calculation | `openfactsheet.metrics` | One registry of metric functions. Functions only calculate; they raise `UndefinedMetric` when a value is mathematically undefined. Shared quantities (wealth index, drawdown path, episodes, moments, aligned benchmark) are cached once per report. |
| Policy | `openfactsheet.policy` | Decides applicability, status and confidence, and attaches assumptions and warnings. |
| Interpretation | `openfactsheet.interpretation` | Plain-language and professional explanations plus context notes (for example, a smoothing caveat on the Sharpe ratio). Never grades or advises. |
| Reporting | `openfactsheet.report` | Builds the `FactsheetReport` and renders it as JSON, terminal text, Markdown or HTML. Calculations know nothing about rendering. |

## Compute everything

The metric engine evaluates every registered metric for every report. There is
no public way to select a subset. Each metric produces a structured
`MetricResult`; none is omitted because its value is unattractive.

## Policy layer: applicability, confidence, status

Three separate questions are answered for each metric:

1. **Applicability** (before calculation, `policy/applicability.py`): can the
   metric be computed at all?
   - benchmark required but none supplied → `not_applicable`;
   - annualized metric without a regular frequency → `not_applicable`;
   - wealth-path metric with returns below -100% → `not_applicable`;
   - fewer observations than the mathematical minimum → `insufficient_data`.
2. **Calculation outcome**: a value that is mathematically undefined (for
   example zero volatility in a ratio denominator) → `not_applicable` with the
   reason; an unexpected failure or non-finite result → `error` with the reason
   (the value is withheld).
3. **Confidence** (after calculation, `policy/confidence.py`): how reliable is
   the estimate? Labels are `high`, `moderate`, `low` and `not_assessable` (no
   value). They come from the metric's minimum-data policy (observations, years,
   or expected tail observations) and are then capped by data quality: smoothing
   risk, stale returns, missing periods, less than one year of data for an
   annualized metric, and limited benchmark overlap
   ([0015](methodology/decisions/0015-minimum-data-policy.md),
   [0014](methodology/decisions/0014-smoothing-risk.md)).

The resulting **status** is one of:

| Status | Value shown | Meaning |
|---|---|---|
| `applicable` | yes | Computed; confidence `high` or `moderate`. |
| `low_confidence` | yes | Computed; the estimate is unreliable for the stated reasons. |
| `supplementary` | yes | Diagnostic or model-dependent statistic shown for context. |
| `not_applicable` | no | Cannot be meaningfully computed for this input; reason given. |
| `insufficient_data` | no | Below the mathematical minimum; reason given. |
| `error` | no | Unexpected failure; reason given. |

Low confidence never hides a value. Confidence describes the reliability of an
estimate, never the quality of the investment.

## Observed, derived, estimated, model-dependent

Every metric definition carries a `nature` tag, shown in the output:

| Nature | Meaning | Examples |
|---|---|---|
| observed | A fact about the supplied path. | cumulative return, best/worst period, maximum drawdown, time under water, streaks |
| derived | A deterministic transformation of observed quantities. | CAGR, Calmar, Martin, Omega, gain-to-pain, capture ratios |
| estimated | A sample estimate of a population quantity, subject to sampling error. | mean, volatility, Sharpe, Sortino, VaR, ES, skewness, autocorrelation, beta |
| model_dependent | Depends on an explicit statistical or economic model. | CAPM alpha, Treynor ratio, Ljung-Box p-value |

## Assumptions are explicit, not absent

Parameter-less does not mean assumption-less. Every assumption that affects a
metric is recorded on that metric's `assumptions` field (annualization factor
and its source, 0% risk-free rate, 0% target return, 95% confidence level,
sample standard deviation, drawdown starting point, benchmark alignment,
regression model). The full methodology object is embedded in every report and
returned by `ofs.methodology()`.

## Versioning

- The methodology version is independent of the package version.
- Any change to a canonical value, status, confidence rule, threshold or
  convention increments `METHODOLOGY_VERSION`, adds a CHANGELOG entry and a
  decision note, and requires conscious regeneration of the golden reports.
- The meaning of a metric is never changed silently: its `formula_id`
  (for example `sharpe_ratio@v1`) changes when its formula changes.
- Future research APIs may allow overrides; results produced with overrides must
  be labeled non-canonical (`provenance.canonical = false`).

## Anti-cherry-picking rules

Implemented from CLAUDE.md section 43:

- Negative periods, maximum drawdown, and downside, path and tail statistics are
  always part of the report when the data allow them.
- The full supplied history is used; no start date, window, target, confidence
  level, benchmark or risk-free rate is chosen per fund.
- Track-record length, frequency and annualization are always disclosed.
- Benchmark overlap (aligned observations and dropped periods) is always
  disclosed; benchmarks are never inferred.
- Material data-quality findings appear in the diagnostics section and on the
  affected metrics.
- Renderers have no flags to remove canonical sections; unavailable sections are
  shown with the reason (for example "no benchmark supplied").
- `ofs.compare()` applies the identical methodology to every investment, adds a
  common-period analysis when histories differ, and does not rank.
- There is no composite score.

## Provenance

Each report records the package version, methodology version, input type,
a SHA-256 fingerprint of the analyzed returns (and benchmark), the date range,
frequency, annualization statement, number of observations and every
transformation applied (sorting, trimming, percent conversion, table reshaping).
The JSON output contains no timestamps, so identical inputs produce identical
JSON.

## Related documents

- [Assumptions for methodology 0.1.0](assumptions.md)
- [Methodology decision notes](methodology/decisions/README.md)
- [Reference implementations and validation](validation/reference_implementations.md)
- Full specification: [exact formulas](reference/formulas.md),
  [notation](reference/notation.md), [decision criteria](reference/criteria.md),
  [policies and thresholds](reference/policies.md),
  [JSON report schema](reference/report_schema.md)
