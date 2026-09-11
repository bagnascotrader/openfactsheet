# CLAUDE.md — OpenFactsheet

## 0. Mission

Build **OpenFactsheet**, a free and open-source Python library that takes an investment return history and produces a standardized, transparent, non-cherry-picked investment performance analysis.

Supported inputs should eventually include:

- Python `list`, `tuple`, `numpy.ndarray`, `pandas.Series`, and `pandas.DataFrame`
- CSV
- Excel
- pasted monthly-return tables
- PDF factsheets
- screenshots / images of monthly-return tables
- optionally, price/NAV series when explicitly identifiable, converting them to returns before analysis

The primary API should be intentionally simple:

```python
import openfactsheet as ofs

report = ofs.analyze(returns)
```

and, when applicable:

```python
report = ofs.analyze(returns, benchmark=benchmark_returns)
comparison = ofs.compare(fund_a, fund_b, etf_c)
```

The user SHOULD NOT need to choose metric windows, annualization conventions, downside thresholds, display subsets, or similar knobs merely to obtain a factsheet.

OpenFactsheet is not another configurable tear-sheet library. It is intended to become an **open standard for consistent investment-performance measurement**.

---

# 1. First principles

All implementation decisions MUST be consistent with the following principles.

## 1.1 Approximately right is better than exactly wrong

Investment performance statistics are estimates generated from finite, noisy return histories. Many investment returns are non-normal, serially correlated, heteroskedastic, smoothed, regime-dependent, or otherwise inconsistent with the assumptions behind classical statistics.

Prefer:

- robust interpretation,
- explicit assumptions,
- confidence/applicability warnings,
- transparent methodology,

over false numerical precision.

Never imply that a metric is more reliable than the data permits.

---

## 1.2 Compute broadly; do not permit metric cherry-picking

OpenFactsheet should compute the full canonical metric universe that is mathematically possible from the available data.

The default report is determined by OpenFactsheet, NOT by the fund marketer.

Do not design the primary API around:

```python
metrics = ["sharpe", "sortino", "calmar"]
```

because this makes selective reporting the default behavior.

Internally, metrics can be selected for tests or development, but end-user factsheets should follow canonical reporting rules.

The reporting engine can distinguish:

- applicable
- applicable but low confidence
- supplementary
- benchmark required
- factor data required
- unavailable
- not meaningful for the supplied data

but must not silently omit an unfavorable metric merely because it produces an unattractive result.

---

## 1.3 No fine-tuning metric periods

Avoid arbitrary user-selected periods and thresholds designed to improve presentation.

The canonical analysis should use:

- full available history for since-inception statistics;
- standard calendar periods when reporting calendar statistics;
- standard trailing periods only when objectively defined and enough data exist;
- deterministic annualization based on inferred frequency;
- deterministic conventions stored in a methodology registry.

Do not let the default workflow optimize:

- start dates,
- rolling window lengths,
- MAR thresholds,
- confidence levels,
- benchmark choice,
- risk-free assumptions,
- return frequency,
- annualization factor,

for a better-looking result.

Advanced APIs may expose overrides in the future for research purposes, but overridden results MUST be labeled as non-canonical.

---

## 1.4 Simple to use; unusually well documented

Every metric must answer:

1. What does it measure?
2. Formula / mathematical definition.
3. What inputs does it require?
4. Is higher/lower better?
5. How should a retail investor interpret it?
6. How should an institutional investor interpret it?
7. What assumptions does it make?
8. When can it be misleading?
9. What minimum amount of data is sensible?
10. Which reference implementation(s) agree with it?
11. Which academic / practitioner source defines it?
12. What OpenFactsheet convention is used where definitions vary?

Documentation is a core feature, not an afterthought.

---

## 1.5 Broad investment applicability

OpenFactsheet should be useful for return streams from:

- ETFs
- mutual funds
- hedge funds
- CTAs
- separately managed accounts
- pension mandates
- private funds when periodic NAV returns are available
- crypto funds
- systematic trading strategies
- discretionary strategies
- personal portfolios
- model portfolios
- indices
- benchmarks

Do not assume US equities unless a metric fundamentally requires market-specific information.

---

## 1.6 Free public infrastructure

The core package and canonical performance methodology should remain open source.

The architecture must avoid requiring commercial datasets or paid APIs for basic analysis.

Optional integrations with commercial data sources may exist later, but the core metric engine MUST work from user-supplied returns.

---

## 1.7 Never silently fail

Never return an unexplained `NaN`, `inf`, or missing cell.

Every metric must produce a structured result such as:

```python
MetricResult(
    id="treynor_ratio",
    value=None,
    status="not_applicable",
    reason="Benchmark returns are required to estimate beta.",
)
```

or:

```python
MetricResult(
    id="skewness",
    value=-1.21,
    status="low_confidence",
    warnings=["Only 18 monthly observations are available."],
)
```

---

## 1.8 Parameter-less does not mean assumption-less

Some measures inherently require assumptions:

- Sharpe → risk-free rate convention
- Sortino → minimum acceptable return / target
- Treynor → beta and benchmark
- Jensen alpha → benchmark / factor model
- VaR / ES → confidence level
- annualized quantities → observation frequency
- rolling metrics → rolling-window convention

OpenFactsheet MUST solve this using a **canonical policy layer**, not by pretending assumptions do not exist.

Canonical assumptions must be:

- deterministic,
- versioned,
- documented,
- visible in output,
- never optimized for a particular fund.

---

# 2. Core design philosophy

The architecture MUST separate five concerns:

```text
INPUT
  ↓
NORMALIZATION
  ↓
DATA QUALITY & FREQUENCY INFERENCE
  ↓
METRIC CALCULATION
  ↓
APPLICABILITY / CONFIDENCE POLICY
  ↓
INTERPRETATION
  ↓
REPORTING / EXPORT
```

Metric functions calculate.

Policy decides meaning/applicability.

Reporting presents.

Do NOT mix these layers.

---

# 3. Proposed repository layout

Use a `src/` layout.

