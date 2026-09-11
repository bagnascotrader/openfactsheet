# 0020 — Mean-return inference and the Jarque-Bera normality test

**Status:** Accepted — methodology 0.1.0

## Problem

A confidence interval for the mean return needs a choice between a normal and
a Student-t quantile, and between one- and two-sided intervals. The Jarque-Bera
test can be computed from bias-corrected or population moments, and the choice
changes the statistic.

## Known definitions

- Mean standard error $s/\sqrt{n}$. Student-t interval
  $\bar r \pm t_{0.975,\,n-1}\,s/\sqrt{n}$ and t-statistic $t = \bar r / (s/\sqrt{n})$
  (Student, 1908), exact for normal i.i.d. data.
- Jarque & Bera (1987):

```math
JB = \frac{n}{6}\left(g_1^2 + \frac{g_2^2}{4}\right), \quad
g_1 = \frac{m_3}{m_2^{3/2}}, \quad g_2 = \frac{m_4}{m_2^2} - 3, \quad
p = 1 - F_{\chi^2_2}(JB)
```

  The original test uses population (biased) moments. Some variants
  substitute bias-corrected $G_1$ and $G_2$.

## PerformanceAnalytics behavior

PerformanceAnalytics has no function for these statistics. The R harness
instead uses R's own `t.test(r)` as an independent reference, and computes
Jarque-Bera manually from `skewness(method = "moment")` and
`kurtosis(method = "excess")`. **Verified:** the CI bounds, t-statistic and
p-value of `mean_return_standard_error` equal `t.test` to 1e-9 (p-value to
1e-7), and the Jarque-Bera statistic and p-value equal the manual R
computation.

## QuantStats behavior

Not used as a reference for these statistics.

## Empyrical behavior

Not used as a reference. SciPy is used instead: `scipy.stats.jarque_bera`
agrees with `jarque_bera_pvalue` (statistic to 1e-9, p-value to 1e-7), and
`scipy.stats.ttest_1samp(r, 0)` agrees with the reported p-value (**verified**).

## Academic sources

- Student [Gosset, W. S.] (1908). The Probable Error of a Mean. *Biometrika* 6(1).
- Jarque, C. M., & Bera, A. K. (1987). A Test for Normality of Observations and
  Regression Residuals. *International Statistical Review* 55(2).

## OpenFactsheet decision

- `mean_return_standard_error` (per period) is $s/\sqrt{n}$. Its details give
  the two-sided **95%** Student-t interval with $n-1$ degrees of freedom
  (`mean_inference.ci_level`), the t-statistic and the two-sided p-value
  against a zero mean. It is `not_applicable` when $s = 0$, uses the
  `dispersion` minimum-data policy, and is volatility-based.
- `jarque_bera_pvalue` uses population moments and the asymptotic
  $\chi^2_2$ p-value, and reports the statistic in its details. It is
  `supplementary`, `model_dependent`, uses the `skewness` minimum-data policy
  (low confidence below 60 observations), and is `not_applicable` when
  $m_2 = 0$.

## Rationale

The Student-t interval is exact under normality and reduces to the normal
interval for large $n$, so short histories get honestly wide intervals.
Jarque-Bera follows the original definition, which matches SciPy and R
practice, so users can reproduce the value.

## Consequences

- Neither statistic models serial correlation. Smoothed series get intervals
  that are too narrow, which the smoothing diagnostics flag.
- The Jarque-Bera test has poor size and low power in small samples, and
  flags trivial departures in very large ones. It is a diagnostic, not a
  performance measure, and the report labels it supplementary.
