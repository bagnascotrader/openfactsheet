# Reference implementations

OpenFactsheet implements every metric independently from its mathematical
definition and then checks the numbers against established implementations.
Agreement across languages and libraries is evidence of correctness;
disagreements are either fixed or recorded here and in the
[methodology decisions](../methodology/decisions/README.md), with a test that
pins the relationship.

## Libraries and licenses

| Library | Version checked | License | Role |
|---|---|---|---|
| PerformanceAnalytics (R) | 2.0.4 on R 4.3.1 | GPL-2 \| GPL-3 | External numerical oracle only. Function bodies were read to understand conventions; **no code was copied** into OpenFactsheet. |
| empyrical-reloaded | 0.5.12 | Apache-2.0 | Python cross-check (optional `validation` extra). |
| QuantStats | 0.0.81 | Apache-2.0 | Python cross-check (optional `validation` extra). |
| statsmodels | installed version | BSD-3-Clause | Runtime dependency: OLS, ACF, Ljung-Box. |
| SciPy | installed version | BSD-3-Clause | Runtime dependency: skewness, kurtosis. |
| NumPy | installed version | BSD-3-Clause | Runtime dependency: numerical kernels, quantiles. |
| pandas | installed version | BSD-3-Clause | Runtime dependency: labeled time series and input handling. |

Reference libraries are never runtime dependencies of the core package.

## How the checks run

**R harness.** `validation/r/performanceanalytics_reference.R` reads the
committed synthetic fixtures in `tests/fixtures/` and writes
`tests/fixtures/reference/performanceanalytics.json`. The JSON is committed, so
the Python test suite does not need R. Regenerate from the repository root with:

```bash
Rscript validation/r/performanceanalytics_reference.R
```

The benchmark case aligns fund (month-end dates) and benchmark (month-start
dates) by calendar month in R, the same convention OpenFactsheet uses.

**Python checks.** `tests/cross_library/test_performanceanalytics.py` compares
against the committed R values. `tests/cross_library/test_python_references.py`
calls empyrical and QuantStats directly and is skipped automatically when they
are not installed (`pip install -e ".[validation]"`).

**Fixtures.** `monthly_fund_10y` (120 months, fat-tailed), `negative_fund`
(60 months), `smoothed_hedge_fund` (96 months, smoothed, large losses),
`benchmark_case_fund` / `benchmark_case_benchmark` (102 months each, 96
overlapping). Generated once by `scripts/make_fixtures.py` and committed.

Tolerance for agreement: relative 1e-9 / absolute 1e-12 (Ljung-Box p-value:
relative 1e-7).

## Per-metric agreement

"Agrees" means asserted equal within tolerance on every applicable fixture.
"Differs (pinned)" means the test asserts the documented relationship or
inequality. "—" means not compared.