```text
openfactsheet/
├── CLAUDE.md
├── README.md
├── LICENSE
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── CITATION.cff
├── docs/
│   ├── index.md
│   ├── getting_started.md
│   ├── methodology.md
│   ├── assumptions.md
│   ├── metric_catalog.md
│   ├── interpretation/
│   ├── examples/
│   └── validation/
├── examples/
│   ├── basic_returns.py
│   ├── dataframe.py
│   ├── compare_funds.py
│   ├── monthly_table.csv
│   └── notebooks/
├── src/
│   └── openfactsheet/
│       ├── __init__.py
│       ├── api.py
│       ├── version.py
│       │
│       ├── models/
│       │   ├── input.py
│       │   ├── metric.py
│       │   ├── report.py
│       │   ├── diagnostics.py
│       │   └── assumptions.py
│       │
│       ├── input/
│       │   ├── dispatcher.py
│       │   ├── arrays.py
│       │   ├── pandas_input.py
│       │   ├── csv.py
│       │   ├── excel.py
│       │   ├── clipboard.py
│       │   ├── image.py
│       │   ├── pdf.py
│       │   └── monthly_table.py
│       │
│       ├── normalization/
│       │   ├── returns.py
│       │   ├── dates.py
│       │   ├── frequency.py
│       │   ├── scaling.py
│       │   └── validation.py
│       │
│       ├── diagnostics/
│       │   ├── data_quality.py
│       │   ├── missingness.py
│       │   ├── smoothing.py
│       │   ├── autocorrelation.py
│       │   ├── outliers.py
│       │   └── stale_returns.py
│       │
│       ├── metrics/
│       │   ├── registry.py
│       │   ├── returns.py
│       │   ├── volatility.py
│       │   ├── downside.py
│       │   ├── risk_adjusted.py
│       │   ├── drawdown.py
│       │   ├── tail.py
│       │   ├── distribution.py
│       │   ├── consistency.py
│       │   ├── benchmark.py
│       │   ├── factors.py
│       │   ├── dependence.py
│       │   ├── path.py
│       │   └── statistical.py
│       │
│       ├── policy/
│       │   ├── defaults.py
│       │   ├── applicability.py
│       │   ├── confidence.py
│       │   ├── annualization.py
│       │   ├── risk_free.py
│       │   ├── thresholds.py
│       │   └── methodology_version.py
│       │
│       ├── factors/
│       │   ├── capm.py
│       │   ├── regressions.py
│       │   ├── fama_french.py
│       │   └── models.py
│       │
│       ├── interpretation/
│       │   ├── engine.py
│       │   ├── templates.py
│       │   └── glossary.py
│       │
│       ├── report/
│       │   ├── builder.py
│       │   ├── tables.py
│       │   ├── charts.py
│       │   ├── html.py
│       │   ├── markdown.py
│       │   ├── json.py
│       │   └── terminal.py
│       │
│       ├── compare/
│       │   ├── alignment.py
│       │   └── comparison.py
│       │
│       └── utils/
│           ├── math.py
│           ├── typing.py
│           └── warnings.py
│
└── tests/
    ├── unit/
    │   ├── metrics/
    │   ├── policy/
    │   ├── normalization/
    │   └── diagnostics/
    ├── integration/
    ├── regression/
    ├── cross_library/
    ├── fixtures/
    ├── golden/
    └── property/
```

---

# 4. Public API

Keep the initial public surface small.

## Required

```python
openfactsheet.analyze(...)
openfactsheet.compare(...)
openfactsheet.load(...)
openfactsheet.metric_catalog()
openfactsheet.methodology()
```

Example:

```python
import openfactsheet as ofs

report = ofs.analyze(returns)
report.summary()
report.metrics
report.diagnostics
report.assumptions
report.to_html("factsheet.html")
report.to_json("factsheet.json")
```

Benchmark:

```python
report = ofs.analyze(
    returns,
    benchmark=benchmark_returns,
)
```

Comparison:

```python
comparison = ofs.compare(
    {
        "Fund A": fund_a,
        "Fund B": fund_b,
        "ETF": etf,
    }
)
```

Avoid exposing dozens of arguments in `analyze()`.

Canonical analysis should require almost no configuration.

---

# 5. Canonical input model

Create a normalized immutable input object.

```python
@dataclass(frozen=True)
class ReturnSeries:
    values: np.ndarray
    dates: pd.DatetimeIndex | None
    frequency: ObservationFrequency
    periods_per_year: float | None
    source_type: str
    return_type: str  # initially "simple"
    metadata: dict
```

For multiple return columns:

```python
@dataclass(frozen=True)
class ReturnTable:
    series: dict[str, ReturnSeries]
```

Preserve original input separately for provenance.

Never mutate caller data.

---

# 6. Input interpretation contract

Before calculating metrics, generate an explicit `InputDiagnostics`.

Example:

```text
Detected input: monthly returns
Start: 2017-01
End: 2026-08
Observations: 116
Return scale detected: decimal
Missing months: 0
Duplicate dates: 0
Potential parsing issues: none
```

For OCR/image inputs, retain confidence and parsed cells.

The report MUST make it possible to inspect exactly which returns OpenFactsheet believes it received.

---

# 7. Return normalization

## 7.1 Primary convention

Internally use **simple decimal returns**:

- `0.01` = +1%
- `-0.02` = -2%

Do not mix simple and log returns.

If prices/NAVs are accepted, transform explicitly:

```python
r_t = P_t / P_{t-1} - 1
```

and record that a transformation occurred.

---

## 7.2 Percent-vs-decimal detection

Input:

```text
1.5, -0.8, 2.1
```

may mean percentages, while:

```text
0.015, -0.008, 0.021
```

probably means decimals.

Do not use a single naive threshold.

Implement a deterministic plausibility classifier and assign:

- detected_decimal
- detected_percent
- ambiguous

If ambiguous, do not silently guess in high-risk cases.

For image/PDF workflows, table labels containing `%` strongly influence interpretation.

---

## 7.3 Impossible values

For ordinary simple returns:

```text
r < -1.0
```

is impossible unless leverage/accounting conventions create a nonstandard series.

Flag this aggressively.

Do not clip.

---

# 8. Frequency inference

Frequency must be inferred from timestamps where possible.

Create:

```python
class ObservationFrequency(Enum):
    DAILY
    WEEKLY
    MONTHLY
    QUARTERLY
    YEARLY
    IRREGULAR
    UNKNOWN
```

Do not infer "daily = 252" solely because there are many observations.

