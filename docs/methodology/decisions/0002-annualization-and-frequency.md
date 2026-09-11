# 0002 — Frequency inference and annualization factors

**Status:** Accepted — methodology 0.1.0

## Problem

Annualized statistics need a periods-per-year factor `P`. Guessing it (for
example "many observations, so daily, so 252") can mis-scale volatility by
large factors. The factor must come from evidence and be disclosed.

## Known definitions

Conventional factors: daily 252 (trading days) or 365 (calendar days),
weekly 52, monthly 12, quarterly 4, yearly 1. Volatility scales with `sqrt(P)`,
arithmetic means with `P`, geometric returns via `(prod(1 + r))^(P/n) - 1`.

## PerformanceAnalytics behavior

`periodicity()` (xts) classifies the index; functions map daily → 252,
weekly → 52, monthly → 12, quarterly → 4, yearly → 1 (seen in
`Return.annualized`, `StdDev.annualized`, `SharpeRatio.annualized`,
`CalmarRatio`). There is no 365 option without an explicit `scale`.

## QuantStats behavior

Defaults to `periods=252`, overridable by argument; frequency is not inferred
for most statistics (reported in library docs, not verified here).

## Empyrical behavior

The caller passes `period="daily" | "weekly" | "monthly" | ...` or
`annualization=`; the default is daily (252). No inference.

## Academic sources

- Lo, A. W. (2002). The Statistics of Sharpe Ratios. *FAJ* 58(4) — square-root-of-time
  scaling assumes serially uncorrelated returns.

## OpenFactsheet decision

Frequency is inferred from **calendar spacing only** (`normalization/frequency.py`):

| Median gap between dates | Candidate | Regularity test |
|---|---|---|
| 25–35 days | monthly | calendar-month steps; >= 50% exactly one month, none zero |
| 80–100 days | quarterly | calendar-quarter steps, same rule |
| 300–400 days | yearly | calendar-year steps, same rule |
| 5–9 days | weekly | every gap a multiple of 7 days (±1), same rule |
| <= 4 days | daily | >= 80% of gaps <= 4 days |
| anything else | irregular | — |

- Steps larger than one period are gaps: counted as missing expected periods and
  disclosed. Two observations in the same calendar period → irregular.
- Inference uses the full date grid, including dates whose value is missing, so
  a NaN row is a missing observation, not irregular spacing.
- Daily: weekend observations present → calendar-day series, `P = 365`, missing
  days counted; otherwise business-day series, `P = 252`, missing days *not*
  counted (holidays are legitimate), gaps longer than 7 days reported.
- Canonical factors: daily 252/365, weekly 52, monthly 12, quarterly 4, yearly 1
  (`policy/defaults.py`).
- **Irregular or unknown frequency is never annualized**: annualized metrics are
  `not_applicable` with a reason. Undated input has `UNKNOWN` frequency.
- The caller may *declare* the frequency of undated values
  (`frequency="monthly"`). With dates, a declaration must match the inferred
  frequency or a `FrequencyInferenceError` is raised. Declared daily without
  dates assumes 252 and says so. Declarations are recorded and warned on every
  annualized metric.
- The number of observations is never evidence of frequency.

## Rationale

Calendar spacing is objective and reproducible. Refusing to annualize irregular
data is "approximately right" rather than precisely wrong.

## Consequences

- Every annualized metric carries an assumption string such as "Annualized with
  12 periods per year (monthly frequency, inferred from dates)."
- Crypto and other 7-day markets get 365 automatically when weekends appear.
- Resampling between frequencies is not performed in 0.1.0.
