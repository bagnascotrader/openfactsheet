# 0017 — Drawdown-based ratios: Burke, Sterling, Pain; payoff ratio

**Status:** Accepted — methodology 0.1.0

## Problem

Burke, Sterling and Pain ratios each divide an annualized return by a
drawdown statistic. The literature does not agree on which drawdowns to use
(episodes, runs of losing periods, averages of annual maxima), and the Sterling
ratio adds an arbitrary 10%. The payoff ratio needs a rule for zero returns.

## Known definitions

- **Burke** (Burke, 1994): $(r_p - r_f) / \sqrt{\sum_k D_k^2}$ over drawdowns $D_k$.
- **Sterling:** originally the average of annual maximum drawdowns minus 10%;
  the variant popularized by Kestner (1996) and Bacon is annualized return
  divided by (|max drawdown| + 10%).
- **Pain ratio** (Zephyr; see Bacon): $(r_p - r_f) / \text{Pain Index}$.
- **Payoff ratio:** average winning period / |average losing period|.

## PerformanceAnalytics behavior

- `BurkeRatio(R)` builds "drawdowns" from runs of consecutive negative returns,
  not from peak-to-recovery episodes, and multiplies returns by 0.01 (it
  assumes percent inputs). **Verified to differ.** OpenFactsheet agrees with
  `CAGR / sqrt(sum(depths^2))`, where the depths come from PA's own
  `findDrawdowns(R)$return < 0`.
- `SterlingRatio(R, excess = 0.1)` = `Return.annualized / |maxDrawdown + 0.1|`,
  where `maxDrawdown` is a positive magnitude. **Verified equal** to
  `sterling_ratio`.
- `PainRatio(R)` divides by `PainIndex`, which inherits the `DrawdownPeak`
  percent-input issue ([0007](0007-drawdown-conventions.md)). OpenFactsheet
  agrees with `CAGR / mean(abs(Drawdowns(R)))` (**verified**).

## QuantStats behavior

`stats.payoff_ratio` = mean of positive returns / |mean of negative returns|.
**Verified equal** to `payoff_ratio` on all fixtures.

## Empyrical behavior

No equivalents are used as references here.

## Academic sources

- Burke, G. (1994). A Sharper Sharpe Ratio. *Futures* 23(3).
- Kestner, L. N. (1996). Getting a Handle on True Performance. *Futures* 25(1).
- Bacon, C. R. (2021). *Practical Risk-Adjusted Performance Measurement*.

## OpenFactsheet decision

All three drawdown ratios use the geometric CAGR, $r_f = 0$, the full history,
and the canonical drawdown engine ([0007](0007-drawdown-conventions.md)), with
episode depths $\delta_k = \min_{t \in E_k} D_t$:

```math
\mathrm{Burke} = \frac{\mathrm{CAGR}}{\sqrt{\sum_{k=1}^{K}\delta_k^2}}, \qquad
\mathrm{Sterling} = \frac{\mathrm{CAGR}}{|\mathrm{MDD}| + 0.10}, \qquad
\mathrm{PR} = \frac{\mathrm{CAGR}}{\mathrm{PI}}
```

- The Sterling adjustment is `sterling.excess = 0.10` and is disclosed on every
  result as a convention, not an estimate.
- Burke and the Pain ratio are `not_applicable` when no drawdown occurred.
  Sterling is always defined, because its denominator is at least 0.10.
- Payoff ratio: arithmetic means of strictly positive and strictly negative
  periods. Zero returns are excluded from both. It is `not_applicable` without
  at least one gain and one loss.

## Rationale

One episode engine keeps Burke consistent with maximum drawdown, the Ulcer
Index and the Pain Index. Sterling follows the most widely implemented variant
(PA/Bacon), which needs no choice of calendar window. The alternative, an
average of annual maximum drawdowns, would require a partial-year rule and is
left out.

## Consequences

- Burke values differ from PerformanceAnalytics' `BurkeRatio`; the difference
  is pinned by a test.
- Sterling values are not comparable with Sterling ratios computed from
  averaged annual drawdowns.
