# 0004 — Annual return: geometric CAGR by observation count

**Status:** Accepted — methodology 0.1.0

## Problem

"Annualized return" can mean the compound annual growth rate or the arithmetic
mean times periods per year. The two differ by roughly half the variance, and
CAGR itself can be computed from observation counts or calendar time.

## Known definitions

- Geometric (CAGR): `(prod(1 + r_t))^(P / n) - 1`.
- Arithmetic: `P * mean(r_t)`.
- Calendar-time CAGR: `(W_end / W_start)^(365.25 / days) - 1`.

## PerformanceAnalytics behavior

`Return.annualized(geometric = TRUE)` computes `prod(1 + R)^(scale / n) - 1`;
`geometric = FALSE` computes `mean(R) * scale`. Verified: `cagr` and
`annualized_arithmetic_mean` agree to 1e-9 on all fixtures.

## QuantStats behavior

`stats.cagr(returns, periods=...)` uses a `periods` argument whose default
assumes daily observations. Verified on the monthly fixture: with the default it
returns 93.75% (each month treated as a trading day); with `periods=12` it
agrees with OpenFactsheet to 1e-9. OpenFactsheet never takes an annualization
factor from the caller; it is established from the dates.

## Empyrical behavior

`annual_return` computes `ending_value^(1 / (n / P)) - 1`, the same as
observation-count CAGR. Verified: agrees to 1e-9.

## Academic sources

- Bacon (2021).
- CFA Institute (2020). GIPS: annualized returns are geometric; returns for
  periods shorter than one year must not be annualized.

## OpenFactsheet decision

- `cagr` = `(prod(1 + r))^(P / n) - 1`, using the canonical `P` from
  [0002](0002-annualization-and-frequency.md) and the number of observations `n`.
- `annualized_arithmetic_mean` = `P * mean(r)` is reported separately; it is
  the return component of the canonical Sharpe ratio ([0008](0008-sharpe-ratio.md)).
- If wealth reaches zero or below, CAGR is reported as -100%.
- **Less than one year of data:** annualized metrics are still computed (the
  value is mathematically valid) but confidence is forced to `low`, with the
  warning "Annualized from only X years of data; the figure extrapolates a
  partial year." The interpretation of `cagr` and `annualized_arithmetic_mean`
  cites the GIPS rule ([0015](0015-minimum-data-policy.md)).

## Rationale

Observation count ties annualization to the detected frequency and removes
ambiguity about whether the first period's start date is known. Reporting both
geometric and arithmetic figures prevents choosing the more attractive one.

## Consequences

- Differences against QuantStats `cagr` are expected when calendar span and
  `n / P` differ.
- Missing periods shorten `n` and are disclosed; confidence is capped at
  `moderate` for annualized and wealth-path metrics when gaps exist.
