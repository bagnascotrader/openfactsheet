# 0018 — Parametric VaR: Gaussian and Cornish-Fisher with population moments

**Status:** Accepted — methodology 0.1.0

## Problem

Parametric VaR needs a variance estimator (sample or population) and, in the
Cornish-Fisher (modified) version, estimators for skewness and kurtosis. It is
model-dependent, so it must not be presented as if it were an observed or
historical estimate.

## Known definitions

With $z = \Phi^{-1}(0.05)$, moment skewness $S = m_3 / m_2^{3/2}$ and excess
kurtosis $K = m_4/m_2^2 - 3$:

```math
\mathrm{VaR}^{N}_{95} = \bar r + z\sqrt{m_2}, \qquad
\mathrm{mVaR}_{95} = \bar r + h\sqrt{m_2}, \quad
h = z + \frac{(z^2-1)S}{6} + \frac{(z^3-3z)K}{24} - \frac{(2z^3-5z)S^2}{36}
```

(Zangari, 1996; Favre & Galeano, 2002). Implementations differ in whether they
use population moments ($m_k$, denominator $n$) or sample moments.

## PerformanceAnalytics behavior

`VaR.Gaussian` uses `-mean(r) - qnorm(alpha) * sqrt(m2)` with the centered
(population) second moment. `VaR.CornishFisher` uses population $m_2, m_3, m_4$
with `.skewEst` and `.kurtEst` (moment skewness and excess kurtosis). The public
`VaR(method = ...)` returns a signed (negative) number. **Verified:**
`gaussian_var_95` and `modified_var_95` equal `VaR(p = 0.95, method =
"gaussian")` and `VaR(p = 0.95, method = "modified")` to 1e-9 on all fixtures.

## QuantStats behavior

`stats.value_at_risk` is a normal-distribution VaR that uses the sample
(n − 1) standard deviation. **Verified** to equal
`norm.ppf(0.05, mean, std(ddof=1))`; it therefore differs slightly from
`gaussian_var_95`.

## Empyrical behavior

No parametric VaR is used as a reference here.

## Academic sources

- Zangari, P. (1996). A VaR Methodology for Portfolios That Include Options.
  *RiskMetrics Monitor*.
- Favre, L., & Galeano, J.-A. (2002). Mean-Modified Value-at-Risk Optimization
  with Hedge Funds. *Journal of Alternative Investments* 5(2).
- Boudt, K., Peterson, B. G., & Croux, C. (2008). Estimation and Decomposition
  of Downside Risk for Portfolios with Non-Normal Returns. *Journal of Risk* 11(2).
- Jorion, P. (2006). *Value at Risk*.

## OpenFactsheet decision

- Both VaRs use population moments (`parametric_var.moments = "population"`)
  at 95% (`parametric_var.confidence`). They are per period and signed
  (negative = loss), like the historical VaR ([0010](0010-var-es-quantiles.md)).
- Both carry status `supplementary` and nature `model_dependent`, and they are
  volatility-based (smoothing lowers their confidence). The historical VaR
  remains the headline tail estimate.
- Gaussian VaR uses the `dispersion` minimum-data policy. Modified VaR uses the
  `kurtosis` policy (at least 4 observations; low confidence below 120).
- Modified VaR is `not_applicable` when all returns are identical ($m_2 = 0$).

## Rationale

Population moments follow Boudt, Peterson & Croux (2008), the published
reference implementation. They also make the Cornish-Fisher quantile reduce
*exactly* to the Gaussian one when $S = K = 0$, so the two parametric VaRs are
mutually consistent. The small difference from the sample standard deviation
used for volatility ([0003](0003-standard-deviation.md)) is disclosed here.

## Consequences

- `gaussian_var_95` does not equal `mean + z × volatility` exactly (population
  vs sample standard deviation); the relative difference is about $1/(2n)$.
- For extreme skewness or kurtosis, the Cornish-Fisher expansion can become
  non-monotonic and unreliable. The metric documentation warns about this, and
  the value is shown for context, not as the canonical tail estimate.
