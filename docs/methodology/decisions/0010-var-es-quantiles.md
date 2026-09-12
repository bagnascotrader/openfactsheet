# 0010 — Historical VaR, Expected Shortfall and tail ratio

**Status:** Accepted — methodology 0.1.0

## Problem

Tail measures depend on the confidence level, on the estimator (historical,
parametric, Cornish-Fisher), on the empirical quantile definition (there are
nine common ones), on how ties at the quantile are handled, and on the sign
convention. A marketer could pick any of these to shrink reported losses.

## Known definitions

- Historical VaR at level `c`: the `1 - c` empirical quantile of returns.
- Historical ES: mean of returns at or beyond that quantile.
- Hyndman & Fan (1996) type 7: linear interpolation between order statistics
  (R and NumPy default).
- Tail ratio: `|Q_0.95| / |Q_0.05|`.

## PerformanceAnalytics behavior

`VaR.historical` returns `-quantile(r, 0.05)` (type 7); the public
`VaR(p = 0.95, method = "historical")` returns a negative number. `ES.historical`
averages `r[r < q]` (strictly below the quantile) and falls back to VaR when that
set is empty. Verified: `var_historical_95` and
`expected_shortfall_historical_95` agree to 1e-9 on all fixtures (no fixture
has a return exactly equal to the quantile).

## QuantStats behavior

`stats.value_at_risk` is parametric: verified equal to the normal 5% quantile
with the sample mean and sample standard deviation, and different from the
historical VaR. `stats.cvar` conditions on that parametric threshold (function
behavior observed, not asserted). `stats.tail_ratio` agrees with OpenFactsheet
to 1e-9 on all fixtures (verified).

## Empyrical behavior

`tail_ratio` = `|percentile 95| / |percentile 5|`; verified to 1e-9.
`conditional_value_at_risk` averages returns at or below the 5th percentile
(reported in library docs, not verified here).

## Academic sources

- Jorion, P. (2006). *Value at Risk* (3rd ed.).
- Acerbi, C., & Tasche, D. (2002). On the Coherence of Expected Shortfall. *JBF* 26(7).
- Hyndman, R. J., & Fan, Y. (1996). Sample Quantiles in Statistical Packages.

## OpenFactsheet decision

- Confidence level 95% for VaR and ES (`tail.var_confidence`,
  `tail.es_confidence`); not user-selectable in the canonical report.
- Historical (empirical) estimator only in 0.1.0; parametric and modified VaR
  are future supplementary metrics.
- Quantile: linear interpolation (`numpy.quantile(method="linear")`, R type 7).
- `var_historical_95 = Q_0.05(r)`; `expected_shortfall_historical_95 =
  mean(r[r <= Q_0.05])`. The `<=` rule guarantees a non-empty tail; it differs
  from PA only when an observation equals the quantile exactly.
- Both reported as **signed per-period returns** (negative = loss), consistent
  with drawdowns ([0007](0007-drawdown-conventions.md)).
- `tail_ratio = |Q_0.95| / |Q_0.05|`; `not_applicable` when `Q_0.05 = 0`.

## Rationale

Historical estimates need no distributional assumption. Type 7 is the default of
R and NumPy, so results reproduce in both. A fixed level prevents confidence
shopping.

## Consequences

- With monthly data a 95% tail estimate rests on about `n/20` points; the `tail`
  minimum-data policy marks estimates `low` confidence below 5 expected tail
  observations (n < 100) and `moderate` below 10 (n < 200)
  ([0015](0015-minimum-data-policy.md)).
- Values are per observation period, not annualized or horizon-scaled.
- The same estimators are applied to the drawdown path for Drawdown-at-Risk and
  CDaR ([0021](0021-drawdown-tail-and-entropic-measures.md)).
