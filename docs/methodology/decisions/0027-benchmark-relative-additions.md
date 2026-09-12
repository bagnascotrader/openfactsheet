# 0027 — Benchmark-relative additions: capture ratio, batting average, residual risk, appraisal ratio, M², regime betas

**Status:** Accepted — methodology 0.1.0

## Problem

CLAUDE.md §12.9 lists benchmark-relative measures beyond those of decision
[0012](0012-benchmark-alignment-and-relative-metrics.md): capture ratio, batting
average, bull/bear market sensitivity "if objectively defined", residual
volatility, the appraisal ratio (§12.3) and M² (§12.3). Libraries disagree on
denominators (m vs m − 2), on how alpha is annualized, and on how up/down
periods are defined. Several of these ratios have denominators that can be
zero, negative or pure rounding noise.

## Known definitions

With aligned fund returns $r_t$, benchmark returns $b_t$, $t = 1..m$, and the
single-index OLS fit $r_t = \hat\alpha + \hat\beta b_t + \hat\varepsilon_t$:

- **Residual (specific) risk:** $\hat\sigma_\varepsilon$, the standard deviation
  of $\hat\varepsilon_t$ (with m or m − 2 in the denominator).
- **Appraisal ratio** (Treynor & Black 1973): $\alpha / \sigma_\varepsilon$.
- **M²** (Modigliani & Modigliani 1997): the fund's Sharpe ratio times the
  benchmark's volatility, plus the risk-free rate: the fund's return at the
  benchmark's risk.
- **Batting average** (Morningstar): share of periods in which the fund beat the
  benchmark.
- **Capture ratio:** upside capture / downside capture.
- **Bull / bear beta** (Fabozzi & Francis 1977): betas estimated separately on
  periods when the benchmark rose / fell; **timing ratio** = bull / bear beta.

## PerformanceAnalytics behavior

Function bodies of PerformanceAnalytics 2.0.4 were read (conventions only, no
code copied) and values computed on the `benchmark_case` fixture in the R
harness:

- `SpecificRisk`: `sqrt(sum((e - mean(e))^2) / m) * sqrt(P)`, the
  **m-denominator** residual standard deviation. Verified: equals
  OpenFactsheet's residual volatility x sqrt((m − 2) / m).
- `AppraisalRatio(method = "appraisal")`: `CAPM.jensenAlpha / SpecificRisk`,
  where `CAPM.jensenAlpha = Rp − Rf − beta (Rb − Rf)` uses **geometric
  annualized** fund and benchmark returns. Verified numerically.
- `Modigliani`: per-period `SharpeRatio(Ra, FUN = "StdDev") * StdDev(Rb) +
  mean(Rf)`. Verified: equals OpenFactsheet's M² / 12.
- `CAPM.beta.bull` / `CAPM.beta.bear`: `lm` with intercept on the subsets
  `Rb > 0` / `Rb < 0` (excess of Rf = 0). `TimingRatio` = bull / bear. All
  verified to 1e-9.
- `UpDownRatios(method = "Percent")`: share of up (`Rb > 0`) or down (`Rb < 0`)
  periods in which `Ra > Rb` (strict). Verified against the details of
  `batting_average`.

## QuantStats behavior

No appraisal ratio, M², batting average, regime betas or capture ratio in
QuantStats 0.0.81 (not verified further).

## Empyrical behavior

`up_down_capture` = `up_capture / down_capture` with geometric annualized
captures. Verified to 1e-9 against `capture_ratio`. empyrical has no appraisal
ratio, M², batting average or regime betas.

## Academic sources

- Treynor, J. L., & Black, F. (1973). *Journal of Business* 46(1).
- Modigliani, F., & Modigliani, L. (1997). *Journal of Portfolio Management* 23(2).
- Fabozzi, F. J., & Francis, J. C. (1977). *Journal of Finance* 32(4).
- Grinold & Kahn (2000); Bacon (2021); Morningstar capture and batting-average
  definitions.

## OpenFactsheet decision

All metrics use the aligned overlap of decision 0012, rf = 0
([0005](0005-risk-free-rate.md)) and arithmetic annualization.

- `residual_volatility` $= \hat\sigma_\varepsilon \sqrt{P}$ with
  $\hat\sigma_\varepsilon^2 = \sum \hat\varepsilon_t^2 / (m - 2)$ (the
  regression standard error, consistent with the OLS standard errors already
  reported for alpha and beta). Details give the systematic volatility
  $|\hat\beta| \, s_b \sqrt{P}$. Model-dependent.
- `appraisal_ratio` $= P\hat\alpha / (\hat\sigma_\varepsilon\sqrt{P})$. Undefined
  when $\hat\sigma_\varepsilon \le \sqrt{\epsilon_{\text{mach}}}\, s_r$, i.e.
  $1 - R^2$ below machine epsilon: the benchmark explains the fund exactly and
  the ratio would be rounding noise.
- `m_squared` $= P \, (\bar r / s_r) \, s_b$ on aligned periods (sample
  standard deviations). Details give the benchmark's annualized mean and the
  difference (M² excess). Undefined when fund or benchmark returns are constant
  (tested on the values, not on a computed standard deviation, which can be
  rounding noise).
- `batting_average` = share of aligned periods with $r_t > b_t$ strictly; ties
  do not count as beating. Details give up- and down-market batting averages
  (benchmark > 0 / < 0), ties and period counts.
- `capture_ratio` = `upside_capture / downside_capture` (geometric, decision
  0012). Undefined when downside capture is zero or negative: the fund did not
  lose on average when the benchmark fell, and a ratio with a non-positive
  denominator would have a meaningless sign. Both captures remain reported.
- `bull_beta` / `bear_beta`: OLS with intercept on periods with $b_t > 0$ /
  $b_t < 0$ (zero-benchmark periods belong to neither), at least 3 periods and
  a non-constant benchmark in the subset; a note is added below 12 periods.
- `timing_ratio` = bull / bear beta; undefined unless bear beta > 0, for the same
  reason as the capture ratio.

**Exact solution for a constant fund.** When the fund's aligned returns are
identical, the single-index fit is solved exactly (beta 0, alpha equal to the
return, zero residuals) instead of numerically. A numerical solve leaves
rounding noise such as beta = 1e−17, which previously produced a Treynor ratio
of about −8.6e15; ratios dividing by beta or residual risk are now
`not_applicable`. R² is undefined for a constant fund (no variance to explain)
instead of an `error` status.

## Rationale

The m − 2 residual denominator and the arithmetic alpha keep the appraisal
ratio consistent with the alpha t-statistic and with alpha, Treynor and the
Information ratio of decision 0012. Refusing ratios whose denominators are
non-positive or below numerical resolution follows "approximately right rather
than exactly wrong": the components are always shown, only the meaningless
quotient is withheld, with the reason.

## Consequences

- Residual volatility and the appraisal ratio differ from PerformanceAnalytics'
  `SpecificRisk` and `AppraisalRatio`; the tests pin both relationships.
- Regime betas condition on the sign of the benchmark, which truncates the
  regressor; they are descriptive, not a test of timing skill. Formal timing
  models (Treynor-Mazuy, Henriksson-Merton) are not part of methodology 0.1.0.
- The metric catalog grows from 82 to 90 metrics; no existing value changes.
