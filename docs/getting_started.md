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
| Screenshot or scanned PDF | `ofs.analyze("table.png")` with `pip install "openfactsheet[ocr]"`: recognized locally (no network) and accepted only when every year reconciles with its printed YTD; otherwise refused with the table as read. `ofs.load(path, ocr_engine="tesseract")` uses Tesseract instead. |
| PDF factsheet | `ofs.analyze("factsheet.pdf")` with `pip install "openfactsheet[pdf]"`: the monthly-return table is read from the embedded text, checked against its YTD column, and refused (with the reconstructed table) if anything is inconsistent. Pages without embedded text are recognized by OCR when the `ocr` extra is installed. |

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

## Factor models

Supply factor returns explicitly (OpenFactsheet never downloads them): a dated
DataFrame, CSV/Excel file or table text with one column per factor. A column
named `RF` is treated as the risk-free rate and subtracted from fund returns.

```python
factors = pd.read_csv("my_factors.csv", index_col="date", parse_dates=True)
# columns: Mkt-RF, SMB, HML, RF  (percent or decimal: one scale is detected for all)
report = ofs.analyze(fund_returns, factors=factors)
report.factor_analysis.fit.loadings  # every loading with Newey-West SE, t, p, 95% CI
report.metrics["factor_alpha"]  # annualized alpha; details hold the interval
```

Only the months where the fund and every factor have a value are used (never
filled). Standard errors are Newey-West with a fixed lag rule
([decision 0028](methodology/decisions/0028-factor-models.md)).

## Export

```python
report.to_json("factsheet.json")  # deterministic, NaN-free, methodology embedded
report.to_markdown("factsheet.md")
report.to_html("factsheet.html")  # self-contained, with the canonical charts
report.charts()  # {"wealth": "<svg ...>", "underwater": ..., ...}
```

The HTML report contains eight canonical charts (growth of 1, calendar-year
returns, monthly heatmap, rolling one-year volatility, underwater chart, return
distribution, rolling one-year return and, with a benchmark, growth over the
aligned overlap), each with a caption and a data table. Every chart spans the
full history and follows the fixed presentation rules of
[decision 0026](methodology/decisions/0026-canonical-charts.md); a chart that
cannot be drawn for the data is replaced by the reason.

## Explore the methodology

```python
ofs.methodology().describe()  # canonical conventions
ofs.metric_catalog()  # DataFrame of all metrics and their definitions
```

## Follow a number to its definition

Every result links to the page of the
[reference manual](manual/README.md) that defines it — formula, inputs,
assumptions, when it misleads, and the papers and reference implementations it
comes from ([decision 0035](methodology/decisions/0035-linking-results-to-the-manual.md)):

```python
report.metrics["sharpe_ratio"].documentation
# '.../openfactsheet-manual.pdf#nameddest=metric-sharpe_ratio'

report.documentation.manual  # the manual of the version that produced the report
report.documentation.catalog  # the metric catalog at that version
```

The Markdown and HTML reports link every metric name, the JSON carries the link
on every metric and a `documentation` block, and the terminal report gives the
address of the manual. The links are pinned to the version that computed the
numbers, so an archived report always points at the conventions it actually
used, not at whatever the documentation says later.
