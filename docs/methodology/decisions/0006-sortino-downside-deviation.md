# 0006 — Sortino ratio and downside deviation: MAR 0, full-sample denominator

**Status:** Accepted — methodology 0.1.0

## Problem

Downside deviation has two free choices: the target (minimum acceptable return,
MAR) and the denominator (all observations or only those below the target).
Both change the Sortino ratio materially, and both could be tuned.

## Known definitions

- Full-sample: `DD = sqrt( (1/n) sum min(r_t - MAR, 0)^2 )` (Sortino & Price, 1994).
- Subset: `DD = sqrt( (1/k) sum_{r_t < MAR} (r_t - MAR)^2 )`, k = number of shortfalls.
- Sortino ratio: `(mean(r) - MAR) / DD`, annualized by `sqrt(P)` or reported per period.

## PerformanceAnalytics behavior

`DownsideDeviation(R, MAR = 0, method = c("full", "subset"))` defaults to
`"full"` (`len = length(R)`). `SortinoRatio(R, MAR = 0)` returns the per-period
`mean(R - MAR) / DownsideDeviation(R, MAR)`. Verified:
`downside_deviation = DownsideDeviation(full) * sqrt(12)` and
`sortino_ratio = SortinoRatio * sqrt(12)`, both to 1e-9.

## QuantStats behavior

`stats.sortino` uses `sqrt(sum(r[r < 0]^2) / n)` (full sample) and annualizes by
`sqrt(periods)` (reported in library docs, not verified here).

## Empyrical behavior

`downside_risk` uses the full-sample denominator and annualizes by `sqrt(P)`;
`sortino_ratio` = `mean(r - required) * P / downside_risk`. Verified: both agree
to 1e-9 on all fixtures.

## Academic sources

- Sortino, F. A., & Price, L. N. (1994). Performance Measurement in a Downside
  Risk Framework. *Journal of Investing* 3(3).
- Bacon (2021).

## OpenFactsheet decision

- MAR = 0% per period (`downside.mar = 0.0`).
- Full-sample denominator `n` (`downside.denominator = "full_sample"`).
- `downside_deviation` is reported annualized: `DD * sqrt(P)`.
- `sortino_ratio = mean(r) / DD * sqrt(P)` (equivalently `P * mean / (DD * sqrt(P))`).
- With no return below 0%, downside deviation is 0 and the Sortino ratio is
  `not_applicable` ("No returns below the 0% target...").

## Rationale

The full-sample denominator is the original definition and the default in all
three reference libraries. MAR = 0 matches the canonical zero risk-free rate
([0005](0005-risk-free-rate.md)) and avoids a per-fund target.

## Consequences

- Series with very few losses give unstable Sortino values; the metric's
  documentation says so, and it is volatility-based for smoothing warnings.
- A different MAR would be a methodology change, not a parameter.
