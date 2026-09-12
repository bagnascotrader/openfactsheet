# 0025 — Episode durations, recovery factor and path summaries

**Status:** Accepted — methodology 0.1.0

## Problem

Duration statistics must say how open (unrecovered) episodes are treated;
recovery factor has competing numerators; the geometric mean and interquartile
range need a stated estimator.

## Known definitions

For episodes $k = 1..K$ with peak $\pi_k$, trough $\tau_k$ (first minimum),
recovery $\rho_k$ and depth $\delta_k$ ([0007](0007-drawdown-conventions.md)):

```math
\ell_k = \begin{cases} \rho_k - \pi_k & \text{recovered} \\ n - \pi_k & \text{open} \end{cases},
\qquad
\mathrm{RF} = \frac{W_n - 1}{|\mathrm{MDD}|}, \qquad
\bar r_g = W_n^{1/n} - 1
```

## PerformanceAnalytics behavior

`findDrawdowns` returns per-episode `return`, `length`, `peaktotrough` and
`recovery`. It counts an episode still open at the end of the data one period
longer (`length` and `recovery`). **Verified:** after that +1 adjustment, the
median depth, mean length, maximum peak-to-trough and mean recovery (recovered
episodes only) equal OpenFactsheet's values to 1e-9; when the only episode is
open, `average_recovery_duration` is asserted `not_applicable`. `mean.geometric`
equals `geometric_mean_return` and R `IQR` (type 7) equals
`interquartile_range` (`test_phase2b_agreement`).

## QuantStats behavior

`stats.recovery_factor` divides the **arithmetic sum** of returns by the
absolute maximum drawdown. **Verified** to differ from OpenFactsheet
(`test_quantstats_recovery_factor_uses_arithmetic_sum`).

## Empyrical behavior

None of these statistics are compared.

## Academic sources

- Bacon, C. R. (2021). *Practical Risk-Adjusted Performance Measurement*.
- Hyndman, R. J., & Fan, Y. (1996). Sample Quantiles in Statistical Packages.

## OpenFactsheet decision

- `median_drawdown`: median of episode depths, signed; 0 when $K = 0$.
- `average_drawdown_duration`: mean $\ell_k$ over **all** episodes, open ones
  measured to the last observation; a note flags the result as a lower bound
  when an episode is open; 0 when $K = 0$.
- `max_peak_to_trough_duration`: $\max_k(\tau_k - \pi_k)$; 0 when $K = 0$.
- `average_recovery_duration`: mean $\rho_k - \tau_k$ over **recovered**
  episodes only; open episodes are excluded and counted in details;
  `not_applicable` when no episode has recovered.
- `recovery_factor`: compounded cumulative return $/ |\mathrm{MDD}|$, not
  annualized; `not_applicable` when MDD = 0.
- `geometric_mean_return`: $W_n^{1/n} - 1$ per period ($-1$ after a total loss).
- `interquartile_range`: $Q_{0.75} - Q_{0.25}$ with linear interpolation, per
  period (volatility-based).
- Durations are in observation periods; details add years when $P$ is known.

## Rationale

Open episodes have a known lower bound on duration but no recovery time, so the
two averages treat them differently and say so. The compounded numerator of the
recovery factor is the investor's actual net gain.

## Consequences

- Average duration can rise as an open drawdown lengthens; the note makes this
  visible.
- The recovery factor grows with track-record length; compare only equal
  histories.
