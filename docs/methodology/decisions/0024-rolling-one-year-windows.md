# 0024 — Rolling one-year windows

**Status:** Accepted — methodology 0.1.0

## Problem

Rolling statistics depend on the window length and step (CLAUDE.md §12.8:
rolling periods must come from canonical policy, never from the user). A chosen
window or start date could be tuned to flatter a fund.

## Known definitions

With window $w$ observations, the rolling compounded return ending at $t$ is

```math
R^{(w)}_t = \prod_{i=t-w+1}^{t} (1 + r_i) - 1, \qquad t = w, \dots, n
```

## PerformanceAnalytics behavior

`apply.rolling` / `zoo::rollapply` compute rolling functions with a caller-chosen
width. **Verified:** with width 12 on the monthly fixtures,
`rollapply(R, 12, function(x) prod(1 + x) - 1, align = "right")` (padding
removed) gives the same minimum, maximum, share of positive windows and number of
windows as OpenFactsheet, to 1e-9
(`tests/cross_library/test_performanceanalytics.py::test_phase2b_agreement`).

## QuantStats behavior

Rolling metrics with caller-chosen windows (reported in library docs, not
verified here).

## Empyrical behavior

`roll_*` functions with a caller-chosen window (reported in library docs, not
verified here).

## Academic sources

- Bacon, C. R. (2021). *Practical Risk-Adjusted Performance Measurement*.

## OpenFactsheet decision

- Window $w = \operatorname{round}(P \times 1)$ observations (`rolling.window_years
  = 1`): 12 monthly, 4 quarterly, 52 weekly, 252 business-daily, 365
  calendar-daily, 1 yearly. Step: one observation (`rolling.step_periods = 1`).
- Every start date is used; `best_rolling_year`, `worst_rolling_year` and
  `positive_rolling_year_pct` (a zero window counts as not positive) summarize
  all $n - w + 1$ windows. Details give the number of windows, $w$, and the end
  date of the best / worst window.
- $n < w$ → `not_applicable`. The metrics are flagged annualized (they need a
  regular frequency) and wealth-path; `path_risk` minimum-data policy.

## Rationale

A single, frequency-derived window with every start date leaves nothing to
choose: no favorable start date or window length can be selected.

## Consequences

- Windows overlap, so rolling statistics are strongly autocorrelated; they are
  descriptive, not probability estimates.
- Windows count observations, not calendar time: with missing periods a window
  spans more than one year (the gap warning of the confidence policy applies).
- The worst rolling year is typically worse than the worst calendar year
  ([0023](0023-calendar-year-statistics.md)).
