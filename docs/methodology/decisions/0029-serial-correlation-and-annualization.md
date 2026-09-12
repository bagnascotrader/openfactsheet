# 0029 — Serial correlation and annualization: variance ratio, Lo-adjusted Sharpe, profit factor

**Status:** Accepted — methodology 0.1.0

## Problem

Square-root-of-time annualization assumes serially uncorrelated returns. Smoothed
or illiquid returns (hedge funds, private assets) are positively autocorrelated,
so annualized volatility is understated and the annualized Sharpe ratio
overstated. CLAUDE.md lists "annualization under serial correlation" as a
decision to make explicitly. The conventional ratios stay canonical (decision
0008); the question is which established correction to report beside them, at
which horizon, and from which autocorrelation estimator. Separately, the profit
factor is widely quoted and was missing from the return summary.

## Known definitions

With sample autocorrelations $\hat\rho_k$ and horizon $q$:

```math
\mathrm{VR}(q) = 1 + 2 \sum_{k=1}^{q-1} \Big(1 - \frac{k}{q}\Big) \hat\rho_k, \qquad
\eta(q) = \frac{q}{\sqrt{q + 2 \sum_{k=1}^{q-1} (q-k) \hat\rho_k}} = \sqrt{\frac{q}{\mathrm{VR}(q)}}
```

- Lo & MacKinlay (1988): the variance ratio of $q$-period to one-period returns;
  asymptotic i.i.d. variance of $\sqrt n(\mathrm{VR}-1)$ is $2(2q-1)(q-1)/(3q)$.
  Their overlapping estimator is asymptotically equivalent to the
  autocorrelation form above.
- Lo (2002), "The Statistics of Sharpe Ratios": the $q$-period Sharpe ratio is
  $\eta(q)\,\mathrm{SR}$, with $\eta(q) = \sqrt q$ only without serial
  correlation; eq. (33) gives the AR(1) closed form.
- Profit factor: gross gains / gross losses (Pardo 2008); equal to one plus
  Schwager's gain-to-pain ratio.

## PerformanceAnalytics behavior

No function implements Lo's $\eta(q)$ annualization or the variance ratio
(`SmoothingIndex` and `Return.GLM` address smoothing through a different model;
unsmoothing is outside the canonical report, decision 0014). No profit factor.

## QuantStats behavior

`stats.profit_factor` = sum of non-negative returns / |sum of negative returns|.
**Verified** to agree on all single-series fixtures (zeros add nothing to either
sum). No variance ratio or Lo adjustment.

## Empyrical behavior

None of these statistics.

## Academic sources

- Lo, A. W., & MacKinlay, A. C. (1988). Stock Market Prices Do Not Follow Random Walks.
- Lo, A. W. (2002). The Statistics of Sharpe Ratios. *Financial Analysts Journal* 58(4).
- Getmansky, M., Lo, A. W., & Makarov, I. (2004). Serial correlation and illiquidity in
  hedge fund returns.
- Pardo, R. (2008). *The Evaluation and Optimization of Trading Strategies*.

## OpenFactsheet decision

- **Horizon:** one year, $q = \operatorname{round}(P)$ (12 monthly, 4 quarterly,
  52 weekly, 252 or 365 daily) — the horizon the annualized ratios refer to.
  Undefined for yearly data ($q = 1$), irregular or undated data.
- **Estimator:** the sample autocorrelations of the dependence metrics
  (full-sample denominator, statsmodels `acf(adjusted=False)`), on simple
  returns, lags $1..q-1$.
- **Minimum data:** two years ($n \ge 2q$); below that both statistics are
  `not_applicable` with the reason. Confidence policy `long_horizon_dependence`
  (years basis): low below 5 years and moderate below 10, because the standard
  error of $\mathrm{VR}(q)$ is about $\sqrt{4/(3y)}$ for $y$ years.
- `variance_ratio_1y` (dependence, **supplementary**): $\mathrm{VR}(q)$ with the
  i.i.d. standard error, z-statistic and two-sided p-value in details.
- `sharpe_ratio_autocorrelation_adjusted` (risk-adjusted): per-period Sharpe
  ratio of decision 0008 times $\eta(q)$; equal to the conventional Sharpe
  ratio when all $\hat\rho_k = 0$; `not_applicable` when
  $q\,\mathrm{VR}(q) \le 0$. Not flagged volatility-based: it is the correction
  for the bias that flag warns about.
- `profit_factor` (returns): $\sum_{r_t>0} r_t / |\sum_{r_t<0} r_t|$;
  `not_applicable` without a losing period.
- An interpretation note states both Sharpe ratios and the variance ratio.

## Rationale

Lo's adjustment is the established, reference-backed correction for exactly the
bias the confidence engine already warns about; reporting it next to the
unchanged conventional ratio shows the size of the bias instead of only naming
it. Using the same autocorrelation estimator as the lag-1–3 metrics keeps the
report internally consistent, and the autocorrelation form makes
$\eta(q) = \sqrt{q/\mathrm{VR}(q)}$ an identity, so the two new numbers cannot
disagree. A one-year horizon is the only choice that matches the annualized
figures; shorter horizons would not correct them. The minimum of two years and
the low/moderate thresholds reflect how noisy $q-1$ estimated autocorrelations
are; the adjustment is shown with reduced confidence rather than hidden.

## Consequences

- The adjusted Sharpe ratio can be higher than the conventional one when
  returns mean-revert ($\mathrm{VR} < 1$); the interpretation note says which.
- With daily data the adjustment uses 251 (or 364) autocorrelations; it is
  labelled low or moderate confidence unless the history is long.
- The profit factor duplicates the information in the gain-to-pain ratio
  (PF = 1 + GPR); both are reported because both are widely quoted.
