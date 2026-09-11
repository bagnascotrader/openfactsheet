# 0003 — Standard deviation: sample (n − 1) estimator

**Status:** Accepted — methodology 0.1.0

## Problem

Volatility can use the population (`1/n`) or sample (`1/(n-1)`) variance
denominator. The difference matters for short histories (about 9% at n = 6)
and propagates into Sharpe, tracking error and the Information ratio.

## Known definitions

- Population: `sqrt( (1/n) sum (r_t - m)^2 )`.
- Sample (Bessel-corrected): `sqrt( (1/(n-1)) sum (r_t - m)^2 )`.

## PerformanceAnalytics behavior

`StdDev` and `StdDev.annualized` use R `sd()`, the sample estimator.
`TrackingError` uses `sd.xts`, also sample. Verified: `volatility` and
`annualized_volatility` agree to 1e-9 on all fixtures.

## QuantStats behavior

Uses pandas `.std()`, sample by default (`ddof=1`). Its Sharpe ratio agrees
with OpenFactsheet to 1e-9 on all fixtures, which implies the same estimator.

## Empyrical behavior

`annual_volatility` uses `nanstd(ddof=1)`. Verified: agrees to 1e-9.

## Academic sources

- Bacon (2021), chapter on standard deviation.
- Sharpe (1994) uses the sample standard deviation of differential returns.

## OpenFactsheet decision

All standard deviations (volatility, annualized volatility, Sharpe denominator,
tracking error, Information ratio denominator) use `ddof = 1`
(`dispersion.ddof = 1` in the methodology). A single observation makes these
metrics `insufficient_data`.

Downside deviation is a different quantity (a lower partial moment) with a
full-sample `n` denominator; see [0006](0006-sortino-downside-deviation.md).

## Rationale

The sample estimator is unbiased for the variance, is the default in all
reference implementations, and makes results reproducible in Excel (`STDEV.S`).

## Consequences

- Zero variance makes volatility 0 and Sharpe `not_applicable` ("Volatility is
  zero; the Sharpe ratio is undefined.").
- Metric assumption strings state "Sample standard deviation (n - 1 denominator)."