Calendar spacing is primary evidence.

For canonical annualization:

- daily market observations: methodology-defined factor
- weekly: methodology-defined factor
- monthly: 12
- quarterly: 4
- annual: 1
- irregular: do not annualize blindly

Store every annualization assumption in the output.

---

# 9. Canonical methodology policy

Create a versioned methodology object:

```python
@dataclass(frozen=True)
class Methodology:
    version: str
    conventions: Mapping[str, Any]
```

Example:

```text
OpenFactsheet Methodology 0.1
```

Every report MUST embed the methodology version.

This makes future formula/convention changes auditable.

Never change the meaning of a metric silently between releases.

If methodology changes materially:

- increment methodology version,
- add changelog,
- maintain regression fixtures for old behavior if feasible.

---

# 10. Metric result model

Every metric returns metadata, not just a float.

```python
@dataclass(frozen=True)
class MetricResult:
    id: str
    name: str
    category: str
    value: float | None
    unit: str | None

    status: Literal[
        "applicable",
        "low_confidence",
        "supplementary",
        "not_applicable",
        "insufficient_data",
        "error",
    ]

    direction: Literal[
        "higher_is_better",
        "lower_is_better",
        "context_dependent",
        "neutral",
    ]

    observations: int
    formula_id: str
    methodology_version: str

    assumptions: tuple[str, ...]
    warnings: tuple[str, ...]
    reason: str | None

    reference_values: Mapping[str, float] | None
```

No public calculation should return unexplained `NaN` or `inf`.

---

# 11. Metric registry

Do not maintain metric lists manually in multiple places.

Create a single registry.

Example:

```python
@metric(
    id="sharpe_ratio",
    category="risk_adjusted",
    requires=("returns",),
    benchmark_required=False,
    min_observations_policy="ratio_standard",
)
def sharpe_ratio(ctx: MetricContext) -> MetricResult: ...
```

Registry metadata should contain:

```python
MetricDefinition(
    id=...,
    name=...,
    category=...,
    formula=...,
    references=...,
    dependencies=...,
    applicability_rule=...,
    confidence_rule=...,
    direction=...,
)
```

The report engine iterates over the registry.

This enforces "compute all."

---

# 12. Metric families

Implement in phases but design the registry for all categories from day one.

## 12.1 Return metrics

Candidate metrics:

- cumulative return
- arithmetic mean
- geometric mean
- CAGR / annualized return
- annualized arithmetic return
- best period
- worst period
- median return
- positive-period percentage
- negative-period percentage
- gain/loss ratio
- payoff ratio
- profit factor
- gain-to-pain ratio
- expected return estimates clearly labeled as estimates

---

## 12.2 Volatility / dispersion

- variance
- standard deviation
- annualized volatility
- semi-variance
- semi-deviation
- downside deviation
- mean absolute deviation
- median absolute deviation where meaningful
- interquartile range
- coefficient-like measures only when economically meaningful

---

## 12.3 Risk-adjusted performance

Target broad coverage:

- Sharpe Ratio
- geometric Sharpe where explicitly defined
- adjusted Sharpe
- Probabilistic Sharpe Ratio
- Deflated Sharpe Ratio
- Sortino Ratio
- Treynor Ratio
- Calmar Ratio
- MAR Ratio
- Sterling Ratio
- Burke Ratio
- modified Burke
- Omega Ratio
- Kappa
- Kappa 3
- Martin Ratio / Ulcer Performance Index
- Information Ratio
- M² / Modigliani-Modigliani
- Jensen alpha
- Appraisal Ratio
- Recovery Factor
- Gain-to-Pain
- upside-potential ratio

Do not create novel variants without references.

---

## 12.4 Drawdowns and underwater behavior

Drawdowns are a first-class module.

Implement:

- current drawdown
- maximum drawdown
- average drawdown
- median drawdown
- drawdown count / episodes
- longest drawdown
- average drawdown duration
- maximum peak-to-trough duration
- recovery duration
- time underwater
- percentage time underwater
- drawdown area / integrated underwater area
- Ulcer Index
- Pain Index
- Pain Ratio
- CDaR
- Drawdown-at-Risk where standardized
- EDaR where supported
- recovery efficiency measures with references

Create a reusable drawdown-episode engine. Do not independently reconstruct drawdowns inside each ratio.

---

## 12.5 Tail risk

- historical VaR
- historical Expected Shortfall / CVaR
- parametric VaR only as supplementary/model-dependent
- Cornish-Fisher / modified VaR
- modified Expected Shortfall where authoritative implementation exists
- worst return
- lower quantiles
- tail ratio
- extreme-loss frequency
- entropic VaR where appropriate
- Gini-based risk measures where established
- lower partial moments

Confidence levels must be canonical and methodology-versioned.

Do not allow marketers to choose confidence levels in the canonical report.

---

## 12.6 Distribution

- skewness
- excess kurtosis
- non-excess kurtosis if useful and explicitly named
- median
- quantiles
- Jarque-Bera
- normality diagnostics
- robust central tendency / dispersion
- asymmetry measures

Do not overinterpret normality tests for huge or tiny samples.

---

## 12.7 Dependence / smoothing / serial behavior

Important for hedge funds and illiquid assets:

- autocorrelation lag 1
- autocorrelation lag 2
- autocorrelation lag 3
- Ljung-Box diagnostic where appropriate
- variance ratio diagnostics if justified
- return smoothing indicators
- stale-price / repeated-return indicators
- percentage exact-zero returns
- consecutive identical returns
- volatility suppression warning
- optional unsmoothing research module later

Never automatically "unsmooth" returns in the canonical report unless methodology is extremely defensible.

Instead, diagnose and warn.

---

## 12.8 Consistency

- hit rate
- positive periods
- negative periods
- positive years
- positive rolling-year observations
- best/worst year
- best/worst month
- consecutive gains
- consecutive losses
- rolling Sharpe
- rolling Sortino
- rolling volatility
- rolling drawdown
- stability diagnostics

Rolling periods must come from canonical policy based on data frequency and should not be user-optimized.

---

## 12.9 Benchmark-relative

Only compute if a benchmark is available.

