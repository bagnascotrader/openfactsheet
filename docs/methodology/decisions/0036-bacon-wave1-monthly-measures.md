# 0036 — Bacon Wave 1: mean difference, shape ratios and the bias ratio

**Status:** Accepted — methodology 0.1.0 (adds five metrics; no existing value,
status or convention changes)

## Problem

Bacon's *Practical Risk-Adjusted Performance Measurement* (2nd ed.) defines
several measures that need nothing beyond the periodic return series and were
not in the catalog: Gini's mean difference and its relative form (ch. 2), the
skewness-kurtosis ratio (ch. 3), volatility skewness (ch. 6) and the bias ratio
(ch. 10). Each has an estimator choice that must be fixed: the pair
denominator of the mean difference, the sign of the mean in the relative form,
which skewness and kurtosis estimators enter the ratio, how the bias ratio
treats a zero return and the ±s bounds, and the target and denominators of the
partial moments.

The source audit (`docs/audits/bacon_wave1_monthly_gap_audit.md`) found none of
the five in the registry, under any name or formula, and no registered metric
from which any of them follows by a monotonic transform.

The printed book was not available in the workspace; the formulas below are
those of the implementation brief, which quotes Bacon's equations (2.8), (2.9),
(3.7), (6.32) and (10.17). Ambiguities are listed under *Consequences*.

## Known definitions

With returns $r_1..r_n$, order statistics $r_{(1)} \le \dots \le r_{(n)}$, mean
$\bar r$, sample standard deviation $s$ (decision 0003) and target $\tau = 0$
(decision 0016):

```math
\mathrm{MD} = \frac{1}{n(n-1)} \sum_{i \ne j} |r_i - r_j|
            = \frac{2}{n(n-1)} \sum_{k=1}^{n} (2k-n-1)\, r_{(k)},
\qquad
\mathrm{RMD} = \frac{\mathrm{MD}}{\bar r}
```

```math
\mathrm{SKR} = \frac{G_1}{G_2 + 3},
\qquad
\mathrm{VS} = \frac{\mathrm{UPM}_2(\tau)}{\mathrm{LPM}_2(\tau)}
            = \frac{\frac1n\sum \max(r_t-\tau,0)^2}{\frac1n\sum \max(\tau-r_t,0)^2},
\qquad
\mathrm{BR} = \frac{\#\{t: 0 \le r_t \le s\}}{1 + \#\{t: -s \le r_t \le 0\}}
```

- **Mean difference.** Bacon's eq. (2.8) averages over the $n(n-1)$ ordered
  pairs $i \ne j$ (the unbiased U-statistic). Some texts divide by $n^2$
  (including the zero self-pairs); that variant is smaller by $(n-1)/n$.
- **Relative mean difference.** Eq. (2.9) divides by the arithmetic mean. In
  inequality measurement the mean is positive by construction; for returns it
  can be zero or negative.
- **Skewness-kurtosis ratio.** Eq. (3.7) (Watanabe 2006) divides skewness by
  kurtosis — Pearson, non-excess kurtosis — not by excess kurtosis. Bacon's
  moments are population moments.
- **Volatility skewness.** Eq. (6.32) is the ratio of the second upper and lower
  partial moments, without square roots. Bacon's *variability skewness* (p. 131)
  is its square root. The expression
  $(\sqrt{\mathrm{UPM}_2}-\sqrt{\mathrm{LPM}_2})/(\sqrt{\mathrm{UPM}_2}+\sqrt{\mathrm{LPM}_2})$
  is a different statistic and is not eq. (6.32).
- **Bias ratio.** Eq. (10.17) (Abdulali 2006) uses closed intervals on both
  sides, so a return of exactly zero falls in both the numerator and the
  denominator, and returns equal to $\pm s$ count.

## PerformanceAnalytics behavior

- `VolatilitySkewness(R, MAR = 0, stat = "volatility")` =
  `UpsideRisk(R, MAR, stat = "variance") / DownsideDeviation(R, MAR)^2`, both
  with the full-sample denominator. **Verified:** equals `volatility_skewness`
  to 1e-9 on the three single-series fixtures. Its `stat = "variability"` is the
  square root (variability skewness).
- `SkewnessKurtosisRatio(R)` = `skewness(R, method = "moment") /
  kurtosis(R, method = "moment")`, i.e. population $g_1 / b_2$ with
  $b_2 = m_4/m_2^2$. **Verified** equal to $g_1/b_2$ from OpenFactsheet's cached
  population moments, and different from the canonical $G_1/(G_2+3)$ (known
  difference 22 in `docs/validation/reference_implementations.md`).
- No mean-difference or bias-ratio function in PerformanceAnalytics 2.0.4.

## QuantStats behavior

None of the five statistics is implemented (QuantStats 0.0.81).

## Empyrical behavior

None of the five statistics is implemented (empyrical-reloaded 0.5.12).

## Other implementations

skfolio 1.0.6 `measures.gini_mean_difference` uses ordered weights
$(4k - 2(n+1)) / (n(n-1))$ on the sorted returns, which is the same $n(n-1)$
estimator. **Verified** equal to `gini_mean_difference` (and, divided by the
mean, to `relative_mean_difference`) to 1e-9 on the three fixtures. No library
implementation of the bias ratio was found; it is checked against hand
computations.

## Academic sources

- Bacon, C. R. *Practical Risk-Adjusted Performance Measurement* (2nd ed.),
  Wiley: ch. 2 p. 16 eqs. (2.8)-(2.9); ch. 3 p. 58 eq. (3.7); ch. 6 pp. 130-131
  eq. (6.32); ch. 10 p. 194 eq. (10.17) (page and equation numbers as given in
  the implementation brief).
