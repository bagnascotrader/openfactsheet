# 0021 — Drawdown tail (DaR, CDaR, EDaR) and entropic VaR

**Status:** Accepted — methodology 0.1.0

## Problem

Tail measures of the drawdown path (Drawdown-at-Risk, Conditional
Drawdown-at-Risk, Entropic Drawdown-at-Risk) and the entropic VaR of returns
need four choices: which drawdown path (compounded or uncompounded, with or
without the inception peak), which periods form the sample, which quantile
estimator, and how to compute the entropic infimum.

## Known definitions

With losses $X$ and tail probability $a = 0.05$:

```math
\mathrm{DaR}_{95} = Q_{0.95}(-D), \qquad
\mathrm{CDaR}_{95} = \mathbb{E}[-D \mid -D \ge \mathrm{DaR}_{95}], \qquad
\mathrm{EVaR}_{a}(X) = \inf_{z>0} z \ln\frac{\mathbb{E}[e^{X/z}]}{a}
```

and $\mathrm{EDaR}_{a} = \mathrm{EVaR}_{a}(-D)$ (Chekhlov, Uryasev & Zabarankin
2005; Ahmadi-Javid 2012; Cajas 2021). Libraries differ in the drawdown path
(uncompounded cumulative sums vs compounded wealth) and in the discrete
quantile / CVaR estimator.

## PerformanceAnalytics behavior

`CDD` ("Conditional Drawdown") is the 5% quantile over all `findDrawdowns` runs
(drawdown episodes and the zero-return runs between them), inverted to a positive
number; it is not a conditional expectation of the drawdown path (verified in the
R harness and pinned by a test). No DaR / EDaR / EVaR.

## QuantStats behavior

No drawdown tail or entropic measures.

## Empyrical and skfolio behavior

empyrical has none. skfolio 1.0.6 (`skfolio.measures`) was compared in
`tests/cross_library/test_python_references.py::test_skfolio_drawdown_and_entropic_measures`:

- `get_drawdowns(r, compounded=True)` starts its running peak at $W_1$, so a
  first-period loss is not a drawdown; the default is `compounded=False`
  (uncompounded). **Verified** (path pinned).
- `drawdown_at_risk` equals `numpy.quantile(-D, 0.95, method="inverted_cdf")`
  (lower order statistic). **Verified.**
- `cdar` uses a fractional Rockafellar–Uryasev weighting; it equals the
  OpenFactsheet value exactly when $(1-0.95)\,n$ is an integer. **Verified** on
  the fixtures where it is ($n = 60$ and $n = 120$).
- `edar` and `evar` agree with OpenFactsheet to relative 1e-7 (solver tolerance)
  on all fixtures. **Verified.**

## Academic sources

- Chekhlov, A., Uryasev, S., & Zabarankin, M. (2005). Drawdown Measure in
  Portfolio Optimization. *IJTAF* 8(1).
- Ahmadi-Javid, A. (2012). Entropic Value-at-Risk. *JOTA* 155(3).
- Cajas, D. (2021). Entropic Portfolio Optimization. SSRN 3792520.

## OpenFactsheet decision

- Path: the canonical compounded drawdowns $D_t = W_t/M_t - 1$, $t = 1..n$, with
  $W_0 = 1$ counting as a peak ([0007](0007-drawdown-conventions.md)); the
  inception point itself is not a sample observation.
- `drawdown_at_risk_95` $= Q_{0.05}(D)$ with linear interpolation, and
  `cdar_95` $= $ mean of $D_t \le Q_{0.05}(D)$ — the historical VaR / ES
  estimators of [0010](0010-var-es-quantiles.md). Signed (negative = loss).
- `edar_95` $= -\mathrm{EVaR}_{0.05}(-D)$ and `evar_95` $= -\mathrm{EVaR}_{0.05}(-r)$,
  computed by `utils.math.entropic_value_at_risk`: losses scaled to unit maximum
  absolute value (EVaR is positively homogeneous), bounded Brent search over
  $\log z \in [-25, 12]$ (`xatol` 1e-12), result capped at the maximum loss;
  zero losses give 0 and constant losses give that constant.
- Confidence 95% (`drawdown_risk.confidence`, `entropic.confidence`). All four use
  the `tail` minimum-data policy; the three drawdown measures are wealth-path
  metrics.

## Rationale

One estimator for every historical tail measure keeps DaR and CDaR consistent
with VaR and ES and makes CDaR literally "Expected Shortfall of the drawdown
path". Counting $W_0$ as a peak matches the rest of the drawdown module.

## Consequences

- The coherent ordering $\mathrm{MDD} \le \mathrm{EDaR} \le \mathrm{CDaR} \le
  \mathrm{DaR} \le 0$ is expected (EVaR dominates the fractional CVaR, which in
  turn is at least as severe as the `<=`-quantile mean); it is asserted in a unit
  test.
- With $n \le 1/a = 20$ observations the empirical EVaR equals the worst loss,
  so `evar_95` equals the worst period and `edar_95` the maximum drawdown
  (asserted in `tests/unit/metrics/test_phase2b.py`; stated on the metric pages).
- Drawdown observations are strongly serially dependent: the 5% tail often
  comes from one episode.