- beta
- alpha
- Jensen alpha
- R²
- correlation
- tracking error
- active return
- Information Ratio
- Treynor Ratio
- upside capture
- downside capture
- capture ratio
- batting average
- bull/bear market sensitivity if objectively defined
- residual volatility

Align dates explicitly.

Never forward-fill benchmark returns.

---

## 12.10 Factor analysis

Separate from benchmark analysis.

Potential models:

- CAPM
- Fama-French 3
- Carhart 4
- Fama-French 5
- momentum
- quality / profitability / investment where recognized
- custom user factors in advanced API

Primary engine:

- `statsmodels`
- optionally `linearmodels`

Store:

- coefficients
- alpha
- standard errors
- t-stats
- p-values
- confidence intervals
- R² / adjusted R²
- residual diagnostics
- number of aligned observations

Do not imply causality.

---

## 12.11 Statistical confidence / uncertainty

OpenFactsheet should go further than most tear-sheet libraries.

Potential metrics/diagnostics:

- sample length
- years of history
- standard error where known
- confidence interval for mean
- confidence interval for volatility where defensible
- confidence interval for Sharpe
- Probabilistic Sharpe Ratio
- Deflated Sharpe Ratio
- bootstrap uncertainty for selected metrics
- minimum track-record concepts where academically defensible

Separate raw performance from confidence in performance.

---

# 13. Data-quality diagnostics

Run before metrics.

Required checks:

- missing values
- duplicate timestamps
- missing expected periods
- unsorted timestamps
- impossible returns
- suspiciously large returns
- suspicious percentage/decimal scaling
- repeated returns
- excessive zero returns
- very short history
- irregular frequency
- frequency changes
- stale returns
- serial correlation
- potential smoothing
- date alignment quality with benchmark
- OCR confidence when applicable

Example output:

```text
DATA QUALITY
Observations:              120
Frequency:                 Monthly
History:                   10.0 years
Missing expected periods:  0
Duplicate periods:         0
Zero-return periods:       3
Lag-1 autocorrelation:     0.31
Smoothing warning:         Moderate
```

Metrics should receive diagnostics context so confidence policies can react to poor data.

---

# 14. Applicability engine

This is one of OpenFactsheet's key differentiators.

Metric calculation and metric applicability MUST be separate.

Example rules:

```python
if metric.requires_benchmark and benchmark is None:
    status = "not_applicable"

elif n < metric.minimum_observations:
    status = "insufficient_data"

elif diagnostics.smoothing_risk == "high" and metric.id == "sharpe_ratio":
    status = "low_confidence"

elif frequency == IRREGULAR and metric.requires_annualization:
    status = "low_confidence"
```

Do not hide a metric merely because confidence is low.

Show the number when valid, plus the warning, unless the calculation is mathematically invalid.

---

# 15. Confidence engine

Do not invent arbitrary red/yellow/green classifications casually.

Create transparent confidence rules based on:

- observation count
- effective years
- missing data
- serial dependence
- frequency reliability
- benchmark overlap
- denominator stability
- degenerate values
- OCR uncertainty
- metric-specific statistical requirements

Initial confidence labels:

```text
high
moderate
low
not_assessable
```

Use labels cautiously.

Confidence indicates reliability of estimation, NOT quality of the investment.

---

# 16. Interpretation engine

Never encode "Sharpe > 2 = excellent" as universal truth without nuance.

Interpretations should have two layers:

## Plain-language

Example:

> The Sharpe Ratio compares excess return with total return variability. Higher values indicate more return per unit of measured volatility, but the statistic can be misleading when returns are smoothed, strongly skewed, serially correlated, or have significant tail risk.

## Professional notes

Example:

> Annualization assumes the detected observation frequency. Serial dependence may cause conventional square-root-of-time scaling to understate or overstate uncertainty.

Avoid investment advice.

OpenFactsheet explains measurements; it should not say "buy" or "sell."

---

# 17. Existing libraries: REUSE BEFORE REINVENTING

Claude Code MUST inspect existing implementations before implementing a metric.

The goal is NOT to blindly depend on all these libraries at runtime.

The goal is to:

1. locate established formulas,
2. compare conventions,
3. identify edge-case handling,
4. build cross-library validation tests,
5. cite sources,
6. implement a clean canonical OpenFactsheet version when necessary.

Prefer authoritative academic definitions when libraries disagree.

---

# 18. Python reference libraries

## 18.1 QuantStats

Repository:

https://github.com/ranaroussi/quantstats

Use as a reference for:

- Sharpe
- Sortino
- volatility
- max drawdown
- Calmar
- win rate
- payoff / profit factor
- gain-to-pain
- tail ratio
- VaR / CVaR
- skew / kurtosis
- Kelly-related statistics
- rolling statistics
- report organization
- drawdown plots
- monthly return tables

Important source areas:

```text
quantstats/stats.py
quantstats/utils.py
quantstats/reports.py
```

QuantStats has a broad performance analytics implementation and tear-sheet workflow.

Do NOT automatically copy its defaults. Compare definitions and edge cases.

Check license compatibility before copying code. Prefer reimplementation from mathematical definitions plus validation.

---

## 18.2 empyrical-reloaded

Repository:

https://github.com/stefan-jansen/empyrical-reloaded

Use as a primary Python cross-check for:

- cumulative returns
- annual return
- annual volatility
- max drawdown
- Sharpe
- Sortino
- alpha
- beta
- alpha/beta
- capture ratios
- rolling variants

Important source:

```text
src/empyrical/
```

Empyrical is deliberately metric-focused and is therefore a useful reference implementation.

---

## 18.3 pyfolio-reloaded

Repository:

https://github.com/stefan-jansen/pyfolio-reloaded

Use primarily as a reference for:

- tear-sheet architecture
- rolling risk statistics
- drawdown presentation
- benchmark comparison
- portfolio risk presentation
- performance attribution concepts

Do not copy the UI architecture wholesale. OpenFactsheet's core distinction is canonical metrics plus applicability metadata.

---

## 18.4 Riskfolio-Lib

Documentation:

https://riskfolio-lib.readthedocs.io/

Repository:

https://github.com/dcajasn/Riskfolio-Lib

Use as a key reference for advanced risk measures:

- semi-deviation
- lower partial moments
- CVaR
- EVaR
- Tail Gini
- maximum drawdown
- average drawdown
- CDaR
- EDaR
- Ulcer Index
- drawdown-based risk measures
- Omega-related lower-partial-moment concepts

