# 0008 — Sharpe ratio: arithmetic mean over sample volatility, square-root-of-time

**Status:** Accepted — methodology 0.1.0

## Problem

The "annualized Sharpe ratio" has at least two common forms: arithmetic mean
return over volatility scaled by `sqrt(P)`, and annualized geometric return over
annualized volatility. They can differ substantially for volatile series.

## Known definitions

- Ex-post Sharpe (Sharpe, 1994): `mean(r - rf) / std(r - rf)`, annualized by `sqrt(P)`.
- Geometric variant: `[(prod(1 + r - rf))^(P/n) - 1] / (std(r) * sqrt(P))`.

## PerformanceAnalytics behavior

`SharpeRatio.annualized(R, Rf, scale, geometric = TRUE)` by default divides the
**geometric** annualized excess return by `StdDev.annualized`. With
`geometric = FALSE` it computes `mean * scale / (sd * sqrt(scale))`. Verified:
OpenFactsheet equals the `geometric = FALSE` form to 1e-9 and differs from the
PA default on all fixtures.

## QuantStats behavior

`stats.sharpe(returns, rf = 0, periods = 252)` computes
`mean / std(ddof = 1) * sqrt(periods)`. Verified with `periods = 12`: agrees to 1e-9.

## Empyrical behavior

`sharpe_ratio(returns, period = "monthly")` computes `mean / std(ddof = 1) *
sqrt(P)`. Verified: agrees to 1e-9.

## Academic sources

- Sharpe, W. F. (1966). Mutual Fund Performance. *Journal of Business* 39(1).
- Sharpe, W. F. (1994). The Sharpe Ratio. *JPM* 21(1).
- Lo, A. W. (2002). The Statistics of Sharpe Ratios. *FAJ* 58(4).
- Getmansky, Lo & Makarov (2004). *JFE* 74(3).

## OpenFactsheet decision

`sharpe_ratio = mean(r) / std(r, ddof = 1) * sqrt(P)` with `rf = 0`
([0005](0005-risk-free-rate.md)), the canonical `P`
([0002](0002-annualization-and-frequency.md)) and sample standard deviation
([0003](0003-standard-deviation.md)).

- Zero volatility → `not_applicable`.
- Irregular/unknown frequency → `not_applicable` (it is an annualized metric).
- The metric is `volatility_based`: high smoothing risk forces confidence to
  `low`; moderate caps it at `moderate`; strongly non-normal returns add a
  warning ([0014](0014-smoothing-risk.md)).

## Rationale

This is Sharpe's own ex-post definition and the form shared by QuantStats and
empyrical. Using the arithmetic mean keeps the Sharpe, Information ratio,
active return and alpha conventions consistent with each other
([0012](0012-benchmark-alignment-and-relative-metrics.md)).

## Consequences

- Values differ from PerformanceAnalytics' default `SharpeRatio.annualized`.
  The cross-library test asserts the difference so that it cannot disappear
  silently.
- Confidence intervals, Probabilistic and Deflated Sharpe ratios are planned for
  a later methodology version.
