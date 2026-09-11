# 0019 — Sharpe-ratio inference: PSR, standard error, minimum track record length

**Status:** Accepted — methodology 0.1.0

## Problem

A Sharpe ratio from a finite, non-normal sample is uncertain. Measuring that
uncertainty requires choosing a variance formula for the estimator, a
reference Sharpe ratio, confidence levels, moment estimators, and whether the
result is per period or annualized.

## Known definitions

For the per-period ratio $\widehat{SR} = \bar r / s$, the asymptotic
i.i.d. variance allowing for skewness $g_3$ and (non-excess) kurtosis $g_4$ is
(Mertens, 2002; Opdyke, 2007):

```math
\operatorname{Var}(\widehat{SR}) \approx \frac{1 - g_3\widehat{SR} + \frac{g_4-1}{4}\widehat{SR}^2}{n-1}
```

Bailey & López de Prado (2012) build on this variance:

```math
\mathrm{PSR}(SR^*) = \Phi\!\left(\frac{(\widehat{SR}-SR^*)\sqrt{n-1}}{\sqrt{1-g_3\widehat{SR}+\frac{g_4-1}{4}\widehat{SR}^2}}\right),
\qquad
\mathrm{MinTRL} = 1 + \left(1-g_3\widehat{SR}+\tfrac{g_4-1}{4}\widehat{SR}^2\right)\left(\frac{z_{1-\alpha}}{\widehat{SR}-SR^*}\right)^2
```

The Deflated Sharpe Ratio additionally corrects for the number of strategies
tried.

## PerformanceAnalytics behavior

`ProbSharpeRatio` and `MinTrackRecord` use the formulas above with moment
skewness and moment kurtosis, but the default `ignore_kurtosis = TRUE` fixes
$g_4 = 3$. **Verified:** with `refSR = 0` and `ignore_kurtosis = FALSE`,
OpenFactsheet's `probabilistic_sharpe_ratio` and
`minimum_track_record_length` agree to 1e-9 on the fixtures with a positive
Sharpe ratio. When `refSR > SR`, PerformanceAnalytics stops with an error;
on the negative fixture OpenFactsheet reports PSR < 0.5 and MinTRL as
`not_applicable` (both asserted). PA's `sr_confidence_interval` uses
`qnorm(p)` with p = 0.95, which gives a 90% two-sided interval on the
per-period Sharpe ratio.

## QuantStats behavior

Not used as a reference for these statistics.

## Empyrical behavior

Not used as a reference for these statistics.

## Academic sources

- Lo, A. W. (2002). The Statistics of Sharpe Ratios. *Financial Analysts Journal* 58(4).
- Mertens, E. (2002). Comments on Variance of the IID Estimator in Lo (2002).
- Opdyke, J. D. (2007). Comparing Sharpe Ratios: So Where Are the p-Values?
  *Journal of Asset Management* 8(5).
- Bailey, D. H., & López de Prado, M. (2012). The Sharpe Ratio Efficient
  Frontier. *Journal of Risk* 15(2).

## OpenFactsheet decision

- $\widehat{SR}$ = per-period mean / sample standard deviation, with
  $r_f = 0$. $g_3 = m_3/m_2^{3/2}$ and $g_4 = m_4/m_2^2$ are population moments,
  and kurtosis is **not** ignored (`sharpe_inference.moments`).
- `probabilistic_sharpe_ratio`: $SR^* = 0$ (`sharpe_inference.reference_sharpe`).
  It is defined for any sign of $\widehat{SR}$.
- `sharpe_ratio_standard_error`: $\sqrt{P}\sqrt{\text{factor}/(n-1)}$. Its details
  give the two-sided **95%** interval $\widehat{SR}\sqrt{P} \pm z_{0.975}\,\mathrm{SE}$
  (`sharpe_inference.ci_level`).
- `minimum_track_record_length`: 95% one-sided (`z_{0.95}`,
  `sharpe_inference.min_track_record_confidence`), in periods, with years and
  sufficiency in the details. It is `not_applicable` when $\widehat{SR} \le 0$.
- All three are `not_applicable` if $s = 0$ or the variance factor is not
  positive. They use the new minimum-data policy `asymptotic_inference`
  (mathematical minimum 4; low confidence below 36 observations, moderate below 60).
- They are volatility-based: serial correlation is not modelled, so smoothing
  risk lowers their confidence ([0014](0014-smoothing-risk.md)).
- The Deflated Sharpe Ratio is **not computed**: it requires the number of
  trials, which a single return series does not reveal.

## Rationale

Keeping kurtosis follows the paper. Setting $g_4 = 3$ would overstate
confidence for fat-tailed strategies, which contradicts "humble about
inference". $SR^* = 0$ is the only reference value that needs no judgment. A
true two-sided 95% interval is the conventional reading of "95% CI".

## Consequences

- PSR and MinTRL differ from PerformanceAnalytics defaults on fat-tailed
  series. They agree once `ignore_kurtosis = FALSE` is set.
- The interval is wider than PerformanceAnalytics' 90% interval.
- The i.i.d. variance understates uncertainty for smoothed or serially
  correlated returns (Lo, 2002). The metric documentation and confidence
  labels disclose this.
