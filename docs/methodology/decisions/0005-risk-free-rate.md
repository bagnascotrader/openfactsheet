# 0005 — Risk-free rate: zero in methodology 0.1.0, always disclosed

**Status:** Accepted — methodology 0.1.0

## Problem

Excess-return metrics (Sharpe, Sortino, Calmar, Martin, alpha, Treynor) need a
risk-free rate. The correct rate depends on currency, period and investor, and
OpenFactsheet has no reliable, free, deterministic source keyed on metadata it
can trust. Choosing a rate per fund would also be a tuning knob.

## Known definitions

Sharpe (1994) defines the ratio on differential returns `r_t - rf_t`. Many
practitioners use a local T-bill or overnight rate; many libraries default to
`rf = 0`.

## PerformanceAnalytics behavior

`Rf = 0` default in `SharpeRatio`, `CAPM.alpha`, `CAPM.beta`, `TreynorRatio`,
`MartinRatio`. The fixtures were computed with `Rf = 0`.

## QuantStats behavior

`rf = 0.0` default in `sharpe`, `sortino` and related functions.

## Empyrical behavior

`risk_free = 0` default in `sharpe_ratio`, `alpha_beta`.

## Academic sources

- Sharpe, W. F. (1994). The Sharpe Ratio. *JPM* 21(1).

## OpenFactsheet decision

- `risk_free.rate = 0.0` per period for every excess-return metric in 0.1.0.
- Every affected metric carries the assumption: "Risk-free rate assumed to be 0%
  (methodology 0.1.0); the ratio therefore uses total rather than excess
  returns and is higher than an excess-return version when cash yields are
  positive."
- Regression-based metrics (beta, alpha, Treynor) regress total returns.
- The investor's currency is never inferred from the computer locale or any
  other ambient setting.
- There is no per-call override in the canonical API.

## Rationale

A disclosed zero is transparent and reproducible, and it matches the default of
every reference library, which makes cross-validation direct. A rate chosen
per fund could be used to improve presentation.

## Consequences

- In periods of positive cash yields, Sharpe-type ratios are overstated relative
  to excess-return versions; the report says so on each metric.
- Roadmap: an optional, deterministic public risk-free series selected from
  explicitly supplied currency metadata. Adding it will be a methodology
  version change, and overridden results will be labeled non-canonical.
