# 0015 — Minimum-data policies and confidence

**Status:** Accepted — methodology 0.1.0

## Problem

Every statistic can be computed from very little data, but many are unreliable
until the sample is large. Hiding such metrics would be selective reporting;
showing them without qualification overstates certainty.

## Known definitions

Common practitioner rules of thumb: at least 36 monthly observations for
risk-adjusted ratios; standard error of skewness about `sqrt(6/n)`, of
kurtosis about `sqrt(24/n)`, of an autocorrelation about `1/sqrt(n)`. GIPS
prohibits annualizing returns for periods shorter than one year.

## PerformanceAnalytics behavior

No minimum-data policy; functions return a number or `NA`.

## QuantStats behavior

No minimum-data policy.

## Empyrical behavior

Returns `NaN` for too-short input; no confidence labels.

## Academic sources

- Lo, A. W. (2002). *FAJ* 58(4).
- Joanes & Gill (1998); Ljung & Box (1978).
- CFA Institute (2020). GIPS.

## OpenFactsheet decision

Each metric names a policy (`policy/thresholds.py`). Below the mathematical
minimum the status is `insufficient_data` (no value). Otherwise the value is
shown and confidence is set from the statistical thresholds:

| Policy | Math min | Basis | Low below | Moderate below |
|---|---:|---|---:|---:|
| observed_point | 1 | none | — | — |
| path_risk | 1 | years | 3 | 5 |
| location | 1 | years | 3 | 5 |
| dispersion | 2 | years | 3 | 5 |
| ratio_standard | 2 | years | 3 | 5 |
| skewness | 3 | observations | 60 | 120 |
| kurtosis | 4 | observations | 120 | 240 |
| tail | 2 | expected tail obs. (n x 5%) | 5 | 10 |
| autocorrelation | 5 | observations | 36 | 60 |
| ljung_box | 10 | observations | 36 | 60 |
| benchmark_regression | 3 | years of overlap | 3 | 5 |
| benchmark_simple | 2 | years of overlap | 3 | 5 |

Additional rules (`policy/confidence.py`):
- Years basis with unknown years (undated, no declared frequency) → `low`.
- Annualized metric with less than one year of data → `low`, with a warning
  that the figure extrapolates a partial year (GIPS).
- Missing periods cap wealth-path and annualized metrics at `moderate`.
- Smoothing and stale-return rules: [0014](0014-smoothing-risk.md).
- Benchmark coverage below 90% caps benchmark metrics at `moderate`.
- Status: `supplementary` for supplementary metrics; else `low_confidence` when
  confidence is `low`; else `applicable`.

## Rationale

Separating "can it be computed" (applicability) from "how reliable is it"
(confidence) lets the report compute everything while stating uncertainty.
Thresholds are conventions, not laws of nature, so they are explicit and versioned.

## Consequences

- Short track records show a full metric set, mostly labeled `low` confidence.
- Confidence describes estimation reliability, never investment quality.
- Changing any threshold requires a methodology version bump.