Particularly important for broadening OpenFactsheet beyond common tear-sheet ratios.

---

## 18.5 skfolio

Documentation:

https://skfolio.org/

Repository:

https://github.com/skfolio/skfolio

Inspect:

```text
skfolio.measures
skfolio.portfolio.BasePortfolio
```

Use as a reference for:

- mean / cumulative returns
- variance and standard deviation
- semi-variance / semi-deviation
- MAD
- lower partial moments
- CVaR
- EVaR
- CDaR
- EDaR
- maximum drawdown
- average drawdown
- Ulcer Index
- Gini mean difference
- ratio measures
- factor models

skfolio is especially useful because its measures are cleanly separated and documented.

Again: OpenFactsheet must not inherit configurable optimization assumptions as defaults.

---

## 18.6 ffn

Repository:

https://github.com/pmorissette/ffn

Inspect for:

- CAGR
- Sharpe
- Sortino
- max drawdown
- performance-stat summaries
- return-series utility logic

Use mainly as a secondary cross-check.

---

## 18.7 statsmodels

Documentation:

https://www.statsmodels.org/

Use for:

- OLS
- CAPM/factor regressions
- robust/HAC covariance
- residual tests
- autocorrelation diagnostics
- statistical inference

Do NOT hand-code linear regression unless there is a compelling reason.

---

## 18.8 linearmodels

Documentation:

https://bashtage.github.io/linearmodels/

Use where appropriate for:

- factor-model regressions
- panel models
- Fama-MacBeth style workflows
- robust econometric estimation

Probably optional in early versions.

---

## 18.9 scipy

Documentation:

https://docs.scipy.org/

Use rather than reinventing:

- skew
- kurtosis
- statistical distributions
- hypothesis tests
- quantiles where appropriate
- bootstrap utilities where appropriate

---

## 18.10 numpy / pandas

These should be foundational runtime dependencies.

Use:

- NumPy for numerical kernels
- pandas for labeled time series and input interoperability

Avoid unnecessary heavyweight dependencies in the core metric engine.

---

## 18.11 Alphalens-reloaded

Repository:

https://github.com/stefan-jansen/alphalens-reloaded

Reference for factor research concepts such as:

- factor returns
- Information Coefficient
- quantile analysis
- turnover
- grouped analysis

This is not the primary library for fund factsheets, but useful if OpenFactsheet later analyzes predictive signals/factors.

---

## 18.12 arch

Repository / docs:

https://github.com/bashtage/arch

Use only for optional/model-dependent analytics such as:

- GARCH
- conditional volatility
- heteroskedasticity modeling

These should NOT be core canonical factsheet metrics initially.

---

# 19. R reference implementations

OpenFactsheet is Python, but Claude Code SHOULD use R packages as independent reference implementations.

Cross-language agreement is valuable evidence.

## 19.1 PerformanceAnalytics

Repository:

https://github.com/braverock/PerformanceAnalytics

CRAN:

https://cran.r-project.org/package=PerformanceAnalytics

This is one of the most important references in the entire project.

Inspect functions for:

- Sharpe Ratio
- Sortino Ratio
- Treynor Ratio
- Jensen alpha
- Information Ratio
- Omega
- Kappa
- Calmar
- Sterling
- Burke
- downside risk
- drawdowns
- VaR
- Expected Shortfall
- modified risk measures
- capture ratios
- skewness / kurtosis
- co-moments
- standard errors for performance/risk estimators

The package explicitly focuses on returns-based performance and risk analysis across different periodicities and normal/non-normal return streams.

Do not copy GPL code into OpenFactsheet unless the project's license strategy explicitly permits it.

Instead:

- inspect formulas,
- consult cited literature,
- reproduce formula independently,
- validate numerically against R.

This license separation is important.

---

## 19.2 PortfolioAnalytics

Repository:

https://github.com/braverock/PortfolioAnalytics

Useful primarily for:

- portfolio risk objectives
- expected shortfall
- downside-risk formulations
- risk-budgeting concepts
- portfolio-level metrics

Lower priority than PerformanceAnalytics for v0.x.

---

## 19.3 FactorAnalytics

Search CRAN/GitHub for current maintained implementation before use.

Reference concepts:

- factor exposures
- factor-model risk decomposition
- returns-based style analysis

---

## 19.4 Other R packages to inspect selectively

- `xts`
- `zoo`
- `rugarch`
- `rmgarch`
- `QRM`
- `copula`
- `evir`
- `POT`
- `moments`
- `e1071`
- `sandwich`
- `lmtest`

Only add as references where they materially improve a metric's definition or validation.

---

# 20. Formula sourcing protocol

For every new metric, Claude Code MUST follow this sequence.

## Step 1 — Identify authoritative definition

Search:

1. original paper if available
2. recognized textbook / practitioner standard
3. PerformanceAnalytics implementation/docs
4. established Python libraries

## Step 2 — Compare implementations

Build a small note such as:

```text
Metric: Sortino Ratio

PerformanceAnalytics:
- denominator convention:
- MAR convention:
- annualization:

QuantStats:
- denominator convention:
- rf handling:
- annualization:

Empyrical:
- denominator convention:
- required annualization parameter:

OpenFactsheet decision:
- canonical formula:
- canonical target:
- annualization:
- rationale:
```

## Step 3 — Implement independently

Do not paste substantial licensed source code.

Implement from the mathematical definition.

## Step 4 — Cross-library tests

Run deterministic fixtures through every available implementation.

## Step 5 — Document discrepancies

If libraries disagree, add a methodology note and regression fixture.

Never "fix" disagreement by choosing whichever produces the most attractive number.

---

# 21. Licensing rule for source inspection

Before borrowing implementation details, inspect package licenses.

Examples may include:

- Apache-2.0
- BSD
- GPL
- other open-source licenses

Do NOT copy GPL-covered implementation code into a permissively licensed project unless the chosen OpenFactsheet license and legal strategy explicitly allow it.

Mathematical formulas are not the same as copying source code.

The preferred process is:

```text
source implementation
       ↓
understand mathematical definition
       ↓
consult original literature
       ↓
write independent OpenFactsheet implementation
       ↓
cross-check numerically
```

