# Methodology decisions

Each file records one convention of the canonical OpenFactsheet methodology:
the problem, how reference implementations behave, the academic sources, the
decision and its consequences. The machine-readable form of every decision is
`src/openfactsheet/policy/defaults.py` (conventions) and
`src/openfactsheet/policy/thresholds.py` (minimum-data policies).

All decisions below are **Accepted** for methodology **0.1.0**.

| # | Decision | Summary |
|---|---|---|
| [0001](0001-return-type.md) | Return type | Simple decimal returns internally; percent converted; prices rejected; values below -100% flagged, never clipped. |
| [0002](0002-annualization-and-frequency.md) | Frequency and annualization | Frequency inferred from calendar spacing; 252/365/52/12/4/1; irregular or unknown frequency is never annualized. |
| [0003](0003-standard-deviation.md) | Standard deviation | Sample estimator (n − 1) everywhere volatility appears. |
| [0004](0004-annual-return.md) | Annual return | Geometric CAGR by observation count; arithmetic `P x mean` reported separately; under one year → low confidence. |
| [0005](0005-risk-free-rate.md) | Risk-free rate | 0% in 0.1.0, disclosed on every affected metric; never inferred from locale. |
| [0006](0006-sortino-downside-deviation.md) | Sortino / downside deviation | MAR = 0, full-sample denominator, annualized by sqrt(P). |
| [0007](0007-drawdown-conventions.md) | Drawdowns | Initial wealth 1 is a peak; signed depths; peak-to-recovery episodes and durations; one shared engine. |
| [0008](0008-sharpe-ratio.md) | Sharpe ratio | Arithmetic mean / sample std x sqrt(P), rf = 0. |
| [0009](0009-calmar-full-history.md) | Calmar ratio | Full history (not a trailing 36-month window). |
| [0010](0010-var-es-quantiles.md) | VaR / ES / tail ratio | Historical 95%, linear (type 7) quantile, signed returns, ES over r <= q. |
| [0011](0011-skewness-kurtosis.md) | Skewness / kurtosis | Bias-corrected G1 and excess G2 (pandas / Excel). |
| [0012](0012-benchmark-alignment-and-relative-metrics.md) | Benchmark alignment and metrics | Calendar-period intersection, never filled; OLS with rf = 0; arithmetic alpha / IR / Treynor; geometric capture. |
| [0013](0013-return-scale-detection.md) | Return-scale detection | Deterministic percent/decimal classifier; refuses to guess in the ambiguous zone. |
| [0014](0014-smoothing-risk.md) | Smoothing risk | Lag-1 autocorrelation + significance thresholds; warn and downgrade, never unsmooth. |
| [0015](0015-minimum-data-policy.md) | Minimum-data policies | Named policies: mathematical minimum vs statistical confidence thresholds. |
| [0016](0016-lower-partial-moment-ratios.md) | Lower-partial-moment ratios and dispersion | Kappa 3, upside potential, LPM 1, semi-deviation, MAD: target 0, full-sample denominators; per period except annualized semi-deviation. |
| [0017](0017-drawdown-ratios-burke-sterling-pain.md) | Burke, Sterling, Pain, payoff | Canonical episode depths for Burke; Sterling = CAGR / (\|MDD\| + 10%); Pain ratio = CAGR / Pain Index; payoff excludes zeros. |
| [0018](0018-parametric-var.md) | Parametric VaR | Gaussian and Cornish-Fisher VaR with population moments; supplementary, model-dependent. |
| [0019](0019-sharpe-ratio-inference.md) | Sharpe-ratio inference | PSR vs 0, SE with two-sided 95% CI, MinTRL at 95%; kurtosis kept; i.i.d. asymptotics; no Deflated Sharpe. |
| [0020](0020-mean-inference-and-normality.md) | Mean inference and normality | Student-t 95% CI and t-test for the mean; Jarque-Bera with population moments (supplementary). |

## Adding or changing a decision

Follow CLAUDE.md sections 20 and 45 whenever definitions of a metric or
convention disagree:

1. Identify the authoritative definition (original paper, recognized textbook or
   practitioner standard, PerformanceAnalytics documentation, established Python
   libraries).
2. Compare implementations and record each library's behavior. Mark anything
   not checked numerically as "reported in library docs, not verified here".
3. Write a note `NNNN-short-slug.md` with the sections: Status, Problem, Known
   definitions, PerformanceAnalytics behavior, QuantStats behavior, Empyrical
   behavior, Academic sources, OpenFactsheet decision, Rationale, Consequences.
4. Implement the decision independently from the mathematical definition (never
   copy GPL code), add edge-case unit tests and a cross-library test that pins
   agreement or the documented difference.
5. Update `docs/validation/reference_implementations.md` and, if applicable,
   `docs/assumptions.md`.

Never resolve a disagreement by choosing whichever convention produces the more
attractive number.

## Versioning rule

Any change that alters a canonical value, status, confidence label, threshold
or convention requires:

- incrementing `METHODOLOGY_VERSION` in
  `src/openfactsheet/policy/methodology_version.py`;
- a CHANGELOG entry;
- a new or superseding decision note (the old note is kept and marked
  "Superseded by NNNN");
- conscious regeneration and review of the golden reports
  (`python scripts/update_golden.py`).

Package releases that do not change results keep the same methodology version.
