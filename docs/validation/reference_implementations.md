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
| skfolio | 1.0.6 | BSD-3-Clause | Python cross-check for DaR / CDaR / EDaR / EVaR (optional `validation` extra). |
| R `stats` (base R) | R 4.3.1 | GPL-2 \| GPL-3 | External oracle only: `acf`, `Box.test`, `cor`, `lm`, `t.test`, `pchisq` in the R harness. |
| statsmodels | installed version | BSD-3-Clause | Runtime dependency: OLS, ACF, Ljung-Box. |
| SciPy | installed version | BSD-3-Clause | Runtime dependency: skewness, kurtosis, normal / Student-t / chi-squared distributions; `jarque_bera` and `ttest_1samp` used as test references. |
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
calls empyrical, QuantStats and skfolio directly and is skipped automatically when they
are not installed (`pip install -e ".[validation]"`); its SciPy checks
(Jarque-Bera, one-sample t-test) always run.

Where PerformanceAnalytics stops with an error (PSR and MinTRL for a negative
Sharpe ratio), the harness records `null` and the tests assert OpenFactsheet's
documented behavior instead.

**Fixtures.** `monthly_fund_10y` (120 months, fat-tailed), `negative_fund`
(60 months), `smoothed_hedge_fund` (96 months, smoothed, large losses),
`benchmark_case_fund` / `benchmark_case_benchmark` (102 months each, 96
overlapping). Generated once by `scripts/make_fixtures.py` and committed.

