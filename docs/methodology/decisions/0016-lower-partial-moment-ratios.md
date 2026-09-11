# 0016 — Lower-partial-moment ratios and dispersion: target 0, full-sample denominators

**Status:** Accepted — methodology 0.1.0

## Problem

Kappa 3, the upside potential ratio, downside potential (LPM1), semi-deviation
and mean absolute deviation all need a target and a denominator, and each can
be reported per period or annualized. Every one of these choices changes the
numbers, so each has to be fixed canonically rather than left to the user.

## Known definitions

Lower and upper partial moments of order $k$ at target $\tau$:

```math
\mathrm{LPM}_k(\tau) = \frac{1}{n}\sum_{t=1}^{n} \max(\tau - r_t, 0)^k, \qquad
\mathrm{UPM}_k(\tau) = \frac{1}{n}\sum_{t=1}^{n} \max(r_t - \tau, 0)^k
```

- Kappa of order $k$ (Kaplan & Knowles, 2004):
  $K_k = (\bar r - \tau) / \mathrm{LPM}_k(\tau)^{1/k}$. The Sortino ratio is
  Kappa 2, and Omega − 1 is Kappa 1.
- Upside potential ratio (Sortino, van der Meer & Plantinga, 1999):
  $\mathrm{UPM}_1(\tau) / \sqrt{\mathrm{LPM}_2(\tau)}$.
- Semi-deviation: the downside deviation with the sample mean as target. Some
  sources divide by the number of below-mean periods instead of by $n$.
- Mean absolute deviation: $\frac{1}{n}\sum |r_t - \bar r|$.

## PerformanceAnalytics behavior

- `Kappa(R, MAR, l)` = `(mean(R) − MAR) / ((1/n) Σ_{r<MAR} (MAR − r)^l)^(1/l)`,
  per period. **Verified:** `kappa_3_ratio` = `Kappa(MAR=0, l=3)`.
- `UpsidePotentialRatio(R, MAR = 0, method = c("subset", "full"))` defaults to
  `"subset"`, which divides by the number of gains and of losses. **Verified:**
  OpenFactsheet equals `method = "full"` and differs from the default (the
  difference is pinned by a test).
- `SemiDeviation(R)` = `DownsideDeviation(R, MAR = mean(R), method = "full")`,
  per period. **Verified:** `semi_deviation` = `SemiDeviation × sqrt(12)`.
- `DownsideDeviation(R, MAR = 0, potential = TRUE)` = `Σ_{r<0} (0 − r) / n`.
  **Verified** equal to `downside_potential`.
- `MeanAbsoluteDeviation(R)` = `Σ |R − mean(R)| / n`. **Verified.**

## QuantStats behavior

No equivalents are used as references here.

## Empyrical behavior

No equivalents are used as references here.

## Academic sources

- Kaplan, P. D., & Knowles, J. A. (2004). Kappa: A Generalized Downside
  Risk-Adjusted Performance Measure. *Journal of Performance Measurement* 8(3).
- Sortino, F. A., van der Meer, R., & Plantinga, A. (1999). The Dutch Triangle.
  *Journal of Portfolio Management* 26(1).
- Sortino & Price (1994); Bacon (2021).

## OpenFactsheet decision

- Target $\tau = 0$ per period (`lower_partial_moments.target`), the same as the
  Sortino target ([0006](0006-sortino-downside-deviation.md)); Kappa order 3
  (`lower_partial_moments.kappa_order`).
- All partial moments divide by all $n$ observations
  (`lower_partial_moments.denominator = "full_sample"`).
- `kappa_3_ratio`, `upside_potential_ratio`, `downside_potential` and
  `mean_absolute_deviation` are **per period** (not annualized).
- `semi_deviation` uses the sample mean as target and the $n$ denominator, and
  is **annualized** by $\sqrt{P}$ like `downside_deviation`:

```math
\mathrm{SemiDev}_{\text{ann}} = \sqrt{P}\,\sqrt{\frac{1}{n}\sum_{t=1}^{n}\min(r_t - \bar r, 0)^2}
```

- Kappa 3 and the upside potential ratio are `not_applicable` when no return is
  below 0% (zero denominator).
- Kappa 3, the upside potential ratio, semi-deviation and MAD are
  volatility-based, so smoothing and stale-price diagnostics lower their
  confidence. Downside potential is not.

## Rationale

The full-sample denominator is the original definition and matches Sortino
and Omega, so these measures stay mutually consistent (Omega = 1 + mean / LPM1
at threshold 0). No convention exists for annualizing Kappa 3 or the upside
potential ratio, so they are reported per period, like Omega. Semi-deviation
is a volatility-type quantity and is annualized like the other deviations.

## Consequences

- The upside potential ratio differs from PerformanceAnalytics' default output.
  The difference is documented and pinned.
- Per-period ratios are not comparable across data frequencies; the metric
  documentation says so.
