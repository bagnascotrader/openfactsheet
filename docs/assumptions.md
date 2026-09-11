# Canonical assumptions — methodology 0.1.0

This page answers each methodological question listed in CLAUDE.md section 41
for methodology **0.1.0**. The machine-readable source of truth is
`src/openfactsheet/policy/defaults.py` (`ofs.methodology()` returns it, and
every report embeds it). Rationale and library comparisons are in the
[decision notes](methodology/decisions/README.md).

Items marked **Deferred** have no canonical answer yet; the report's behavior
in those cases is described so that nothing is hidden.

| Question | Methodology 0.1.0 answer | Decision |
|---|---|---|
| Arithmetic vs geometric annual return | Headline annualized return is geometric (CAGR by observation count). The arithmetic `P x mean` is reported separately as `annualized_arithmetic_mean`. | [0004](methodology/decisions/0004-annual-return.md) |
| Sample vs population standard deviation | Sample (n − 1) everywhere. | [0003](methodology/decisions/0003-standard-deviation.md) |
| Annualization under serial correlation | Square-root-of-time scaling is applied as usual; serial correlation is diagnosed and volatility-based metrics are downgraded and warned. No autocorrelation-adjusted annualization (e.g. Lo 2002) yet — **Deferred** until it can be added as a separately labeled statistic. | [0002](methodology/decisions/0002-annualization-and-frequency.md), [0014](methodology/decisions/0014-smoothing-risk.md) |
| Risk-free treatment | 0% per period for every excess-return metric, disclosed on each metric. Currency is never inferred from the locale. | [0005](methodology/decisions/0005-risk-free-rate.md) |
| Sortino MAR / target | 0% per period. | [0006](methodology/decisions/0006-sortino-downside-deviation.md) |
| Omega threshold | 0% per period, simple empirical estimator `sum(max(r, 0)) / sum(max(-r, 0))`, not annualized. | `policy/defaults.py` (`omega`) |
| VaR confidence | 95%, historical, per observation period. | [0010](methodology/decisions/0010-var-es-quantiles.md) |
| ES confidence | 95%, historical: mean of returns at or below the 5% quantile. | [0010](methodology/decisions/0010-var-es-quantiles.md) |
| Exact quantile interpolation | Linear interpolation (Hyndman-Fan type 7; R and NumPy default). | [0010](methodology/decisions/0010-var-es-quantiles.md) |
| Downside deviation denominator | All n observations (full sample). | [0006](methodology/decisions/0006-sortino-downside-deviation.md) |
| Minimum track record | **Deferred.** No minimum-track-record statistic (e.g. Bailey & López de Prado's MinTRL) in 0.1.0 because it depends on a Sharpe inference framework not yet implemented. Short histories are handled by confidence labels: most estimates are `low` below 3 years and `moderate` below 5. | [0015](methodology/decisions/0015-minimum-data-policy.md) |
| Benchmark alignment | Intersection of calendar periods (monthly/quarterly/yearly) or exact dates (daily/weekly); never filled; overlap disclosed; different frequencies raise an error. | [0012](methodology/decisions/0012-benchmark-alignment-and-relative-metrics.md) |
| Missing values | Never replaced by zero or forward-filled. Leading and trailing missing values are trimmed; interior missing values are removed, counted and disclosed, and appear as missing expected periods. Wealth-path and annualized metrics are capped at `moderate` confidence when gaps exist. | [0002](methodology/decisions/0002-annualization-and-frequency.md), [0015](methodology/decisions/0015-minimum-data-policy.md) |
| Monthly table partial years | Empty cells are missing, never zero. Empty cells after the last reported month (future months) are trimmed; empty cells inside the history are interior missing values. Annual total columns (YTD, Year, Total) are ignored for calculation and the omission is recorded as a transformation. | `input/monthly_table.py` |
| Return scale detection | Deterministic classifier: declared scale, `%` labels, then median absolute value against frequency-dependent bounds; ambiguous cases raise `AmbiguousReturnScaleError` instead of guessing. | [0013](methodology/decisions/0013-return-scale-detection.md) |
| -100% return behavior | Valid (total loss). Wealth becomes zero, cumulative return and CAGR are -100%, maximum drawdown is -100%, and a critical finding plus metric warnings are shown. | [0001](methodology/decisions/0001-return-type.md), [0007](methodology/decisions/0007-drawdown-conventions.md) |
| Returns below -100% | Impossible for ordinary simple returns: kept (never clipped), flagged as critical, and every wealth-path metric is `not_applicable`. Moment-based metrics are still computed. | [0001](methodology/decisions/0001-return-type.md) |
| Non-finite return behavior | Infinite values raise `InputError` before any calculation. NaN means a missing observation (see above). No metric result can hold NaN or infinity: undefined values are `not_applicable` with a reason, unexpected failures are `error` with a reason. | [0001](methodology/decisions/0001-return-type.md) |
| Compounding after total loss | Wealth stays at zero; later returns cannot rebuild it and the drawdown never recovers. | [0007](methodology/decisions/0007-drawdown-conventions.md) |
| Irregular time series | Never annualized: annualized metrics are `not_applicable` with a reason. Non-annualized metrics are computed. | [0002](methodology/decisions/0002-annualization-and-frequency.md) |
| Undated values | Frequency is unknown and nothing is annualized unless the caller declares the frequency; a declaration is recorded and warned. | [0002](methodology/decisions/0002-annualization-and-frequency.md) |
| Crypto / non-business-day data | Daily series with weekend observations use 365 periods per year; business-day series use 252. **Deferred:** mixed calendars (e.g. a 365-day fund against a 252-day benchmark, which currently aligns only on common dates), intraday data, and holiday calendars by exchange. | [0002](methodology/decisions/0002-annualization-and-frequency.md) |
| Frequency changes within a series | Detected as irregular when fewer than half of the spacings equal one period; no resampling. **Deferred:** splitting a history into regular segments. | [0002](methodology/decisions/0002-annualization-and-frequency.md) |
| Drawdown starting point | Initial wealth 1 counts as the first peak, so a first-period loss is a drawdown. | [0007](methodology/decisions/0007-drawdown-conventions.md) |
| Skewness / kurtosis estimators | Bias-corrected G1 and excess G2. | [0011](methodology/decisions/0011-skewness-kurtosis.md) |
| Smoothed returns | Diagnosed (lag-1 autocorrelation with significance), warned and downgraded; never unsmoothed. | [0014](methodology/decisions/0014-smoothing-risk.md) |

## What the caller may and may not set

The canonical API has no parameters for windows, thresholds, confidence
levels, target returns, risk-free rates or metric subsets. The only optional
arguments describe the input when the data cannot establish it:

- `return_scale="decimal" | "percent"` — only needed when detection reports ambiguity;
- `frequency=` — the observation frequency of undated values (checked against dates when dates exist);
- `benchmark=` — an explicitly supplied benchmark; none is ever inferred;
- `name=` — a display name.

Declarations are recorded in the input diagnostics and warned on the affected
metrics.
