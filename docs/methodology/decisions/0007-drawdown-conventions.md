# 0007 — Drawdown conventions

**Status:** Accepted — methodology 0.1.0

## Problem

Drawdown statistics depend on whether the starting capital counts as a peak,
on the sign convention, on how episodes are delimited, and on how durations are
counted. Reconstructing drawdowns separately inside each ratio invites
inconsistency.

## Known definitions

`W_t = W_0 * prod_{i<=t}(1 + r_i)`, `D_t = W_t / max_{s<=t} W_s - 1`.
Maximum drawdown `min D_t`; Ulcer Index `sqrt(mean(D_t^2))` (Martin & McCann,
1989); Pain Index `mean(|D_t|)` (Bacon); average drawdown either per episode or
per period.

## PerformanceAnalytics behavior

- `Drawdowns` computes `cumprod(1 + R) / cummax(c(1, cumprod(1 + R)))[-1] - 1`,
  i.e. the initial value 1 counts as a peak. `maxDrawdown` reports a positive
  magnitude; `AverageDrawdown` averages episode depths from `findDrawdowns`.
  Verified: `max_drawdown` and `average_drawdown` equal the negated PA values
  to 1e-9.
- `UlcerIndex` and `PainIndex` use `DrawdownPeak`, which divides returns by 100
  (a percent-input assumption). On decimal inputs they do not match the
  textbook formula. Verified instead: OpenFactsheet `ulcer_index` and
  `pain_index` equal `sqrt(mean(Drawdowns(R)^2))` and `mean(|Drawdowns(R)|)`.
  `MartinRatio` inherits the issue; OpenFactsheet `martin_ratio` equals
  `Return.annualized / sqrt(mean(Drawdowns(R)^2))`.
- `findDrawdowns` `length` equals OpenFactsheet duration for recovered episodes
  and is one period longer for an episode still open at the end of the data
  (verified on all fixtures).

## QuantStats behavior

`stats.max_drawdown` returns a signed value. Verified: agrees to 1e-9 on all
fixtures.

## Empyrical behavior

`max_drawdown` returns a signed value. Verified: agrees to 1e-9 on all fixtures.

## Academic sources

- Magdon-Ismail, M., & Atiya, A. (2004). Maximum Drawdown. *Risk* 17(10).
- Martin & McCann (1989); Bacon (2021).

## OpenFactsheet decision

- One engine (`metrics/path.py`): `W_0 = 1` precedes the first return and is the
  first peak, so a first-period loss is a drawdown.
- Drawdowns and depths are **signed** (negative = loss). Ulcer and Pain indices
  are non-negative magnitudes, as their originators define them.
- An episode starts at the last peak before wealth falls below it and ends at
  the first period in which wealth regains that peak (recovery). If it never
  recovers it is *ongoing* and runs to the last observation. Every decline below
  a prior peak is an episode, however small.
- Duration = periods from peak to recovery (`recovery - peak`); ongoing:
  `n - peak`, flagged as a lower bound.
- Average drawdown = mean of episode depths; 0 when no drawdown occurred.
- Time under water, Ulcer and Pain are computed over observations 1..n (the
  inception point is excluded).
- Returns below -100% make every wealth-path metric `not_applicable`.

## Rationale

Counting the initial capital as a peak reflects the investor's experience from
inception. One engine guarantees that every drawdown metric describes the same path.

## Consequences

- PA's `UlcerIndex`, `PainIndex` and `MartinRatio` values differ from
  OpenFactsheet on decimal data; this is a PA input-convention issue, documented
  in [reference implementations](../../validation/reference_implementations.md).
- Drawdown statistics grow with history length; path metrics use the
  `path_risk` minimum-data policy ([0015](0015-minimum-data-policy.md)).
