# 0023 — Calendar-year statistics: complete years only

**Status:** Accepted — methodology 0.1.0

## Problem

Best / worst calendar year and the share of positive years depend on how
partial years are treated (CLAUDE.md §41, "monthly table partial years"). A
partial first or last year — or a year with a missing month — is not a
calendar-year return, and including it would let the inception date shape the
statistics.

## Known definitions

A calendar-year return compounds the period returns of the year:

```math
R_y = \prod_{t \in y} (1 + r_t) - 1
```

GIPS requires annual returns for complete calendar years and prohibits
presenting partial periods as annual returns.

## PerformanceAnalytics behavior

`apply.yearly(R, Return.cumulative)` / `table.CalendarReturns` compound every
year present, including partial years. **Verified** on the monthly fixtures:
restricted to years with 12 monthly observations, the R values equal
OpenFactsheet's `calendar_year_returns` to 1e-9, and best / worst match
(`tests/cross_library/test_performanceanalytics.py::test_phase2b_agreement`).

## QuantStats behavior

Yearly aggregation of all years present (reported in library docs, not verified
here).

## Empyrical behavior

`aggregate_returns(..., "yearly")` compounds all years present (reported in
library docs, not verified here).

## Academic sources

- CFA Institute (2020). *GIPS Standards* — annual returns for complete calendar
  years.

## OpenFactsheet decision

A calendar year counts only when the observations cover it
(`MetricContext.calendar_years`; key `calendar_years` in `policy/defaults.py`):

| Frequency | Complete year |
|---|---|
| monthly | all 12 calendar months observed (a missing month makes it partial) |
| quarterly | all 4 calendar quarters observed |
| yearly | the year's observation |
| daily, weekly | first observation on or before 1 January + 7 days and last on or after 31 December − 7 days (`daily_weekly_edge_tolerance_days = 7`) |

- Each observation belongs to the calendar year of its (period-end) date.
- Partial years are listed in `details.excluded_partial_years` and in a warning
  ("Partial calendar years excluded: …") and never enter the statistics.
- `best_calendar_year`, `worst_calendar_year` and `positive_calendar_years_pct`
  (a zero year counts as not positive) use complete years only; details carry
  every complete year's return.
- Undated series, or an irregular / unknown frequency → `not_applicable`; no
  complete year → `not_applicable`, naming the partial years.
- Wealth-path metrics; `path_risk` minimum-data policy.

## Rationale

Complete years are objective and match GIPS. The 7-day tolerance for daily and
weekly data absorbs holidays and week-end dating without accepting a year that
is visibly missing weeks at either end.

## Consequences

- A history starting in July has its first calendar year excluded; it still
  contributes to every full-history metric.
- For weekly data a week straddling 31 December is assigned to the year of its
  end date, so calendar-year returns are approximate at the boundary.
- Quarterly and daily rules are covered by unit tests
  (`tests/unit/metrics/test_phase2b.py`); only monthly years are compared with R.