Tolerance for agreement: relative 1e-9 / absolute 1e-12 (Ljung-Box,
Jarque-Bera and t-test p-values: relative 1e-7).

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
| payoff_ratio | — | — | Agrees (`stats.payoff_ratio`) | |
| kappa_3_ratio | Agrees (`Kappa(MAR=0, l=3)`) | — | — | Per period. |
| upside_potential_ratio | Agrees (`UpsidePotentialRatio(MAR=0, method="full")`); differs (pinned) from the default `method="subset"` | — | — | Per period. |
| semi_deviation | Agrees (`SemiDeviation` x sqrt(12)) | — | — | PA reports per period. |
| downside_potential | Agrees (`DownsideDeviation(MAR=0, potential=TRUE)`) | — | — | Per period. |
| mean_absolute_deviation | Agrees (`MeanAbsoluteDeviation`) | — | — | |
| sterling_ratio | Agrees (`SterlingRatio(excess=0.1)`) | — | — | |
| burke_ratio | Differs (pinned) from `BurkeRatio`; agrees with `Return.annualized / sqrt(sum(findDrawdowns depths^2))` | — | — | PA uses runs of negative returns and a percent-input scaling. |
| pain_ratio | Agrees with `Return.annualized / mean(abs(Drawdowns))` | — | — | PA `PainRatio` inherits the `DrawdownPeak` issue. |
| gaussian_var_95 | Agrees (`VaR(p=0.95, method="gaussian")`) | — | — | Population standard deviation; QuantStats `stats.value_at_risk` uses the sample std (see var_historical_95 row). |
| modified_var_95 | Agrees (`VaR(p=0.95, method="modified")`) | — | — | Cornish-Fisher with population moments. |
| jarque_bera_pvalue | Agrees with a manual R computation from `skewness(method="moment")` and `kurtosis(method="excess")` | — | — | Also agrees with SciPy `stats.jarque_bera` (statistic 1e-9, p-value 1e-7). |
| probabilistic_sharpe_ratio | Agrees (`ProbSharpeRatio(refSR=0, ignore_kurtosis=FALSE)`) on fixtures with a positive Sharpe ratio | — | — | PA stops with an error when SR < 0; OpenFactsheet reports PSR < 0.5 (asserted). |
| minimum_track_record_length | Agrees (`MinTrackRecord(refSR=0, p=0.95, ignore_kurtosis=FALSE)`) on fixtures with a positive Sharpe ratio | — | — | `not_applicable` when SR <= 0 (asserted); PA stops with an error. |
| sharpe_ratio_standard_error | — (same variance formula; PA's interval is 90% two-sided) | — | — | Checked against a hand computation in unit tests. |
| mean_return_standard_error | Agrees with R `t.test` (CI bounds, t-statistic; p-value to 1e-7) | — | — | Also agrees with SciPy `stats.ttest_1samp` p-value. |

Phase 2b metrics. Columns as above; skfolio results are in the Notes column.

| Metric id | PerformanceAnalytics / R | empyrical | QuantStats | Notes |
|---|---|---|---|---|
| drawdown_at_risk_95 | — | — | — | skfolio `drawdown_at_risk` differs (pinned): lower order statistic `quantile(-D, 0.95, "inverted_cdf")`; OpenFactsheet = linear `Q_0.05(D)` (asserted). |
| cdar_95 | Differs (pinned): `CDD` = 5% quantile over all `findDrawdowns` runs (episodes and zero runs) | — | — | Agrees with skfolio `cdar` on the canonical path when 0.05·n is an integer (n = 60 and 120). |
| edar_95 | — | — | — | Agrees with skfolio `edar` on the canonical path (rel 1e-7, solver tolerance). |
| evar_95 | — | — | — | Agrees with skfolio `evar` (rel 1e-7). |
| modified_es_95 | Agrees (`ES(p=0.95, method="modified")`) | — | — | Population moments, full expansion. |
| median_drawdown | Agrees with the median of `findDrawdowns` negative-episode depths | — | — | |
| average_drawdown_duration | Agrees with the mean `findDrawdowns` length after subtracting 1 from an open last episode | — | — | Open-episode +1 convention (difference 3). |
| max_peak_to_trough_duration | Agrees with max `findDrawdowns` `peaktotrough` | — | — | |
| average_recovery_duration | Agrees with the mean `findDrawdowns` `recovery` over recovered episodes (open last episode dropped) | — | — | `not_applicable` asserted when the only episode is open (negative_fund). |
| recovery_factor | — | — | Differs (pinned): `stats.recovery_factor` = arithmetic sum of returns / \|MDD\| | OpenFactsheet = compounded cumulative return / \|MDD\| (asserted). |
| geometric_mean_return | Agrees (`mean.geometric`) | — | — | |
| interquartile_range | Agrees with R `IQR` (type 7) | — | — | |
| best_calendar_year | Agrees with R compounded returns of years with 12 monthly observations | — | — | Monthly fixtures; partial years excluded by OpenFactsheet. |
| worst_calendar_year | Agrees (same computation) | — | — | |
| positive_calendar_years_pct | Year set and every complete-year return agree (to 1e-9) | — | — | Share itself derived from the same years. |
| best_rolling_year | Agrees with the max of `zoo::rollapply(R, 12, prod(1 + x) - 1)` | — | — | Monthly fixtures. |
| worst_rolling_year | Agrees with the min of the same rolling series | — | — | |
| positive_rolling_year_pct | Agrees with the share of positive windows; window count agrees | — | — | |

Benchmark-relative additions (decision 0027), on the `benchmark_case` fixture
(96 aligned months).

| Metric id | PerformanceAnalytics / R | empyrical | QuantStats | Notes |
|---|---|---|---|---|
| capture_ratio | — (ratio of PA's summed captures would differ as in item 8) | Agrees (`up_down_capture`) | — | |
| batting_average | Up/down components agree (`UpDownRatios(method="Percent", side="Up"/"Down")`) | — | — | The overall share has no PA counterpart; checked by hand in unit tests. |
| residual_volatility | Agrees with R `summary(lm(...))$sigma` x sqrt(12); differs (pinned) from `SpecificRisk` | — | — | PA divides the residual sum of squares by m, not m − 2 (verified). |
| appraisal_ratio | Differs (pinned) from `AppraisalRatio(method="appraisal")` | — | — | PA = `CAPM.jensenAlpha` (geometric) / `SpecificRisk` (verified); OpenFactsheet = alpha / residual_volatility (asserted). |
| m_squared | Agrees with `Modigliani` x 12 | — | — | PA reports per period. |
| bull_beta | Agrees (`CAPM.beta.bull`) | — | — | |
| bear_beta | Agrees (`CAPM.beta.bear`) | — | — | |
| timing_ratio | Agrees (`TimingRatio`) | — | — | |

Factor models (decision 0028), on the `factor_case` fixture (Fama-French-style
factors in percent with an RF column and one missing HML month; 107 aligned
months for the three-factor model, 108 for CAPM). Reference: R `lm` +
`sandwich::NeweyWest(lag = floor(4 (m/100)^(2/9)), prewhite = FALSE, adjust = TRUE)`
+ `lmtest::coeftest` / `coefci`, generated by `validation/r/factor_reference.R`
into `tests/fixtures/reference/factor_models.json`.

| Quantity | R reference | Notes |
|---|---|---|
| alpha and every loading | Agrees to 1e-9 relative (`coef(lm)`) | |
| Newey-West standard errors, t, p, 95% CI | Agree to 1e-8 relative | Bartlett kernel, fixed lag, no prewhitening, small-sample factor m/(m−k−1), Student t with m−k−1 df. `NeweyWest()` defaults (automatic bandwidth, prewhitening) differ by design. |
| factor_alpha | Agrees with `coef(lm)[1] × 12` | |
| factor_alpha_t_statistic | Agrees with `coeftest(...)[1, 3]` | |
| factor_r_squared | Agrees with `summary(lm)$r.squared` (adjusted: `$adj.r.squared`) | |
| factor_residual_volatility | Agrees with `summary(lm)$sigma × sqrt(12)` | |

The R harness records per-episode `findDrawdowns` columns, whether the last
episode is open, complete-year returns, rolling 12-month returns, modified ES,
`mean.geometric` and `IQR`; `test_phase2b_agreement` rebuilds each statistic
from them. skfolio is compared on OpenFactsheet's canonical drawdown path
because its own compounded path starts the running peak at W_1 (difference 15).

R's base `t.test` is used as an additional independent reference for the
mean-return interval; it is not part of PerformanceAnalytics.

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
10. **Upside potential ratio (PA default).** `UpsidePotentialRatio` defaults to
    `method = "subset"` (divides by the number of gains / losses); OpenFactsheet
    uses the full-sample denominator, equal to `method = "full"`. See
    [0016](../methodology/decisions/0016-lower-partial-moment-ratios.md).
11. **Burke ratio (PA).** `BurkeRatio` treats runs of consecutive negative
    returns as drawdowns and multiplies returns by 0.01; OpenFactsheet uses
    peak-to-recovery episode depths. See
    [0017](../methodology/decisions/0017-drawdown-ratios-burke-sterling-pain.md).
12. **Pain ratio (PA).** `PainRatio` inherits the `PainIndex` / `DrawdownPeak`
    percent-input issue (item 2).
13. **PSR / MinTRL (PA defaults).** `ProbSharpeRatio` and `MinTrackRecord`
    default to `ignore_kurtosis = TRUE` (kurtosis fixed at 3); OpenFactsheet keeps
    the sample kurtosis and agrees with `ignore_kurtosis = FALSE`. PA stops with an
    error when the reference Sharpe ratio exceeds the observed one; OpenFactsheet
    reports PSR below 0.5 and MinTRL as `not_applicable`. See
    [0019](../methodology/decisions/0019-sharpe-ratio-inference.md).
14. **Sharpe confidence interval (PA).** `ProbSharpeRatio(...)$sr_confidence_interval`
    uses `qnorm(p)` with p = 0.95, a 90% two-sided interval on the per-period
    Sharpe ratio; OpenFactsheet reports a two-sided 95% interval on the annualized
    Sharpe ratio (not numerically compared).
15. **Drawdown path (skfolio).** `get_drawdowns(compounded=True)` starts its
    running peak at W_1, so a first-period loss is not a drawdown; the default is
    `compounded=False` (uncompounded cumulative sums). OpenFactsheet counts W_0 = 1
    as a peak and compounds (asserted). See
    [0021](../methodology/decisions/0021-drawdown-tail-and-entropic-measures.md).
16. **Drawdown-at-Risk (skfolio).** `drawdown_at_risk` uses the lower order
    statistic (inverted-CDF quantile); OpenFactsheet uses the linear quantile of
    decision 0010 (asserted).
17. **CDaR (skfolio).** `cdar` uses a fractional Rockafellar-Uryasev weighting of
    the tail; it equals OpenFactsheet's mean of `D_t <= Q_0.05(D)` only when
    0.05·n is an integer.
18. **Conditional Drawdown (PA).** `CDD` returns the 5% quantile over all
    `findDrawdowns` runs (the drawdown episodes and the zero-return runs between
    them), inverted to a positive number: neither a conditional expectation nor
    computed on the drawdown path, so it is not a CDaR reference (verified in the
    R harness and pinned by a test).
19. **Recovery factor (QuantStats).** `stats.recovery_factor` divides the
    arithmetic sum of returns by |MDD|; OpenFactsheet uses the compounded
    cumulative return (asserted). See
    [0025](../methodology/decisions/0025-episode-durations-and-path-summaries.md).
20. **Open drawdown episodes (PA).** As in item 3, `findDrawdowns` `length` and
    `recovery` count an open last episode one period longer; the tests subtract 1
    (length) or drop the episode (recovery) before comparing.
21. **Specific risk and appraisal ratio (PA).** `SpecificRisk` is the population
    (m-denominator) standard deviation of the regression residuals, annualized;
    OpenFactsheet uses the regression standard error (m − 2), consistent with the
    OLS standard errors. `AppraisalRatio(method = "appraisal")` divides Jensen's
    alpha computed from geometric annualized returns by `SpecificRisk`;
    OpenFactsheet divides the arithmetic annualized OLS alpha by its residual
    volatility (both relationships asserted). See
    [0027](../methodology/decisions/0027-benchmark-relative-additions.md).
