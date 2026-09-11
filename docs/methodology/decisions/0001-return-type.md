# 0001 — Return type: simple decimal returns

**Status:** Accepted — methodology 0.1.0

## Problem

Return histories arrive as simple returns, log returns, percentages, decimals,
or price/NAV levels. Mixing conventions silently changes every downstream
statistic (compounding, drawdowns, moments). One internal representation is
required.

## Known definitions

- Simple (arithmetic) return: `r_t = P_t / P_(t-1) - 1`. Compounds by
  multiplication: `W_t = prod(1 + r_i)`.
- Log return: `l_t = ln(P_t / P_(t-1)) = ln(1 + r_t)`. Adds over time but does
  not aggregate across assets and is not what fund factsheets report.

## PerformanceAnalytics behavior

Assumes simple returns by default (`Return.cumulative(geometric = TRUE)` uses
`prod(1 + R) - 1`). Some functions accept a `geometric` switch. Values are
expected as decimals; `DrawdownPeak` (used by `UlcerIndex`/`PainIndex`) divides
returns by 100, i.e. it assumes percent inputs (see [0007](0007-drawdown-conventions.md)).

## QuantStats behavior

Works on simple decimal returns in a pandas Series; compounding uses
`(1 + r).prod() - 1`.

## Empyrical behavior

Simple decimal returns; `cum_returns_final` compounds `prod(1 + r) - 1`.

## Academic sources

- Bacon, C. R. (2021). *Practical Risk-Adjusted Performance Measurement* (2nd ed.).
- CFA Institute (2020). GIPS — time-weighted returns are geometrically linked
  simple returns.

## OpenFactsheet decision

- Internally every series is a read-only `float64` array of **simple decimal
  returns** (`0.01` = +1%). `return_type` is always `"simple"` in 0.1.0.
- Percent inputs are converted by dividing by 100, recorded as a
  transformation (scale detection: [0013](0013-return-scale-detection.md)).
- Log returns are not accepted as a separate type in 0.1.0.
- Price/NAV levels are detected as implausible return values and rejected with a
  message asking for explicit conversion `r_t = P_t / P_(t-1) - 1`.
- Values below -100% are kept (never clipped) and flagged as impossible;
  wealth-path metrics become `not_applicable`.
- A -100% return (total loss) is valid: wealth is zero from that period and
  cannot be rebuilt by later returns.

## Rationale

Simple returns are what funds report and what investors experience when
compounding. One representation removes a whole class of silent mixing errors.

## Consequences

- `ReturnSeries.values` is always decimal simple returns; the report exposes
  them exactly (`report.returns_frame()` and the `returns` block of the JSON).
- A price-to-returns conversion helper with provenance is future work.
