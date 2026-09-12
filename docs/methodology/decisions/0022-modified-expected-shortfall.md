# 0022 — Modified (Cornish-Fisher) Expected Shortfall

**Status:** Accepted — methodology 0.1.0

## Problem

A parametric Expected Shortfall that accounts for skewness and kurtosis
complements the Cornish-Fisher VaR ([0018](0018-parametric-var.md)). It needs a
moment convention, an expansion order and a rule for cases where the expansion
breaks down.

## Known definitions

Boudt, Peterson & Croux (2008) with $a = 0.05$, $z = \Phi^{-1}(a)$, moment
skewness $S = m_3/m_2^{3/2}$, excess kurtosis $K = m_4/m_2^2 - 3$ and the
Cornish-Fisher quantile $h$ of `modified_var_95`:

```math
\mathrm{mES}_{95} = \bar r - \frac{\sqrt{m_2}}{a}\,\varphi(h)\left[1 + \frac{h^3 S}{6}
+ \frac{(h^6 - 9h^4 + 9h^2 + 3) S^2}{72} + \frac{(h^4 - 2h^2 - 1) K}{24}\right]
```

## PerformanceAnalytics behavior

`ES.CornishFisher` implements this expression with population moments
(`centeredmoment`, `.skewEst`, `.kurtEst`) and the full expansion by default
(`c = 2`); `ES(method = "modified")` returns a signed (negative) number.
**Verified:** `modified_es_95` equals `ES(p = 0.95, method = "modified")` to 1e-9
on all fixtures (`tests/cross_library/test_performanceanalytics.py::test_phase2b_agreement`).

## QuantStats behavior

`stats.cvar` conditions on a parametric normal VaR threshold; it is not a
Cornish-Fisher ES and is not compared.

## Empyrical behavior

None.

## Academic sources

- Boudt, K., Peterson, B. G., & Croux, C. (2008). Estimation and Decomposition
  of Downside Risk for Portfolios with Non-Normal Returns. *Journal of Risk* 11(2).
- Zangari, P. (1996); Favre, L., & Galeano, J.-A. (2002) — Cornish-Fisher VaR.

## OpenFactsheet decision

- Population moments and the full second-order expansion
  (`modified_es.moments = "population"`, `modified_es.confidence = 0.95`), the
  same moment convention as the parametric VaRs of 0018.
- Signed, per period; status `supplementary`, nature `model_dependent`,
  volatility-based; `kurtosis` minimum-data policy (at least 4 observations, low
  confidence below 120).
- When the computed mES is *less severe* than the modified VaR (mES > mVaR in
  signed terms), a note is attached: the expansion is unreliable for these
  moments and the historical Expected Shortfall should be relied on.
- `not_applicable` when returns are numerically constant (variance zero or below
  floating-point resolution).

## Rationale

The Boudt–Peterson–Croux form is the published reference implementation and is
consistent with the Cornish-Fisher VaR already reported. Flagging the
non-monotone case is more honest than silently clipping mES to mVaR.

## Consequences

- The historical ES ([0010](0010-var-es-quantiles.md)) remains the headline tail
  estimate; mES is shown for context.
- For extreme skewness or kurtosis the expansion misbehaves; the note makes this
  visible in the report.