Keep a `docs/validation/reference_implementations.md`.

---

# 22. Canonical assumptions registry

Create a machine-readable registry.

Example:

```python
CANONICAL_ASSUMPTIONS = {
    "return_type": "simple",
    "annualization": {
        "monthly": 12,
        "quarterly": 4,
        "yearly": 1,
    },
    "var_confidence": 0.95,
    "es_confidence": 0.95,
    "sortino_target_policy": "...",
    "risk_free_policy": "...",
}
```

Do NOT finalize economically controversial defaults without documenting rationale.

Treat risk-free rate policy as a major methodological decision.

Possible phases:

### v0.1

Risk-free = 0 for metrics that can conventionally be calculated that way, but prominently label the assumption.

### Later

Optional deterministic public risk-free series based on currency/region when reliable market metadata exists.

Never silently infer investor currency from computer locale.

---

# 23. Benchmark policy

Benchmark-dependent metrics must not be fabricated.

Canonical logic:

```text
benchmark explicitly supplied
    → use it

benchmark absent
    → benchmark-relative metrics = not applicable
```

Do NOT automatically infer S&P 500 merely because the investment is a fund.

Future benchmark inference may be explored, but any inferred benchmark must be labeled and must never replace explicit benchmark data.

---

# 24. Missing-data policy

Document and centralize missing-data behavior.

Rules should answer:

- Drop isolated NaNs?
- What if timestamps indicate missing months?
- Can a monthly gap be treated like zero? NO.
- How should benchmark alignment work?
- How do partial histories compare?

Never replace missing investment returns with zero.

Never forward-fill returns.

For benchmark-relative metrics, calculate on the intersection of valid dates and disclose overlap.

---

# 25. Drawdown engine design

Create one canonical wealth index:

```python
wealth_t = wealth_0 * cumprod(1 + r_t)
```

Then:

```python
peak_t = cummax(wealth_t)
drawdown_t = wealth_t / peak_t - 1
```

Use this canonical drawdown vector throughout.

Create drawdown episodes with:

```python
DrawdownEpisode(
    peak_date,
    trough_date,
    recovery_date,
    depth,
    peak_to_trough_periods,
    recovery_periods,
    total_underwater_periods,
    area,
)
```

Every drawdown metric should consume this shared object.

This prevents internal inconsistency.

---

# 26. OCR / image ingestion architecture

Image ingestion is a separate optional extra.

Do not make OCR dependencies mandatory for users who only analyze arrays.

Install pattern:

```bash
pip install openfactsheet
pip install openfactsheet[images]
pip install openfactsheet[pdf]
pip install openfactsheet[all]
```

Pipeline:

```text
image/pdf
  ↓
layout detection
  ↓
table extraction
  ↓
year/month header recognition
  ↓
cell extraction
  ↓
percentage parsing
  ↓
chronological reconstruction
  ↓
validation
  ↓
human-readable reconstructed table
  ↓
metric engine
```

The extraction stage MUST produce confidence metadata.

Never calculate silently from low-confidence OCR.

For screenshots, common target layout:

```text
       Jan   Feb   Mar ... Dec
2022   1.2% -0.3% ...
2023   ...
```

Reconstruct:

```text
2022-01  0.012
2022-02 -0.003
...
```

Preserve empty future cells.

---

# 27. OCR library research

At implementation time, evaluate current libraries rather than hard-coding a 2026 choice forever.

Candidates to investigate:

- PaddleOCR
- Tesseract / pytesseract
- EasyOCR
- docTR
- table extraction tools for PDFs
- native PDF text extraction before OCR

Policy:

1. Prefer extracting embedded PDF text/table data when present.
2. OCR only rasterized pages / screenshots.
3. Keep OCR optional.
4. Never make metric correctness depend on an opaque LLM vision call in the core library.
5. Allow pluggable extractors.

---

# 28. Report model

Create one structured report object.

```python
@dataclass
class FactsheetReport:
    input_summary: InputDiagnostics
    diagnostics: DataQualityReport
    metrics: MetricCollection
    assumptions: Methodology
    interpretations: InterpretationCollection
    benchmark_summary: BenchmarkDiagnostics | None
    provenance: Provenance
```

Rendering must be downstream.

A calculation should not know anything about HTML.

---

# 29. Output formats

v0.x priorities:

1. Python object
2. dict
3. JSON
4. terminal / text
5. Markdown
6. HTML

Later:

- PDF
- notebook rich display
- interactive web report

JSON is important because OpenFactsheet should be usable as an analytical engine by other applications.

---

# 30. Standard factsheet structure

Canonical report:

```text
OPENFACTSHEET

1. Input & methodology
2. Data-quality diagnostics
3. Return summary
4. Risk summary
5. Drawdowns
6. Risk-adjusted performance
7. Tail behavior
8. Distribution
9. Consistency
10. Benchmark-relative analysis
11. Factor analysis
12. Statistical confidence
13. Metric catalog / details
14. Assumptions & caveats
```

No single composite "Fund Score" in initial versions.

A universal score introduces arbitrary weights and can recreate the cherry-picking problem in another form.

---

# 31. Testing strategy

This library concerns financial measurement. Testing is critical.

Use:

- `pytest`
- `hypothesis`
- `numpy.testing`
- `pandas.testing`

Consider `ruff`, `mypy` or `pyright`, and coverage tooling.

---

## 31.1 Unit tests

Every metric:

- typical returns
- all positive
- all negative
- constant zero
- constant positive
- single observation
- two observations
- NaN
- infinite value
- extreme loss
- -100% return
- duplicate timestamps
- unsorted dates

---

## 31.2 Mathematical identities

Examples:

```text
all zero returns
→ cumulative return = 0
→ volatility = 0

wealth never falls below prior high
→ max drawdown = 0

identical return and benchmark series
→ beta approximately 1
→ tracking error = 0
→ active return = 0
```

Use property-based testing where possible.

---

## 31.3 Cross-library validation tests

Create tests against:

- QuantStats
- empyrical-reloaded
- Riskfolio-Lib
- skfolio
- PerformanceAnalytics (R)

These should live separately because reference dependencies may be optional.

Example:

