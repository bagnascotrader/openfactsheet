# 0011 — Skewness and kurtosis estimators

**Status:** Accepted — methodology 0.1.0

## Problem

Several sample skewness and kurtosis estimators are in use (biased moment
estimators, bias-adjusted estimators, "excess" vs raw kurtosis). They differ
noticeably in short samples, and library defaults disagree.

## Known definitions

With `m_k = (1/n) sum (r_t - mean)^k` (Joanes & Gill, 1998):

- `g1 = m3 / m2^(3/2)` (biased moment skewness).
- `G1 = sqrt(n(n-1)) / (n-2) * g1` (adjusted Fisher-Pearson; Excel `SKEW`, pandas).
- `G2 = (n-1)/((n-2)(n-3)) * ((n+1) * m4/m2^2 - 3(n-1))` (bias-corrected excess
  kurtosis; Excel `KURT`, pandas).

## PerformanceAnalytics behavior

- `skewness(method = "moment")` = `g1`. Verified: OpenFactsheet `skewness`
  equals `g1 * sqrt(n(n-1))/(n-2)` to 1e-9.
- `skewness(method = "sample")` uses the population standard deviation in a
  sample-style formula and equals `G1 * (n/(n-1))^1.5`, i.e. it is neither `g1`
  nor `G1`. Verified to 1e-9 on all fixtures.
- `kurtosis(method = "sample_excess")` = `G2`. Verified to 1e-9.
- `kurtosis` default `"excess"` is the biased moment estimator minus 3.

## QuantStats behavior

`stats.skew` and `stats.kurtosis` call pandas `.skew()` / `.kurt()`, i.e. `G1`
and `G2`. Verified to 1e-9 on all fixtures.

## Empyrical behavior

No skewness/kurtosis functions in the inspected version.

## Academic sources

- Joanes, D. N., & Gill, C. A. (1998). Comparing Measures of Sample Skewness and
  Kurtosis. *JRSS D* 47(1).

## OpenFactsheet decision

- `skewness` = `G1` (`scipy.stats.skew(bias=False)`); requires n >= 3.
- `excess_kurtosis` = `G2` (`scipy.stats.kurtosis(fisher=True, bias=False)`);
  requires n >= 4; normal distribution = 0.
- Constant returns → `not_applicable`.
- Both are tagged `estimated`; direction is `context_dependent`.
- Minimum-data policies: skewness low confidence below 60 observations, moderate
  below 120; kurtosis low below 120, moderate below 240
  ([0015](0015-minimum-data-policy.md)).

## Rationale

`G1`/`G2` are the most widely reproduced estimators (Excel, pandas, SciPy with
`bias=False`), so any reader can check the numbers.

## Consequences

- OpenFactsheet skewness differs from PerformanceAnalytics' `"sample"` method by
  the factor `(n/(n-1))^1.5`; the cross-library test pins this relationship.
- The same moments drive the distribution-shape warning on volatility-based
  metrics (skewness <= -1 or excess kurtosis >= 3 with n >= 24).
