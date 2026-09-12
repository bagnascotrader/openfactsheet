<div align="center">

<img src="docs/assets/openfactsheet_logo.png" alt="OpenFactsheet: See the full picture. No cherry-picking. Just performance." width="440">

<h3>An open standard for investment performance measurement.</h3>

One function call. One versioned methodology. Every metric, including the unflattering ones.

[![CI](https://github.com/bagnascotrader/openfactsheet/actions/workflows/ci.yml/badge.svg)](https://github.com/bagnascotrader/openfactsheet/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-0B3C7D?logo=python&logoColor=white)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache--2.0-0B3C7D)](LICENSE)
[![Methodology](https://img.shields.io/badge/methodology-0.1.0-0E7C86)](docs/methodology.md)
[![Metrics](https://img.shields.io/badge/canonical%20metrics-90-10A37F)](docs/metric_catalog.md)
[![Typed](https://img.shields.io/badge/mypy-strict-10A37F)](pyproject.toml)
[![Status](https://img.shields.io/badge/status-alpha-C98A00)](CHANGELOG.md)

**[Quick start](#quick-start)** &nbsp;·&nbsp;
**[Why OpenFactsheet](#why-openfactsheet)** &nbsp;·&nbsp;
**[Example](#a-sharpe-ratio-of-238-and-why-you-should-not-trust-it)** &nbsp;·&nbsp;
**[Metrics](#90-metrics-one-methodology)** &nbsp;·&nbsp;
**[Methodology](docs/methodology.md)** &nbsp;·&nbsp;
**[Docs](#documentation)** &nbsp;·&nbsp;
**[Roadmap](#roadmap)**

</div>

---

OpenFactsheet takes an investment's return history and produces **one canonical,
fully documented performance analysis**. You do not pick the metrics, the window,
the threshold or the confidence level. A versioned methodology picks them, and it
picks the same ones for every investment. Each number carries its assumptions, a
confidence label, and a warning when the data cannot support it.

```python
import openfactsheet as ofs

report = ofs.analyze(returns)
```

That one call gives you 94 metrics, data-quality diagnostics, a 14-section
report, and JSON output that is stable and never contains a `NaN`.

> [!NOTE]
> **Status: alpha (methodology 0.1.0).** The numerical core is implemented and
> cross-validated against independent R and Python implementations.
> PDF/screenshot ingestion is on the [roadmap](#roadmap).

## Why OpenFactsheet

A performance factsheet is a series of choices: which metrics to show, from which
start date, against which benchmark, with which risk-free rate and which
confidence level. The people making those choices are usually the people selling
the fund. OpenFactsheet makes all of them in advance, documents each one, and
applies them the same way to every return stream.

| | Typical factsheet | OpenFactsheet |
| :-- | :-- | :-- |
| **Metrics shown** | Selected by the issuer | All 94 canonical metrics, in every report |
| **Periods** | Selected by the issuer | Full history, complete calendar years, every rolling one-year window |
| **Assumptions** | Unstated or in the fine print | Versioned, and embedded in every report and every metric |
| **Drawdowns & tail risk** | Often left out | Always computed: 15 drawdown and 7 tail-risk measures |
| **Data problems** | Not visible | Diagnosed: missing periods, stale prices, outliers, return smoothing |
| **Unreliable estimates** | Shown as fact | Shown with a confidence label and the reason |
| **Metrics that can't be computed** | Left out without comment | Listed with a status and an explanation |

### Principles

- **Compute everything, hide nothing.** Every canonical metric is computed for
  every report. A metric that cannot be computed is still listed, with the reason.
- **No hand-picked periods.** Since-inception, complete calendar years, and
  rolling windows over every start date. No start date gets chosen because it
  makes the numbers look better.
- **No knobs, but no hidden assumptions either.** Annualization is inferred from
  calendar spacing, never from the number of observations. The risk-free rate,
  VaR confidence, Sortino target and every other convention come from a
  [versioned methodology](docs/methodology.md) that is written into each report.
- **No unexplained `NaN`.** Every result is a structured `MetricResult` with a
  `status`, a `confidence`, `warnings`, `assumptions` and a `formula_id`.
- **Careful about inference.** Diagnostics such as serial correlation, smoothing,
  outliers, short history and missing data feed a transparent confidence engine.
  Confidence describes how reliable an *estimate* is. It says nothing about the
  quality of the *investment*.
- **Local-first.** Everything runs on your machine. Nothing is uploaded, and no
  commercial data source is needed.

## Quick start

```bash
git clone https://github.com/bagnascotrader/openfactsheet.git
cd openfactsheet
pip install -e ".[excel]"          # PyPI release pending
```

```python
import pandas as pd
import openfactsheet as ofs

returns = pd.Series(
    [0.01, -0.02, 0.015, 0.005, -0.01, 0.03],
    index=pd.date_range("2025-01-31", periods=6, freq="ME"),
)

report = ofs.analyze(returns)

print(report.summary())  # canonical 14-section terminal report
report.to_json("factsheet.json")  # deterministic, NaN-free JSON
report.to_html("factsheet.html")  # self-contained HTML with charts
report.to_markdown("factsheet.md")  # Markdown
report.metrics["sharpe_ratio"]  # value, status, confidence, warnings, assumptions
```

Add a benchmark or factor returns, or compare several investments under the same methodology:

```python
report = ofs.analyze(fund_returns, benchmark=benchmark_returns)

# Factor models use factor returns you supply: a dated DataFrame with one column per
# factor, e.g. Mkt-RF, SMB, HML and an RF column (subtracted from fund returns)
report = ofs.analyze(fund_returns, factors=ff_factors)

comparison = ofs.compare({"Fund A": fund_a, "Fund B": fund_b, "ETF": etf})
print(comparison.summary())  # side by side, never ranked
```

With six months of data, as in the first example, OpenFactsheet does not
crash and does not overstate anything. It detects monthly frequency, computes
every metric the data allow, labels them `low` confidence, explains the
annualization, and states that benchmark metrics are unavailable because no
benchmark was supplied.

## A Sharpe ratio of 2.38, and why you should not trust it

The repository includes an eight-year monthly fixture shaped like many hedge-fund
track records: lots of small, steady gains, low measured volatility, and an
occasional sharp loss. A marketing factsheet would put the Sharpe ratio on the
front page.

```python
report = ofs.analyze("tests/fixtures/smoothed_hedge_fund.csv")

sharpe = report.metrics["sharpe_ratio"]
sharpe.value  # 2.377
sharpe.status  # 'low_confidence'
sharpe.warnings
# ('High serial correlation suggests smoothed or stale returns; measured
#   volatility is likely understated and this metric overstated.',
#  'Returns are far from normal (skewness -3.17, excess kurtosis 12.52);
#   volatility does not capture tail risk. See the drawdown and tail sections.')
```

The number is still reported, because OpenFactsheet never hides a result. It is
simply not presented on its own:

```text
2. DATA-QUALITY DIAGNOSTICS
-----------------------------------------------------------------------------------
  Observations:              96
  Frequency:                 monthly
  History:                   8.0 years
  ...
  Lag-1 autocorrelation:     0.54
  Smoothing risk:            high
  Findings:
    [warning] 4 return(s) are extreme relative to the rest of the series (robust
        z-score > 5). Check for data errors; they are kept in all calculations.
    [warning] High return-smoothing / serial-correlation risk. Lag-1 autocorrelation
        0.54 (approx. z = 5.28 with 96 observations). Rule: high if >= 0.30 and
        z >= 1.96; moderate if >= 0.15 and z >= 1.645. Volatility-based metrics
        (volatility, Sharpe, Sortino, Information Ratio) may overstate
        risk-adjusted performance.
```

Next to it the report shows the path and the tail: an **8.85% maximum
drawdown**, a **−4.50% worst month**, skewness of **−3.17**, and the full
drawdown-episode table. The rule behind each warning is printed with it, and
every threshold is listed in the [decision criteria](docs/reference/criteria.md).

## What you get

Every report has the same 14 sections, in the same order. There is no option to
leave one out.

| | | | |
| :-- | :-- | :-- | :-- |
| **1** | Input & methodology | **8** | Distribution |
| **2** | Data-quality diagnostics | **9** | Consistency |
| **3** | Return summary | **10** | Benchmark-relative analysis |
| **4** | Risk summary | **11** | Factor analysis |
| **5** | Drawdowns | **12** | Statistical confidence |
| **6** | Risk-adjusted performance | **13** | Metric catalog |
| **7** | Tail behavior | **14** | Assumptions & caveats |

Every metric is a structured, serializable result. Nothing is a bare float:

```python
MetricResult(
    id="sharpe_ratio",
    value=0.968,
    status="low_confidence",  # applicable, supplementary, not_applicable, ...
    confidence="low",  # high, moderate, low, not_assessable
    nature="estimated",  # observed, derived, estimated, model_dependent
    formula_id="sharpe_ratio@v1",
    methodology_version="0.1.0",
    assumptions=(
        "Risk-free rate assumed to be 0% (methodology 0.1.0) ...",
        "Sample standard deviation (n - 1 denominator).",
        "Annualized with 12 periods per year (monthly frequency, inferred from dates).",
    ),
    warnings=("Only 0.5 years of history (< 3 years).", ...),
)
```

**Output formats:** Python objects · `dict` · JSON · terminal · Markdown · HTML ·
pandas (`report.metrics.to_frame()`, `report.returns_frame()`).

## 94 metrics, one methodology

| Category | Count | Includes |
| :-- | :-: | :-- |
| **Returns** | 10 | Cumulative, CAGR, arithmetic & geometric mean, median, best/worst period, gain-to-pain, payoff ratio |
| **Volatility & downside** | 7 | Volatility, downside deviation, semi-deviation, MAD, IQR, downside potential (LPM 1) |
| **Drawdowns** | 15 | Max/average/median/current drawdown, durations, recovery time, time under water, Ulcer & Pain indices, DaR, CDaR, EDaR |
| **Risk-adjusted** | 11 | Sharpe, Sortino, Calmar, Martin (UPI), Omega, Kappa 3, upside potential, Burke, Sterling, Pain ratio, recovery factor |
| **Tail risk** | 7 | Historical, Gaussian and Cornish-Fisher VaR; historical and modified Expected Shortfall; entropic VaR; tail ratio |
| **Distribution** | 3 | Skewness, excess kurtosis, Jarque-Bera |
| **Consistency** | 10 | Hit rate, winning/losing streaks, calendar-year and rolling one-year statistics |
| **Serial dependence** | 5 | Autocorrelation (lags 1 to 3), Ljung-Box, zero-return share |
| **Benchmark-relative** | 18 | Beta, CAPM alpha, R², correlation, tracking error, active return, Information, Treynor & appraisal ratios, M², up/down capture and capture ratio, batting average, residual volatility, bull/bear beta, timing ratio |
| **Factor models** | 4 | Multi-factor alpha with Newey-West t-statistic, R², residual volatility; every loading with standard error, t, p and 95% interval (CAPM, Fama-French, Carhart or custom factors you supply) |
| **Statistical confidence** | 4 | Probabilistic Sharpe Ratio, Sharpe standard error, Minimum Track Record Length, standard error of the mean |

Every metric has its own documentation page covering what it measures, its exact
formula, the inputs it needs, whether higher is better, a plain-language and a
professional interpretation, its assumptions, when it misleads, the minimum
sensible data, and its academic and library references. See the
**[metric catalog](docs/metric_catalog.md)**.

## Inputs

| Input | Support |
| :-- | :-- |
| Python lists and tuples, NumPy arrays | ✅ |
| pandas `Series` / `DataFrame` | ✅ |
| CSV files | ✅ |
| Excel files | ✅ `pip install -e ".[excel]"` |
| Wide monthly tables (Year × Jan…Dec, `%` labels understood) | ✅ |
| Pasted table text | ✅ |
| Price / NAV levels | Detected and flagged, never silently treated as returns |
| PDF factsheets, screenshots of monthly-return tables | Planned (roadmap phase 6, with extraction confidence) |

The percent-or-decimal scale is detected by a deterministic classifier, and
frequency is inferred from calendar spacing. `report.input_summary` and
`report.returns_frame()` show exactly which returns OpenFactsheet thinks it
received.

## Validated, not just asserted

- **Cross-library agreement.** Metrics are checked numerically against
  [R PerformanceAnalytics](https://github.com/braverock/PerformanceAnalytics),
  [empyrical-reloaded](https://github.com/stefan-jansen/empyrical-reloaded),
  [QuantStats](https://github.com/ranaroussi/quantstats) and
  [skfolio](https://github.com/skfolio/skfolio). Where their conventions differ,
  the difference is documented and pinned by a test. See
  [reference implementations](docs/validation/reference_implementations.md).
- **Independent implementations.** Formulas are implemented from their academic
  definitions, not copied from other libraries' source code.
- **28 methodology decision records.** Every contested convention (sample vs.
  population deviation, VaR quantile interpolation, the Sortino denominator,
  drawdown episode definitions, partial calendar years, and so on) has a written
  [decision](docs/methodology/decisions/README.md) with its rationale.
- **Tests at every level.** Unit, property-based (Hypothesis), golden-report,
  acceptance and cross-library tests, run in CI on Linux (Python 3.10 to 3.13)
  and Windows. Type-checked with `mypy --strict`.

## Documentation

| | |
| :-- | :-- |
| **Start here** | [Getting started](docs/getting_started.md) · [Methodology](docs/methodology.md) · [Assumptions](docs/assumptions.md) |
| **Metrics** | [Metric catalog](docs/metric_catalog.md): one page per metric |
| **Specification** | [Exact formulas](docs/reference/formulas.md) · [Notation](docs/reference/notation.md) · [Decision criteria](docs/reference/criteria.md) · [Policies & thresholds](docs/reference/policies.md) · [JSON schema](docs/reference/report_schema.md) |
| **Rationale** | [Methodology decisions](docs/methodology/decisions/README.md) |
| **Validation** | [Reference implementations & validation](docs/validation/reference_implementations.md) |

## Roadmap

| Phase | Scope | Status |
| :-- | :-- | :-- |
| 0 | Foundation: typed models, normalization, frequency inference, metric registry | ✅ Done |
| 1 | Core metrics, cross-validated | ✅ Done |
| 2 | Full metric catalog: variance-ratio diagnostics, bootstrap uncertainty and further additions | 🚧 94 metrics so far |
| 3 | Applicability and confidence engine | ✅ Done |
| 4 | Reporting: terminal, Markdown, HTML, JSON; canonical charts and drawdown-episode table | ✅ Done |
| 5 | Comparison engine (`ofs.compare`) | ✅ Done |
| 6 | Optional PDF and screenshot ingestion with extraction confidence | Planned |
| 7 | Factor models (CAPM, Fama-French, Carhart, custom) using factor data you supply | ✅ Done |

## Development

```bash
python -m venv .venv && . .venv/bin/activate      # keep the venv out of synced folders
pip install -e ".[dev,validation]"
pytest                                            # unit, property, golden, cross-library
ruff check . && ruff format --check . && mypy
python scripts/generate_docs.py --check           # generated docs up to date
```

Contributions are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) describes the
formula-sourcing protocol and a metric's definition of done: documented formula,
authoritative reference, edge-case tests, applicability and confidence rules,
and cross-library validation.

## Citing

If you use OpenFactsheet in research, please cite it using
[`CITATION.cff`](CITATION.cff) and **state the methodology version** shown in
your results, so that others can reproduce them.

## About

OpenFactsheet was created by **Prof. Andrés A. Bagnasco** of
**UCU Business School** in September 2026. It is developed in the open, and
contributions from practitioners, academics and developers are welcome.

## License

[Apache-2.0](LICENSE).

<sub>OpenFactsheet explains measurements. It does not give investment advice, and
nothing it produces is a recommendation to buy or sell any investment.</sub>
