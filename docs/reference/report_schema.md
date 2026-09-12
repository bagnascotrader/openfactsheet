# JSON report schema (schema version 0.1)

`report.to_json()` / `report.to_dict()` produce one JSON object per report
([report/json.py](../../src/openfactsheet/report/json.py) `report_to_dict`).
The output is deterministic: keys are sorted, no timestamps are embedded,
floats are written at full precision, and `NaN`/`Infinity` can never appear
(any non-finite float inside nested data is written as `null`).

Complete, always-current examples are the golden reports in
[`tests/golden/`](../../tests/golden/) (e.g.
[`monthly_fund_10y.json`](../../tests/golden/monthly_fund_10y.json)); the test
suite fails if the code and those files disagree.

Conventions used throughout:

- **Returns** are simple decimal returns: `0.01` = +1%.
- **Loss measures are signed**: drawdowns, VaR and Expected Shortfall are
  negative numbers for losses (`-0.27` = -27%). Ulcer and Pain indices are
  non-negative magnitudes.
- **Dates** are `YYYY-MM-DD` strings, or `null` when the input is undated.
- **Periods** are observation periods of the supplied frequency (e.g. months).

`ofs.compare(...).to_json()` wraps several reports:
`{"reports": {name: report}, "common_period": [start, end] | null,
"common_period_reports": {name: report} | null, "notes": [string]}`.

---

## Top level

