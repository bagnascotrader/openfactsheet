# 0012 — Benchmark alignment and benchmark-relative metrics

**Status:** Accepted — methodology 0.1.0

## Problem

Benchmark-relative metrics require pairing fund and benchmark returns period by
period. Date conventions differ (month-start vs month-end), histories overlap
only partly, and libraries annualize alpha, active return, Treynor and capture
ratios differently.

## Known definitions

- CAPM/Jensen regression: `r_fund = a + b * r_bench + e` (excess returns).
- Tracking error: `std(r_fund - r_bench) * sqrt(P)`.
- Information ratio: active return / tracking error (arithmetic or geometric
  active return).
- Treynor: annualized (excess) return / beta.
- Up/down capture: fund vs benchmark performance in benchmark up/down periods
  (Morningstar compounds returns geometrically).

## PerformanceAnalytics behavior

- `CAPM.beta`, `CAPM.alpha`: `lm` slope and per-period intercept on
  `na.omit(merge(...))`. Verified: beta and `alpha / 12` agree to 1e-9.
- `TrackingError`: `sd(Ra - Rb) * sqrt(scale)`. Verified.
- `InformationRatio` = `ActivePremium / TrackingError`, where `ActivePremium`
  is the difference of **geometric** annualized returns. Verified to differ from
  OpenFactsheet's arithmetic IR, which equals `mean(active) * 12 / (sd(active) *
  sqrt(12))` computed in R.
- `TreynorRatio` uses `Return.annualized` (geometric) / beta. Verified: PA's
  value equals the geometric annualized aligned fund return divided by beta,
  while OpenFactsheet's equals the arithmetic annualized mean divided by beta.
- `UpDownRatios(method = "Capture")` divides **sums** of returns; up periods are
  `Rb > 0`, down periods `Rb <= 0`. Verified: PA's up and down captures equal
  those sum ratios, and both differ from OpenFactsheet's geometric captures.

## QuantStats behavior

`stats.information_ratio` reports the non-annualized per-period ratio.
Verified: it equals OpenFactsheet's information ratio divided by sqrt(12).

## Empyrical behavior

`beta` agrees to 1e-9 (verified). `alpha` annualizes the intercept
geometrically, `(1 + a)^P - 1`; verified that empyrical equals
`(1 + alpha_OFS / 12)^12 - 1`. `up_capture` / `down_capture` compound returns in
up (`> 0`) / down (`< 0`) benchmark periods and annualize them; verified to 1e-9.

## Academic sources

- Jensen (1968), *JoF* 23(2); Treynor (1965), *HBR* 43(1).
- Grinold & Kahn (2000); Goodwin (1998), *FAJ* 54(4).
- Morningstar Upside/Downside Capture Ratio methodology.

## OpenFactsheet decision

**Alignment** (`compare/alignment.py`):
- Both dated: monthly/quarterly/yearly matched by **calendar period** (so
  month-start and month-end dates align), daily/weekly by exact date; only the
  intersection is used. Missing benchmark returns are **never filled**.
- The loss of observations is disclosed (`fund_only_periods`,
  `benchmark_only_periods`, overlap dates, coverage); coverage below 90% caps
  confidence at `moderate`.
- Different regular frequencies → `BenchmarkAlignmentError` (no resampling).
- Neither dated: paired by position only if lengths match; exactly one dated:
  lengths must match and the undated series is assumed to share the dates. Both
  cases add warnings; otherwise an error is raised.
- Benchmark metrics report the aligned observation count separately.

**Metrics** (rf = 0, [0005](0005-risk-free-rate.md)):
- `beta`, `alpha`: statsmodels OLS with intercept; `alpha = a * P` (arithmetic);
  details give per-period alpha, standard error, t and p (i.i.d. errors).
- `r_squared` (regression), `correlation` (Pearson).
- `tracking_error = std(active, ddof=1) * sqrt(P)`;
  `active_return = mean(active) * P`;
  `information_ratio = mean(active) / std(active) * sqrt(P)`.
- `treynor_ratio = mean(r_fund) * P / beta` on aligned periods; note added when
  beta < 0.3; beta = 0 → `not_applicable`.
- `upside_capture` / `downside_capture`: geometric annualized fund return over
  benchmark up (`> 0`) / down (`< 0`) periods divided by the same for the
  benchmark; zero-benchmark periods belong to neither.

## Rationale

Calendar-period alignment handles real-world date conventions without inventing
data. Arithmetic annualization keeps alpha, active return, IR and Sharpe
([0008](0008-sharpe-ratio.md)) mutually consistent. Geometric capture follows
the Morningstar convention investors see in fund documents.

## Consequences

- IR, active return, Treynor and capture values differ from PerformanceAnalytics;
  alpha differs from empyrical by the annualization method. The tests pin these
  relationships.
- A benchmark is never inferred; without one, all benchmark metrics are
  `not_applicable` with the reason stated.
