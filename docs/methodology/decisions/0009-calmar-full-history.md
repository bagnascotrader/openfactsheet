# 0009 — Calmar ratio over the full history

**Status:** Accepted — methodology 0.1.0

## Problem

Young (1991) defined the Calmar ratio on a trailing 36-month window. Others use
the full history, and some use the arithmetic rather than geometric return. A
window choice is exactly the kind of period selection that can flatter results.

## Known definitions

- Young (1991): annualized return over the last 36 months divided by the maximum
  drawdown over the same window.
- MAR ratio: the same quantity over the full history.

## PerformanceAnalytics behavior

`CalmarRatio(R, scale)` = `Return.annualized(R, scale) / abs(maxDrawdown(R))`
over whatever series is supplied (full history, geometric return). Verified:
agrees to 1e-9 on all fixtures.

## QuantStats behavior

`stats.calmar` divides its default CAGR (which assumes daily observations, see
[0004](0004-annual-return.md)) by the absolute maximum drawdown. Verified:
`calmar == cagr_default / |max drawdown|`, so on monthly data it differs from
OpenFactsheet unless the CAGR frequency is corrected.

## Empyrical behavior

`calmar_ratio(returns, period)` = `annual_return / abs(max_drawdown)` over the
supplied series. Verified: agrees to 1e-9.

## Academic sources

- Young, T. W. (1991). Calmar Ratio: A Smoother Tool. *Futures* 20(1).
- Bacon (2021).

## OpenFactsheet decision

`calmar_ratio = cagr / |max_drawdown|` over the **full supplied history**, using
the canonical CAGR and signed maximum drawdown
([0007](0007-drawdown-conventions.md)).

- No drawdown (maximum drawdown 0) → `not_applicable` (zero divisor).
- Annualized metric: not applicable without a regular frequency.
- `martin_ratio = cagr / ulcer_index` follows the same full-history rule.

## Rationale

The full history is the only window that requires no choice. Trailing windows
may be added later as separately identified, objectively defined statistics,
never as a replacement.

## Consequences

- OpenFactsheet's "Calmar" is, strictly, Young's MAR ratio; the metric
  documentation says so.
- Values fall as track records lengthen because maximum drawdown grows with
  history; comparisons across different history lengths are flagged by
  `compare()`.