| Key | Type | Meaning |
|---|---|---|
| `schema_version` | string | Version of this JSON layout (`"0.1"`). Independent of package and methodology versions. |
| `canonical` | boolean | `true` for reports produced by the public API with the canonical methodology. |
| `name` | string | Report / investment name. |
| `methodology` | object | The full methodology used ([methodology](#methodology)). |
| `input` | object | What OpenFactsheet believes it received ([input](#input)). |
| `returns` | array | Exactly the decimal returns analyzed ([returns](#returns)). |
| `data_quality` | object | Data-quality diagnostics ([data_quality](#data_quality)). |
| `metrics` | array | One entry per canonical metric, in canonical order ([metrics](#metrics)). |
| `drawdown_episodes` | array | All drawdown episodes ([drawdown_episodes](#drawdown_episodes)). |
| `benchmark` | object \| null | Benchmark alignment and input summaries; `null` without a benchmark ([benchmark](#benchmark)). |
| `document` | object \| null | For PDF / image input: the fund profile read from the document (decision 0032): `source`, `name`, `objective`, `benchmarks`, `currency`, `launch_date` (each `{value, confidence, evidence: {page, line, snippet, rule}, note}`), `identifiers` (`kind`, `value`, `valid` — true / false / null without a check digit —, `linked_isin`, `evidence`) and `notes`; `null` otherwise. |
| `factor_analysis` | object \| null | Factor-model regression; `null` without factor returns ([factor_analysis](#factor_analysis)). |
| `interpretations` | object | Map metric id → interpretation ([interpretations](#interpretations)). |
| `provenance` | object | Audit information ([provenance](#provenance)). |

---

## methodology

[models/assumptions.py](../../src/openfactsheet/models/assumptions.py) `Methodology.to_dict`.

| Key | Type | Meaning |
|---|---|---|
| `version` | string | Methodology version, e.g. `"0.1.0"`. |
| `name` | string | `"OpenFactsheet Methodology <version>"`. |
| `conventions` | object | The complete canonical assumptions registry from [policy/defaults.py](../../src/openfactsheet/policy/defaults.py), reproduced in full in [policies](policies.md#complete-canonical-assumptions-machine-readable). |

---

## input

[models/input.py](../../src/openfactsheet/models/input.py) `InputDiagnostics.to_dict`.
The benchmark's own input summary has the same shape.

| Key | Type | Meaning |
|---|---|---|
| `name` | string | Series name. |
| `source_type` | string | `list`, `tuple`, `numpy.ndarray`, `pandas.Series`, `pandas.DataFrame`, `csv`, `excel`, `pasted text`, with ` (monthly table)` appended for reshaped wide tables. |
| `observations` | integer | Number of analyzed returns. |
| `start`, `end` | string \| null | First and last analyzed dates; `null` if undated. |
| `years` | number \| null | `observations / periods_per_year`; `null` when not annualizable. |
| `frequency` | string | `daily`, `weekly`, `monthly`, `quarterly`, `yearly`, `irregular`, `unknown`. |
| `frequency_source` | string | `inferred` (from dates), `declared` (by the caller: undated input, or a single timestamp), `none`. |
| `frequency_evidence` | string | Human-readable reason for the frequency decision. |
| `periods_per_year` | number \| null | Annualization factor P; `null` for irregular/unknown frequency. |
| `return_scale` | string | `detected_decimal`, `detected_percent`, `declared_decimal`, `declared_percent`. |
| `return_scale_evidence` | string | Reason for the scale decision. |
| `missing_values` | integer | Interior missing values dropped (never filled). |
| `leading_missing_trimmed`, `trailing_missing_trimmed` | integer | Missing values trimmed at the ends. |
| `missing_expected_periods` | integer \| null | Calendar gaps plus interior missing values; `null` when not assessable (business-day daily, irregular, unknown, undated). |
| `duplicate_periods` | integer | Pairs of observations in the same calendar period (these make the frequency irregular). Identical timestamps are rejected before this point with `InputError`. |
| `was_sorted` | boolean | `false` if OpenFactsheet had to sort the timestamps. |
| `transformations` | array of string | Every transformation applied (sorting, trimming, percent→decimal, table reshaping, timezone removal, ...). |
| `warnings` | array of string | Input-level warnings. |

---

## returns

Dated input: `[{"date": "YYYY-MM-DD", "value": number}, ...]`.
Undated input: `[{"period": 1, "value": number}, ...]` (1-based position).
Values are decimal returns after all transformations listed in `input.transformations`.

---

## data_quality

[models/diagnostics.py](../../src/openfactsheet/models/diagnostics.py) `DataQualityReport.to_dict`.
Trigger rules for every field are in [criteria §7](criteria.md#7-data-quality-diagnostics).

| Key | Type | Meaning |
|---|---|---|
| `observations` | integer | `n`. |
| `years` | number \| null | History length in years. |
| `frequency` | string | Observation frequency. |
| `missing_values` | integer | Interior missing values. |
| `missing_expected_periods` | integer \| null | Missing periods (see input). |
| `duplicate_periods` | integer | Observations sharing a calendar period. |
| `zero_return_count` | integer | Returns exactly equal to 0. |
| `zero_return_pct` | number | `zero_return_count / n`, 0–1. |
| `longest_identical_run` | integer | Longest run of identical consecutive returns. |
| `impossible_return_count` | integer | Returns below -1 (-100%). |
| `total_loss` | boolean | Whether a return of exactly -1 occurs. |
| `suspicious_large_return_count` | integer | Robust outliers (robust z > 5); kept in calculations. |
| `autocorrelation` | object | `lag1`, `lag2`, `lag3` (number \| null) and `approx_95pct_significance_bound` (`1.96/sqrt(n)`, number \| null). |
| `ljung_box_pvalue` | number \| null | Ljung-Box p-value with 3 lags; `null` if `n < 10` or returns are constant. |
| `smoothing_risk` | string | `none`, `moderate`, `high`, `not_assessable`. |
| `smoothing_evidence` | string | Values and rule behind `smoothing_risk`. |
| `findings` | array | `{"id": string, "severity": "info" \| "warning" \| "critical", "message": string, "value": number \| null}`; every id is listed in [criteria §7.1](criteria.md#71-findings). |

---

## metrics

[models/metric.py](../../src/openfactsheet/models/metric.py) `MetricResult.to_dict`.
Every canonical metric appears exactly once, in canonical order, whether or not
it could be computed.

| Key | Type | Meaning |
|---|---|---|
| `id` | string | Stable metric identifier (see the [metric catalog](../metric_catalog.md)). |
| `name` | string | Display name. |
| `category` | string | `returns`, `volatility`, `drawdown`, `risk_adjusted`, `tail`, `distribution`, `consistency`, `dependence`, `benchmark`, `factors`, `statistical`. |
| `value` | number \| null | Raw `float64` value (never rounded, never non-finite); `null` when not computable. |
| `unit` | string | `decimal_return`, `fraction` (0–1), `ratio`, `periods`, `count`, `correlation`, `probability`, `beta`. |
| `status` | string | `applicable`, `low_confidence`, `supplementary`, `not_applicable`, `insufficient_data`, `error`. |
| `confidence` | string | `high`, `moderate`, `low`; `not_assessable` when `value` is `null`. Describes estimation reliability, not investment quality. |
| `direction` | string | `higher_is_better`, `lower_is_better`, `context_dependent`, `neutral`. Applies to the signed value (e.g. a max drawdown closer to 0 is better). |
| `nature` | string | `observed`, `derived`, `estimated`, `model_dependent`. |
| `observations` | integer | Observations used: `n`, or the aligned count `m` for benchmark and factor metrics. |
| `formula_id` | string | `<id>@v<version>`; changes when the formula changes. |
| `methodology_version` | string | Methodology that produced the value. |
| `assumptions` | array of string | Assumptions behind this value (annualization factor, risk-free rate, targets, benchmark, ...). Present even when `value` is `null`. |
| `warnings` | array of string | Data-specific caveats, de-duplicated. |
| `reason` | string \| null | Why there is no value; always present when `value` is `null`. |
| `details` | object | Metric-specific supporting values ([metric details](#metric-details)); `{}` for most metrics. |
| `reference_values` | object \| null | Reserved for reference-implementation values; `null` in methodology 0.1.0. |

Status and confidence rules: [criteria §8–10](criteria.md#8-applicability-criteria)
and each metric's page in [`interpretation/`](../interpretation/).

### Metric details

Keys emitted by metric functions in
[src/openfactsheet/metrics/](../../src/openfactsheet/metrics/). Metrics not
listed emit `{}`.

| Metric | Key | Type | Meaning |
|---|---|---|---|
| `best_period`, `worst_period` | `date` | string \| null | Date of the extreme observation (first occurrence). |
| | `position` | integer | 1-based position in the analyzed series. |
| `max_drawdown` | `peak_date`, `trough_date` | string \| null | Peak (`null` if the peak is the inception point or the input is undated) and trough dates of the deepest episode. |
| | `recovery_date` | string \| null | Recovery date; `null` if not recovered (the result then carries an open-loss warning). |
| | `recovered` | boolean | Whether wealth regained the peak. |
| | `peak_to_trough_periods` | integer | Periods from peak to trough. |
| | `duration_periods` | integer | Peak to recovery, or to the end of data if ongoing. |
| | `episodes` | integer | Only `0`, emitted instead of the keys above when no drawdown occurred. |
| `average_drawdown` | `episodes` | integer | Number of episodes averaged (0 when none). |
| `longest_drawdown_duration` | `years` | number \| null | Duration in years (`null` if not annualizable). |
| | `peak_date`, `recovery_date` | string \| null | Episode dates. |
| | `ongoing` | boolean | `true` if the episode has not recovered (the value is a lower bound). |
| | `episodes` | integer | Only `0`, emitted instead when no drawdown occurred. |
| `drawdown_count` | `ongoing` | integer | Number of episodes still open at the end (0 or 1). |
| `expected_shortfall_historical_95` | `tail_observations` | integer | Returns at or below the 5% quantile that were averaged. |
| `autocorrelation_lag1` … `lag3` | `approx_95pct_bound` | number | `1.96/sqrt(n)`. |
| | `significant` | boolean | `abs(rho) > bound`. |
| `ljung_box_pvalue` | `q_statistic` | number | Ljung-Box Q. |
| | `lags` | integer | 3. |
| `beta` | `standard_error`, `t_statistic`, `p_value` | number \| null | OLS inference for the slope (conventional i.i.d. errors). |
| `alpha` | `per_period` | number | OLS intercept per period (the value is `per_period × P`). |
| | `standard_error_per_period`, `t_statistic`, `p_value` | number \| null | OLS inference for the intercept. |
| `treynor_ratio` | `beta` | number | Beta used as the denominator. |
| `upside_capture` | `up_periods` | integer | Aligned periods with benchmark return > 0. |
| `downside_capture` | `down_periods` | integer | Aligned periods with benchmark return < 0. |
| `upside_capture`, `downside_capture` | `fund_annualized`, `benchmark_annualized` | number | Annualized geometric returns over those periods (numerator and denominator). |
| `payoff_ratio` | `average_gain`, `average_loss` | number | Mean of positive and of negative period returns (loss is signed). |
| `pain_ratio` | `pain_index` | number | Pain Index used as the denominator. |
| `modified_var_95` | `cornish_fisher_quantile` | number | Adjusted quantile `h` (replaces z = -1.645). |
| | `skewness`, `excess_kurtosis` | number | Population moments used by the expansion. |
| `jarque_bera_pvalue` | `statistic` | number | Jarque-Bera statistic (chi-squared with 2 degrees of freedom). |
| `probabilistic_sharpe_ratio` | `sharpe_per_period` | number | Per-period Sharpe ratio used by the test. |
| | `z_statistic` | number | Standardized distance of the Sharpe ratio from 0. |
| | `moment_skewness`, `moment_kurtosis` | number | Population skewness and non-excess kurtosis. |
| `sharpe_ratio_standard_error` | `sharpe_ratio` | number | Annualized Sharpe ratio (same as the `sharpe_ratio` metric). |
| | `ci_level`, `ci_lower`, `ci_upper` | number | Two-sided confidence interval of the annualized Sharpe ratio. |
| | `standard_error_per_period` | number | Standard error of the per-period Sharpe ratio. |
| `minimum_track_record_length` | `years` | number \| null | MinTRL in years (`null` if not annualizable). |
| | `observed_periods` | integer | Actual number of observations. |
| | `sufficient` | boolean | Whether the history is at least MinTRL long. |
| | `additional_periods_needed` | integer | `max(0, ceil(MinTRL - n))`. |
| `median_drawdown` | `episodes` | integer | Number of episodes. |
| `average_drawdown_duration` | `years` | number \| null | Average duration in years. |
| | `episodes`, `ongoing` | integer | Episodes averaged; how many are still open (lower bound). |
| `max_peak_to_trough_duration` | `years` | number \| null | Longest decline in years. |
| | `peak_date`, `trough_date` | string \| null | Dates of that decline (or `episodes: 0` when none). |
| `average_recovery_duration` | `years` | number \| null | Average recovery time in years. |
| | `recovered_episodes`, `excluded_open_episodes` | integer | Episodes used and open episodes excluded. |
| `cdar_95` | `tail_observations` | integer | Drawdown observations at or below the 5% quantile. |
| `modified_es_95` | `cornish_fisher_quantile` | number | Cornish-Fisher quantile `h` used by the expansion. |
| `best_calendar_year` | `year` | integer | Year of the best complete calendar year. |
| | `calendar_year_returns` | object | Map year (string) → compounded return of every complete calendar year. |
| | `excluded_partial_years` | object | Map year (string) → why it is incomplete. |
| `worst_calendar_year` | `year` | integer | Year of the worst complete calendar year. |
| `positive_calendar_years_pct` | `complete_years`, `positive_years` | integer | Counts behind the share. |
| | `calendar_year_returns`, `excluded_partial_years` | object | As for `best_calendar_year`. |
| `best_rolling_year`, `worst_rolling_year` | `window_end` | string \| null | Last date of the extreme one-year window. |
| | `windows`, `window_periods` | integer | Number of windows and window length in observations. |
| `positive_rolling_year_pct` | `windows`, `window_periods` | integer | Number of windows and window length. |
| `mean_return_standard_error` | `ci_level`, `ci_lower`, `ci_upper` | number | Student-t confidence interval of the per-period mean. |
| | `t_statistic`, `p_value` | number | Two-sided t-test of the mean against zero. |
| `factor_alpha`, `factor_alpha_t_statistic`, `factor_r_squared`, `factor_residual_volatility` | `model`, `dependent` | string | Model label and dependent variable of the factor regression. |
| | `factors` | array of string | Factor names. |
| | `hac_lags`, `df_resid` | integer | Newey-West lag and residual degrees of freedom. |
| `factor_alpha` | `per_period` | number | OLS intercept per period (the value is `per_period × P`). |
| | `standard_error_per_period`, `t_statistic`, `p_value` | number \| null | Newey-West inference for the intercept. |
| | `ci_level`, `ci_lower`, `ci_upper` | number \| null | Confidence interval of the **annualized** alpha. |
| `factor_alpha_t_statistic` | `p_value` | number \| null | Two-sided Student-t p-value. |
| `factor_r_squared` | `adjusted_r_squared` | number \| null | Adjusted R-squared. |
| `factor_residual_volatility` | `per_period` | number | Regression standard error per period. |

---

## drawdown_episodes

[metrics/path.py](../../src/openfactsheet/metrics/path.py) `DrawdownEpisode.to_dict`.
Every peak-to-recovery episode of the canonical wealth path, in chronological
order. Empty when no drawdown occurred; also empty when the series contains
returns below -100% (the wealth path is then not meaningful — see
`data_quality.impossible_return_count`).

Indices refer to the wealth index `W_0 … W_n` ([notation](notation.md#wealth-and-drawdowns)),
where `W_0 = 1` is the inception point before the first return and `W_k` is
wealth after the k-th return.

| Key | Type | Meaning |
|---|---|---|
| `peak_index` | integer | Index of the peak (0 = inception). |
| `trough_index` | integer | Index of the lowest wealth in the episode (first occurrence). |
| `recovery_index` | integer \| null | First index where wealth regains the peak; `null` if ongoing. |
| `depth` | number | Signed drawdown at the trough (≤ 0). |
| `peak_to_trough_periods` | integer | `trough_index - peak_index`. |
| `recovery_periods` | integer \| null | `recovery_index - trough_index`; `null` if ongoing. |
| `total_underwater_periods` | integer | Observations with drawdown < 0 in the episode. |
| `duration_periods` | integer | `recovery_index - peak_index`, or `n - peak_index` if ongoing. |
| `area` | number | Sum of `abs(D_t)` over the underwater observations (decimal × periods). |
| `peak_date`, `trough_date`, `recovery_date` | string \| null | Dates; `null` for the inception point, undated input or no recovery. |
| `recovered` | boolean | `recovery_index` is not `null`. |

---

## benchmark

`null` unless a benchmark was supplied. Otherwise
`{"alignment": {...}, "input": {...}}`, where `input` has the shape of
[input](#input) and `alignment` is
[models/report.py](../../src/openfactsheet/models/report.py) `BenchmarkDiagnostics.to_dict`:

| Key | Type | Meaning |
|---|---|---|
| `name` | string | Benchmark name. |
| `fund_observations` | integer | Fund observations before alignment. |
| `benchmark_observations` | integer | Benchmark observations before alignment. |
| `aligned_observations` | integer | Periods present in both (`m`, used by all benchmark metrics). |
| `fund_only_periods` | integer | Fund observations without a benchmark return (excluded, never filled). |
| `benchmark_only_periods` | integer | Benchmark observations outside the fund history. |
| `fund_coverage` | number | `aligned_observations / fund_observations`, 0–1. |
| `overlap_start`, `overlap_end` | string \| null | First and last aligned dates. |
| `alignment_method` | string | `calendar monthly period`, `calendar quarterly period`, `calendar yearly period`, `exact date`, or a `by position (...)` description. |
| `warnings` | array of string | Alignment warnings. |

---

## factor_analysis

`null` unless factor returns were supplied. Otherwise
[factors/models.py](../../src/openfactsheet/factors/models.py) `FactorAnalysis.to_dict`
(decision 0028):

| Key | Type | Meaning |
|---|---|---|
| `model` | string | Descriptive label, e.g. `Fama-French three-factor model` or `Custom factor model (2 factors)`. |
| `factor_names` | array of string | Factor columns in regression order. |
| `dependent` | string | Dependent variable: fund return minus RF, or the fund return when no RF column was supplied. |
| `return_scale`, `return_scale_evidence` | string | Scale applied to every factor column and why. |
| `alignment` | object | `fund_observations`, `factor_observations` (periods with every factor), `aligned_observations` (`m`), `fund_only_periods`, `fund_coverage`, `overlap_start`, `overlap_end`, `alignment_method`, `warnings`. |
| `fit` | object \| null | The regression, or `null` when it is not identified (see `reason`). |
| `reason` | string \| null | Why the regression could not be estimated. |

`fit`: `model`, `factor_names`, `dependent`, `observations` (`m`), `factors`
(`k`), `df_resid` (`m − k − 1`), `hac_lags`, `ci_level`, `alpha_per_period` and each
entry of `loadings` (`name`, `estimate`, `standard_error`, `t_statistic`, `p_value`,
`ci_lower`, `ci_upper`; inference is Newey-West), `r_squared`, `adj_r_squared`,
`residual_std_per_period`, `residual_autocorrelation_lag1`,
`residual_ljung_box_pvalue`, `max_vif`, `periods_per_year`, `alignment` and
`warnings`. Undefined statistics are `null`.

---

## interpretations

Map of metric id → [models/report.py](../../src/openfactsheet/models/report.py) `Interpretation.to_dict`:

| Key | Type | Meaning |
|---|---|---|
| `metric_id` | string | Metric id. |
| `plain` | string | Plain-language explanation (from the metric registry). |
| `professional` | string | Professional note (from the metric registry). |
| `context` | array of string | Data-specific notes: the reason when there is no value, then any rule notes ([criteria §13](criteria.md#13-interpretation-rules)). |

---

## provenance

[models/report.py](../../src/openfactsheet/models/report.py) `Provenance.to_dict`.

| Key | Type | Meaning |
|---|---|---|
| `package_version` | string | OpenFactsheet package version. |
| `methodology_version` | string | Methodology version. |
| `input_type` | string | Same as `input.source_type`. |
| `input_sha256` | string | SHA-256 fingerprint of the analyzed dates and values ([criteria §15](criteria.md#15-determinism-and-provenance)). |
| `date_range` | [string \| null, string \| null] | Start and end dates. |
| `frequency` | string | Observation frequency. |
| `annualization` | string | Annualization statement (factor and whether it was inferred or declared, or why nothing is annualized). |
| `observations` | integer | `n`. |
| `transformations` | array of string | Same as `input.transformations`. |
| `benchmark_name` | string \| null | Benchmark name. |
| `benchmark_sha256` | string \| null | Fingerprint of the analyzed benchmark returns. |
| `factor_names` | array of string \| null | Factor columns supplied (the RF column excluded). |
| `extraction` | object \| null | For document input (PDF, image): `engine` (e.g. `pypdf 6.18.1` or `rapidocr 3.9.2`), `source_sha256` (of the file), `page`, `confidence` (`high` / `moderate`), `monthly_values`, `checks`, `warnings`, `reconstructed_table` (decision 0030). OCR adds `ocr` (`name`, `version`, `models` with `file` and `sha256`), `image_sha256`, `repairs`, `min_cell_confidence` and, for scanned PDFs, `renderer` and `dpi` (decision 0031). `null` otherwise. |
| `factors_sha256` | string \| null | SHA-256 of the compact JSON map column name → fingerprint of that column (same construction as `input_sha256`), RF included. |
| `canonical` | boolean | Same as the top-level `canonical`. |

---

## Example: one metric entry

`ofs.analyze("tests/fixtures/monthly_fund_10y.csv")`, entry for `max_drawdown`:

```json
{
  "assumptions": [
    "Wealth index starts at 1 before the first return; drawdowns are measured from running peaks of compounded wealth."
  ],
  "category": "drawdown",
  "confidence": "high",
  "details": {
    "duration_periods": 54,
    "peak_date": "2020-06-30",
    "peak_to_trough_periods": 24,
    "recovered": false,
    "recovery_date": null,
    "trough_date": "2022-06-30"
  },
  "direction": "higher_is_better",
  "formula_id": "max_drawdown@v1",
  "id": "max_drawdown",
  "methodology_version": "0.1.0",
  "name": "Maximum drawdown",
  "nature": "observed",
  "observations": 120,
  "reason": null,
  "reference_values": null,
  "status": "applicable",
  "unit": "decimal_return",
  "value": -0.2732106828524845,
  "warnings": [
    "The deepest drawdown has not recovered by the end of the data; the loss is still open."
  ]
}
```