| Metric id | PerformanceAnalytics | empyrical | QuantStats | Notes |
|---|---|---|---|---|
| cumulative_return | Agrees (`Return.cumulative`) | Agrees (`cum_returns_final`) | — | |
| cagr | Agrees (`Return.annualized`, geometric) | Agrees (`annual_return`) | Agrees with `stats.cagr(periods=12)`; default differs (pinned) | QuantStats' default `periods` assumes daily observations. |
| annualized_arithmetic_mean | Agrees (`Return.annualized(geometric=FALSE)`) | — | — | |
| volatility | Agrees (`StdDev`) | — | — | |
| annualized_volatility | Agrees (`StdDev.annualized`) | Agrees (`annual_volatility`) | — | |
| downside_deviation | Agrees (`DownsideDeviation(MAR=0)` x sqrt(12)) | Agrees (`downside_risk`) | — | PA reports per period. |
| sharpe_ratio | Agrees (`SharpeRatio.annualized(geometric=FALSE)`) | Agrees (`sharpe_ratio`) | Agrees (`stats.sharpe`) | PA default (`geometric=TRUE`) differs (pinned). |
| sortino_ratio | Agrees (`SortinoRatio` x sqrt(12)) | Agrees (`sortino_ratio`) | — | PA reports per period. |
| calmar_ratio | Agrees (`CalmarRatio`) | Agrees (`calmar_ratio`) | Differs (pinned): `stats.calmar` = default CAGR / \|MDD\| | Inherits QuantStats' daily CAGR default. |
| martin_ratio | Agrees with `Return.annualized / sqrt(mean(Drawdowns^2))` | — | — | PA `MartinRatio` inherits the `DrawdownPeak` issue. |
| omega_ratio | Agrees (`Omega(L=0, method="simple")`) | Agrees (`omega_ratio`) | — | |
| max_drawdown | Agrees with `-maxDrawdown` | Agrees (`max_drawdown`) | Agrees (`stats.max_drawdown`) | PA reports a positive magnitude. |
| average_drawdown | Agrees with `-AverageDrawdown` | — | — | PA reports a positive magnitude. |
| longest_drawdown_duration | Differs (pinned): equal for recovered episodes, PA one period longer for an ongoing episode | — | — | `findDrawdowns` `length`. |
| ulcer_index | Agrees with `sqrt(mean(Drawdowns^2))` | — | — | PA `UlcerIndex` differs (percent-input assumption). |
| pain_index | Agrees with `mean(abs(Drawdowns))` | — | — | PA `PainIndex` same issue. |
| var_historical_95 | Agrees (`VaR(p=0.95, method="historical")`) | — | Differs (pinned): `stats.value_at_risk` is parametric normal | Verified equal to the normal 5% quantile with sample mean/std. |
| expected_shortfall_historical_95 | Agrees (`ES(p=0.95, method="historical")`) | — | — | PA uses `r < q`; OpenFactsheet `r <= q` (no ties in fixtures). |
| tail_ratio | — | Agrees (`tail_ratio`) | Agrees (`stats.tail_ratio`) | |
| skewness | Agrees with `skewness(method="moment")` x sqrt(n(n−1))/(n−2) | — | Agrees (`stats.skew`) | PA `"sample"` = G1 x (n/(n−1))^1.5 (pinned). |
| excess_kurtosis | Agrees (`kurtosis(method="sample_excess")`) | — | Agrees (`stats.kurtosis`) | |
| best_period / worst_period | — | — | Agrees with max / min of the series | |
| positive_period_pct | — | — | Agrees (`stats.win_rate`) | Fixtures contain no zero returns; QuantStats excludes zeros from the denominator. |
| autocorrelation_lag1..3 | Agrees with R `acf` | — | — | |
| ljung_box_pvalue | Agrees with R `Box.test(lag=3, type="Ljung-Box")` | — | — | |
| beta | Agrees (`CAPM.beta`) | Agrees (`beta`) | — | |
| alpha | Agrees with `CAPM.alpha` x 12 | Differs (pinned): empyrical = (1 + alpha/12)^12 − 1 | — | Arithmetic vs geometric annualization. |
| correlation | Agrees with R `cor` | — | — | |
| r_squared | Agrees with R `lm` R² | — | — | |
| tracking_error | Agrees (`TrackingError`) | — | — | |
| information_ratio | Differs (pinned) from `InformationRatio`; agrees with arithmetic IR computed in R | — | Agrees after scaling: `stats.information_ratio` x sqrt(12) | PA uses geometric `ActivePremium`; QuantStats is per period. |
| active_return | Differs (pinned) from `ActivePremium` | — | — | Arithmetic vs difference of geometric returns. |
| upside_capture | Differs (pinned) from `UpDownRatios(Capture, Up)` | Agrees (`up_capture`) | — | PA divides sums of returns. |
| downside_capture | Differs (pinned) from `UpDownRatios(Capture, Down)` | Agrees (`down_capture`) | — | PA = sum ratio over `Rb <= 0` (verified). |
| treynor_ratio | Differs (pinned): PA = geometric annualized return / beta (verified) | — | — | OpenFactsheet = arithmetic annualized mean / beta (verified against PA's beta). |
| gain_to_pain_ratio | — | — | Agrees (`stats.gain_to_pain_ratio`) | Monthly fixtures. |

Metrics without a reference comparison (median_return, arithmetic_mean,
current_drawdown, drawdown_count, time_underwater_pct, negative_period_pct,
streaks, zero_return_pct) are checked against hand computations in
`tests/unit/metrics/test_formulas.py` and property tests.

## Known convention differences

1. **Sharpe ratio (PA default).** `SharpeRatio.annualized` uses the annualized
   geometric return in the numerator unless `geometric = FALSE`.
   See [0008](../methodology/decisions/0008-sharpe-ratio.md).
2. **Ulcer / Pain / Martin (PA).** `DrawdownPeak` divides returns by 100, which
   assumes percent inputs; on decimal inputs PA's values differ from the
   textbook formulas applied to PA's own `Drawdowns()` path. See
   [0007](../methodology/decisions/0007-drawdown-conventions.md).
3. **Drawdown duration (PA).** `findDrawdowns` counts an episode still open at
   the end of the data one period longer than OpenFactsheet.
4. **Skewness (PA `"sample"`).** Uses the population standard deviation inside a
   sample-style formula: `G1 x (n/(n−1))^1.5`. See
   [0011](../methodology/decisions/0011-skewness-kurtosis.md).
5. **Expected Shortfall (PA).** Averages returns strictly below the quantile;
   OpenFactsheet includes a return equal to the quantile. Identical unless ties
   occur. See [0010](../methodology/decisions/0010-var-es-quantiles.md).
6. **Alpha (empyrical).** Annualized geometrically, `(1 + a)^P − 1`;
   OpenFactsheet uses `a x P`.
7. **Information ratio, active return, Treynor (PA).** PA uses geometric
   annualized returns; OpenFactsheet uses arithmetic means.
8. **Capture ratios (PA).** PA divides sums of returns and treats zero-benchmark
   periods as down periods; OpenFactsheet compounds geometrically
   (Morningstar-style) and excludes zero-benchmark periods from both sides. See
   [0012](../methodology/decisions/0012-benchmark-alignment-and-relative-metrics.md).
9. **QuantStats defaults.** `stats.cagr` (and therefore `stats.calmar`) assumes
   daily observations unless `periods` is passed; `stats.value_at_risk` is
   parametric (normal); `stats.information_ratio` is not annualized. All three
   are verified in `tests/cross_library/test_python_references.py`.
   `stats.cvar` conditions on the parametric threshold (observed, not asserted).
