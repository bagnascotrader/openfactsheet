# 0014 — Return-smoothing risk: diagnose and warn, never unsmooth

**Status:** Accepted — methodology 0.1.0

## Problem

Returns of illiquid or appraisal-priced portfolios (many hedge funds, private
assets) are smoothed: reported marks lag true values. Smoothing induces positive
serial correlation, understates volatility and inflates Sharpe-type ratios.
Unsmoothing models exist but add model risk and would change reported returns.

## Known definitions

- Sample autocorrelation `rho_k` (full-sample variance denominator).
- Getmansky, Lo & Makarov (2004): observed returns as a moving average of true
  returns; significant positive `rho_1` indicates smoothing/illiquidity.
- Ljung-Box Q test of joint zero autocorrelation.

## PerformanceAnalytics behavior

Provides `table.Autocorrelation` and `Return.Geltner`/`Return.GLM`-style
unsmoothing tools; no automatic warning. R's `acf` and `Box.test` were used as
references: OpenFactsheet lag-1..3 autocorrelations agree to 1e-9 and the
3-lag Ljung-Box p-value to 1e-7 on all fixtures (verified).

## QuantStats behavior

No smoothing diagnostics (reported in library docs, not verified here).

## Empyrical behavior

No smoothing diagnostics.

## Academic sources

- Getmansky, M., Lo, A. W., & Makarov, I. (2004). An Econometric Model of Serial
  Correlation and Illiquidity in Hedge Fund Returns. *JFE* 74(3).
- Lo, A. W. (2002). The Statistics of Sharpe Ratios. *FAJ* 58(4).
- Ljung, G. M., & Box, G. E. P. (1978). *Biometrika* 65(2).

## OpenFactsheet decision

Smoothing risk (`diagnostics/smoothing.py`), with `z = rho_1 * sqrt(n)`:

| Level | Rule |
|---|---|
| high | `rho_1 >= 0.30` and `z >= 1.96` |
| moderate | `rho_1 >= 0.15` and `z >= 1.645` |
| none | otherwise |
| not_assessable | fewer than 12 observations, or `rho_1` undefined |

Effects on volatility-based metrics (volatility, annualized volatility,
downside deviation, Sharpe, Sortino, tracking error, Information ratio):
`high` forces confidence to `low` (status `low_confidence`) with a warning;
`moderate` caps confidence at `moderate` with a warning. The interpretation adds
that the figure is an optimistic bound. Path and tail metrics are not
downgraded for smoothing.

Related stale-price rules: 10% or more exactly-zero returns caps volatility-based
metrics at `moderate`; 3 or more identical consecutive returns is a finding.
If smoothing is `none` but the Ljung-Box p-value is below 0.05, an informational
finding is added. `autocorrelation_lag1..3` and `ljung_box_pvalue`
(supplementary) are reported as metrics.

Returns are **never unsmoothed** in the canonical report.

## Rationale

Warning preserves the reported data and makes the risk visible; unsmoothing
would replace observed returns with model output. The thresholds combine an
economically material effect size with statistical significance.

## Consequences

- The thresholds are a transparent heuristic, versioned in
  `policy/defaults.py` (`smoothing`); changing them is a methodology change.
- An optional unsmoothing research module may be added outside the canonical report.