- Gini, C. (1912). *Variabilità e mutabilità*.
- Yitzhaki, S. (2003). Gini's Mean Difference: A Superior Measure of Variability
  for Non-Normal Distributions. *Metron*, 61(2), 285-316.
- Watanabe, Y. (2006). Is Sharpe Ratio Still Effective? *Journal of Performance
  Measurement*, 11(1), 55-66.
- Abdulali, A. (2006). The Bias Ratio: Measuring the Shape of Fraud. Protégé
  Partners Quarterly Letter (practitioner note).

## OpenFactsheet decision

| Metric id | Category | Definition | Undefined when | Policy |
|---|---|---|---|---|
| `gini_mean_difference` | volatility | MD with the $n(n-1)$ pair denominator, per period | n < 2 (`insufficient_data`) | `dispersion` |
| `relative_mean_difference` | volatility | MD / $\bar r$ with the **signed** mean | $\bar r = 0$ | `dispersion` |
| `skewness_kurtosis_ratio` | distribution | $G_1/(G_2+3)$ with the canonical estimators of decision 0011 | constant returns; $G_2 + 3 \le 0$ | `kurtosis` |
| `bias_ratio` | distribution | BR with $s$ = sample std, closed intervals, zero counted on both sides | identical returns ($s = 0$) | `ratio_standard` |
| `volatility_skewness` | distribution | $\mathrm{UPM}_2(0)/\mathrm{LPM}_2(0)$, full-sample denominators (they cancel); 0 when no return exceeds the target | no return below the target ($\mathrm{LPM}_2 = 0$) | `ratio_standard` |

- **No annualization** for any of the five: all are per-period quantities or
  dimensionless ratios of per-period quantities.
- **Computation of MD.** O(n log n) from the sorted returns. The implementation
  uses the summation-by-parts identity
  $\sum_k (2k-n-1) r_{(k)} = \sum_{k=1}^{n-1} k(n-k)(r_{(k+1)} - r_{(k)})$, a sum
  of non-negative terms, so identical returns give exactly 0 and rounding can
  never produce a negative dispersion. A quadratic implementation is used only
  in tests.
- **Directions.** `gini_mean_difference` is *lower is better*, like the other
  dispersion measures (volatility, MAD). `relative_mean_difference`,
  `skewness_kurtosis_ratio` and `volatility_skewness` are *context dependent*:
  RMD changes sign with the mean, SKR inherits the context dependence of
  skewness, and VS ignores the level of returns. `bias_ratio` is *neutral*: it
  is a data-shape diagnostic, not a quality scale, and a high value is not
  evidence of wrongdoing.
- **Category of the bias ratio.** *Distribution*: it is a statistic of the
  empirical distribution (invariant to the order of the returns), describing
  where the probability mass sits around zero. The consistency section holds
  path and calendar statistics (streaks, calendar and rolling years), and the
  serial-dependence section holds order-dependent statistics.
- **Flags.** MD, RMD and VS are volatility-based (smoothing lowers their
  confidence, as for MAD and the partial-moment ratios); the bias ratio is not,
  because smoothing is what it describes.
- **Not registered.** Variability skewness ($\sqrt{\mathrm{VS}}$) is a monotonic
  transform of `volatility_skewness`; standalone $\mathrm{UPM}_2$ /
  $\mathrm{LPM}_2$ are intermediate quantities ($\sqrt{\mathrm{LPM}_2}$ is the
  per-period downside deviation already reported).

## Rationale

- The $n(n-1)$ denominator is Bacon's and Gini's definition and the unbiased
  estimator; it agrees with skfolio.
- Bacon prints the signed mean; replacing it by $|\bar r|$ would silently create
  a different statistic. The negative values it produces for losing histories
  are documented instead.
- Using the canonical $G_1$ and $G_2$ keeps the ratio consistent with the
  skewness and excess kurtosis printed next to it in the same report; Bacon's
  population moments are the PerformanceAnalytics convention and are pinned as
  a known difference. $G_2 + 3$ can be zero or negative in very small samples
  (e.g. n = 4 with two values: $G_2 = -6$); a ratio with a non-positive
  kurtosis estimate is meaningless, so it is reported as undefined.
- The bias ratio follows the printed closed intervals exactly, so the value
  replicates Bacon's definition; the double-counted zero is disclosed in the
  result details (`zero_returns_counted_both_sides`).

## Consequences

- The canonical catalog grows from 97 to 102 metrics. No existing value,
  status, confidence label or relative order changes (verified on every golden
  report), so the methodology version stays 0.1.0.
- `relative_mean_difference` is unstable when the mean is near zero and
  negative for losing histories; both cases are stated in its documentation.
- `skewness_kurtosis_ratio` differs from PerformanceAnalytics in small samples;
  the two converge as n grows.
- `skewness_kurtosis_ratio` is 1.5% to 3% smaller in magnitude than
  PerformanceAnalytics' value on the fixtures (n = 60 to 120).
- On the smoothed hedge-fund fixture (high smoothing risk) the bias ratio is 13
  (52 returns in $[0, s]$, 3 in $[-s, 0]$), against 0.8 to 1.6 on the other
  fixtures — the kind of asymmetry it was designed to show, reported beside the
  smoothing diagnostics rather than as a verdict.
- **Flagged ambiguities (book not available to verify):** (1) whether Bacon's
  $s$ in eq. (10.17) is the sample or population standard deviation — the
  sample estimator of decision 0003 is used; (2) whether Bacon intends a
  population-moment SKR — the canonical bias-corrected estimators are used and
  the difference is pinned; (3) page and equation numbers are taken from the
  brief. Bacon's worked examples were not replicated because his sample data
  were not available.