```text
tests/cross_library/test_sharpe_quantstats.py
tests/cross_library/test_max_drawdown_empyrical.py
tests/cross_library/test_omega_performanceanalytics.py
```

Record known convention differences explicitly.

---

## 31.4 Golden tests

Maintain known return series and expected full report JSON.

```text
tests/golden/
    monthly_fund_10y.json
    negative_fund.json
    smoothed_hedge_fund.json
    benchmark_case.json
```

Any change to these outputs requires conscious review.

---

## 31.5 R validation harness

Create optional tooling such as:

```text
validation/r/
    performanceanalytics_reference.R
```

It should read standardized fixtures and output JSON/CSV reference values.

Do not make R a runtime dependency.

Use it during development/CI reference checks where available.

---

# 32. Numerical precision

Default calculations should use NumPy `float64`.

Do not round before calculation.

Round only at presentation.

Store raw metric value.

Example:

```python
value = 1.2384729384
display = "1.24"
```

Do not claim unnecessary precision.

---

# 33. Error handling

Define package exceptions:

```python
OpenFactsheetError
InputError
AmbiguousReturnScaleError
FrequencyInferenceError
BenchmarkAlignmentError
MetricCalculationError
OCRExtractionError
```

Most metric-specific failures should be captured into `MetricResult` rather than crashing the entire report.

Input corruption should fail early.

---

# 34. Performance

Correctness first.

A fund factsheet usually contains hundreds or thousands of observations, not billions.

Avoid premature optimization.

Vectorize obvious operations.

Cache shared quantities:

- wealth index
- drawdown vector
- downside returns
- moments
- aligned benchmark
- annualization information

Use a `MetricContext`:

```python
@dataclass
class MetricContext:
    returns: ReturnSeries
    benchmark: ReturnSeries | None
    diagnostics: DataQualityReport
    methodology: Methodology
    cache: MetricCache
```

---

# 35. Documentation generation

Metric documentation should be generated partly from registry metadata.

Each metric definition should include:

```python
references = [
    AcademicReference(...),
    LibraryReference(...),
]
```

Then generate:

```text
docs/interpretation/sharpe_ratio.md
```

or equivalent catalog entries.

Avoid documentation drifting from code.

---

# 36. Provenance

Reports should expose:

```text
OpenFactsheet package version
Methodology version
Input type
Input date range
Detected frequency
Annualization convention
Benchmark identity if supplied
Number of observations
Transformations applied
Warnings
```

For OCR:

```text
Source image hash
Extraction engine/version
Cells with low confidence
```

Do not collect personal data remotely by default.

---

# 37. Privacy

Core OpenFactsheet should be local-first.

A user analyzing a private hedge-fund return history should not unknowingly upload it to a third party.

If future cloud/LLM integrations exist:

- opt-in only,
- clearly documented,
- not required for core calculations.

---

# 38. Dependency philosophy

Core runtime should be lean.

Likely core:

```text
numpy
pandas
scipy
statsmodels
```

Potential optional/reference dependencies:

```text
quantstats
empyrical-reloaded
riskfolio-lib
skfolio
pyarrow
openpyxl
OCR tools
PDF extraction tools
```

Do not add another package merely to calculate one trivial formula.

Do not reinvent robust scientific computing already provided by NumPy/SciPy/statsmodels.

---

# 39. Development phases

## Phase 0 — Foundation

Deliver:

- package skeleton
- pyproject
- formatting/linting/testing
- typed data models
- normalized return input
- frequency inference
- methodology version
- metric registry
- JSON report skeleton

No pretty report required.

---

## Phase 1 — Core metrics

Implement and validate approximately 30 foundational metrics:

- cumulative return
- CAGR
- mean
- median
- volatility
- downside deviation
- Sharpe
- Sortino
- max drawdown
- average drawdown
- current drawdown
- drawdown duration
- Ulcer Index
- Calmar
- Martin/UPI
- Omega
- skew
- kurtosis
- VaR
- Expected Shortfall
- tail ratio
- best/worst period
- positive-period ratio
- Gain-to-Pain
- autocorrelation
- zero-return diagnostic
- alpha
- beta
- correlation
- tracking error
- Information Ratio

Cross-check each metric.

---

## Phase 2 — Full metric catalog

Expand toward 75–150 metrics.

Add:

- Kappa
- Sterling
- Burke
- modified ratios
- capture ratios
- lower partial moments
- CDaR
- EDaR
- advanced tail statistics
- statistical confidence metrics
- more complete path metrics

---

## Phase 3 — Applicability + confidence

Implement:

- metric-specific minimum data rules
- data-quality impact
- benchmark requirements
- model-dependent labels
- estimation-confidence warnings

This phase is central to product differentiation.

---

## Phase 4 — Reporting

Create canonical:

- terminal
- Markdown
- HTML
- JSON

Add charts:

- cumulative wealth
- underwater
- drawdown episodes
- monthly heatmap
- return distribution
- rolling statistics

Charts must not hide inconvenient periods.

---

## Phase 5 — Comparison engine

Implement:

```python
ofs.compare(...)
```

Ensure identical methodology for all investments.

Align:

- common reporting metadata
- category-by-category metric comparison
- track-record differences
- benchmark differences
- confidence differences

Do not rank metrics where ranking is misleading.

---

## Phase 6 — Image/PDF ingestion

Add optional extraction pipeline.

Start with monthly-return tables.

Prioritize reliability over general document understanding.

---

## Phase 7 — Factor analysis

Add CAPM and multi-factor models.

Keep data acquisition separate from analytics.

Do not make Fama-French downloads mandatory.

---

# 40. Initial priority metric catalog

Create `docs/metric_catalog.md` before implementing all metrics.

Each row:

```text
ID
Name
Category
Formula status
Reference implementation
Academic reference
Dependencies
Benchmark required?
Annualized?
Canonical parameters
Minimum-data policy
Implementation status
Validation status
```

This becomes the implementation backlog.

---

# 41. Important methodological questions to document, not hide

Before v1.0, OpenFactsheet must explicitly decide:

- arithmetic vs geometric annual return conventions
- sample vs population standard deviation conventions
- annualization under serial correlation
- risk-free treatment
- Sortino MAR/target convention
- Omega threshold
- VaR confidence
- ES confidence
- exact quantile interpolation
- downside deviation denominator
- minimum track record
- benchmark alignment
- missing values
- monthly table partial years
- return scale detection
- -100% return behavior
- non-finite return behavior
- compounding after total loss
- irregular time series
- crypto/non-business-day data

