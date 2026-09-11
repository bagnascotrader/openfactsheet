# Getting started

## Install

```bash
git clone https://github.com/bagnascotrader/openfactsheet.git
cd openfactsheet
pip install -e ".[excel]"
```

Core dependencies: NumPy, pandas, SciPy, statsmodels. Excel input needs the
`excel` extra (openpyxl).

## Analyze a return history

```python
import pandas as pd
import openfactsheet as ofs

returns = pd.read_csv("examples/monthly_table.csv")  # wide Year x Jan..Dec table
report = ofs.analyze(returns, name="Example fund")
print(report.summary())
```

Accepted inputs:

| Input | Notes |
|---|---|
| `list`, `tuple`, `numpy.ndarray` | Undated: frequency is unknown, so nothing is annualized unless you declare `frequency="monthly"` (recorded as a declaration). |
| `pandas.Series` | A `DatetimeIndex` or `PeriodIndex` lets OpenFactsheet infer frequency from calendar spacing. |
| `pandas.DataFrame` | One return column → `analyze`; several columns → `compare`. A date column is detected by name or content. |
| CSV / Excel path | Same layouts as DataFrames, including wide monthly tables. |
| Pasted text | A multi-line string, e.g. a monthly table copied from a PDF. |

Percent vs decimal scale is detected deterministically. If the values are
genuinely ambiguous, OpenFactsheet raises `AmbiguousReturnScaleError` instead of
guessing; declare `return_scale="percent"` or `"decimal"`.

## Read a report

```python
report.input_summary  # what OpenFactsheet believes it received
report.returns_frame()  # the exact decimal returns analyzed
report.diagnostics  # data-quality findings, smoothing risk
report.metrics  # every canonical metric
report.assumptions  # the methodology (version + conventions)
report.interpretations["sharpe_ratio"].plain
```

Each metric is a `MetricResult`:

```python
m = report.metrics["sharpe_ratio"]
m.value  # float, or None when not computable
m.status  # applicable | low_confidence | supplementary | not_applicable | insufficient_data | error
m.confidence  # high | moderate | low | not_assessable (estimation reliability, not quality)
m.reason  # why there is no value
m.warnings  # data-specific caveats
m.assumptions  # e.g. risk-free rate 0%, annualization factor
```

Values are raw `float64`; rounding happens only in rendered reports.

## Benchmarks

```python
report = ofs.analyze(fund, benchmark=benchmark)
report.benchmark_summary  # aligned observations, dropped periods, overlap
```

Fund and benchmark are aligned on their common periods (monthly data by
calendar month, so month-start and month-end dates match). Missing benchmark
returns are never filled. Benchmark-relative metrics report their own
observation count. Without a benchmark they are `not_applicable` with a reason —
OpenFactsheet never assumes a default benchmark.

## Compare investments

```python
cmp = ofs.compare({"Fund A": fund_a, "Fund B": fund_b})
cmp.table()  # metric x investment values
cmp.track_records()  # history lengths, frequency, smoothing risk
cmp.table(common_period=True)  # same metrics on the common period, if histories differ
```

Comparisons are never ranked.

## Export

```python
report.to_json("factsheet.json")  # deterministic, NaN-free, methodology embedded
report.to_markdown("factsheet.md")
report.to_html("factsheet.html")
```

## Explore the methodology

```python
ofs.methodology().describe()  # canonical conventions
ofs.metric_catalog()  # DataFrame of all metrics and their definitions
```