Never bury these choices inside functions.

---

# 42. Do not confuse observed and modeled statistics

Tag metric definitions:

```text
observed
derived
estimated
model_dependent
```

Examples:

Observed / path-derived:

- max drawdown
- worst month
- cumulative return

Estimated:

- annualized mean
- annualized volatility

Model-dependent:

- CAPM alpha
- parametric VaR
- GARCH volatility

The report should make this distinction visible.

---

# 43. Anti-marketing design rules

OpenFactsheet exists partly to resist selective fund marketing.

Therefore:

- Do not hide negative periods.
- Do not choose start dates for favorable results.
- Do not automatically suppress max drawdown.
- Do not default to only volatility-based metrics.
- Always include downside/path/tail analysis when enough data exist.
- Always disclose track-record length.
- Always disclose benchmark overlap.
- Always disclose annualization assumptions.
- Always disclose material data-quality warnings.
- Do not let HTML templates remove canonical sections through a casual flag.

Advanced custom rendering may exist, but canonical reports should remain identifiable as canonical.

---

# 44. Claude Code working instructions

When implementing any feature:

1. Read this `CLAUDE.md`.
2. Locate the relevant metric definition in the registry/backlog.
3. Research existing implementations before coding.
4. Identify formula disagreements.
5. Add/modify methodology documentation.
6. Implement the simplest correct independent formula.
7. Add edge-case unit tests.
8. Add at least one reference-validation test when possible.
9. Run the full test suite.
10. Do not change unrelated metrics.
11. Do not introduce hidden user-tunable parameters.
12. Do not silently change methodology.
13. Do not remove unfavorable metrics from reports.
14. Preserve backward compatibility unless explicitly making a major release.

---

# 45. When Claude Code finds multiple formulas

Do not guess.

Create a short design note under:

```text
docs/methodology/decisions/
```

Example:

```text
0003-sortino-downside-deviation.md
```

Include:

```text
Problem
Known definitions
PerformanceAnalytics behavior
QuantStats behavior
Empyrical behavior
Academic sources
OpenFactsheet decision
Rationale
Consequences
```

Then implement the documented decision.

---

# 46. Definition of done for a metric

A metric is NOT done merely because the function runs.

It is done when:

- [ ] formula is documented
- [ ] authoritative reference exists
- [ ] implementation is typed
- [ ] edge cases are tested
- [ ] applicability rule exists
- [ ] confidence rule exists or explicitly says none
- [ ] assumptions are recorded
- [ ] interpretation exists
- [ ] cross-library comparison exists where possible
- [ ] known convention differences are documented
- [ ] metric appears correctly in canonical report
- [ ] JSON serialization works
- [ ] no unexplained NaN/inf behavior remains

---

# 47. Initial implementation order

Start here:

```text
A. Repository/package skeleton
B. ReturnSeries + InputDiagnostics
C. normalization
D. frequency inference
E. methodology registry
F. MetricResult + MetricDefinition
G. metric registry
H. cached wealth/drawdown engine
I. return metrics
J. volatility/downside
K. drawdown metrics
L. Sharpe/Sortino/Calmar/Omega/Martin
M. distribution/tail
N. data-quality diagnostics
O. applicability engine
P. benchmark alignment
Q. alpha/beta/IR/Treynor
R. JSON report
S. terminal/Markdown report
T. cross-library validation harness
```

Do not start with OCR.

The numerical engine and methodology must be trustworthy first.

---

# 48. First acceptance test

This must work cleanly:

```python
import pandas as pd
import openfactsheet as ofs

returns = pd.Series(
    [0.01, -0.02, 0.015, 0.005, -0.01, 0.03],
    index=pd.date_range("2025-01-31", periods=6, freq="ME"),
)

report = ofs.analyze(returns)

print(report.summary())
```

Expected behavior:

- recognizes monthly frequency
- records six observations
- calculates all mathematically valid metrics
- marks unreliable metrics as low-confidence/insufficient-data
- does not crash because history is short
- explains annualization
- explains why benchmark metrics are unavailable
- produces stable JSON

---

# 49. Second acceptance test: benchmark

```python
report = ofs.analyze(
    fund_returns,
    benchmark=benchmark_returns,
)
```

Expected:

- aligns on common timestamps
- reports alignment loss
- computes beta, alpha, correlation, tracking error, Information Ratio, capture measures, Treynor where valid
- does not fill missing benchmark returns with zero
- stores benchmark-dependent observation count separately

---

# 50. Third acceptance test: suspicious hedge-fund series

Create fixture with:

- monthly data
- unusually low volatility
- many tiny positive returns
- high lag-1 autocorrelation
- occasional large loss

OpenFactsheet should:

- compute Sharpe
- flag smoothing/serial-correlation concerns
- avoid presenting high Sharpe as unquestioned evidence of quality
- show drawdown/tail metrics prominently
- label confidence appropriately

This embodies "approximately right rather than exactly wrong."

---

# 51. Fourth acceptance test: monthly return screenshot

Later:

```python
report = ofs.analyze("monthly_returns.png")
```

Expected:

1. extract table
2. reconstruct month sequence
3. show reconstructed returns
4. identify OCR uncertainties
5. refuse canonical metric calculation when extraction confidence is materially inadequate
6. otherwise calculate identical metrics to the same manually supplied series

---

# 52. Long-term goal

OpenFactsheet should make this possible:

```python
ofs.analyze(any_reasonable_return_history)
```

and answer:

> "What does this investment's performance actually look like under one transparent, standardized methodology?"

not:

> "Which metrics would you like me to show?"

That distinction is the project.

---

# 53. Project tagline

**OpenFactsheet — standardized, transparent investment performance analytics without metric cherry-picking.**

---

# 54. Final architectural principle

OpenFactsheet should be opinionated about **methodology**, but humble about **inference**.

The library should calculate aggressively, interpret cautiously, disclose assumptions, expose uncertainty, and never manufacture certainty that the data cannot support.

---

# 55. Sources

OpenFactsheet references are references for established definitions, not sources from which code should be automatically be copied.

