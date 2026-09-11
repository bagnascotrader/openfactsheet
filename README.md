# OpenFactsheet

**Standardized, transparent investment performance analytics without metric cherry-picking.**

OpenFactsheet takes an investment return history and produces one canonical,
fully documented performance analysis. You do not choose metrics, windows,
thresholds or confidence levels: the versioned methodology does, identically
for every investment. Every number comes with its assumptions, a confidence
label, and warnings when the data cannot support it.

> Status: alpha (methodology 0.1.0). The numerical core is implemented and
> cross-validated; charts, PDF/image ingestion and factor models are on the
> roadmap.

## Quick start

```bash
pip install -e ".[excel]"        # from a clone; PyPI release pending
```

```python
import pandas as pd
import openfactsheet as ofs

returns = pd.Series(
    [0.01, -0.02, 0.015, 0.005, -0.01, 0.03],
    index=pd.date_range("2025-01-31", periods=6, freq="ME"),
)

report = ofs.analyze(returns)
print(report.summary())  # canonical terminal report
report.to_json("factsheet.json")  # stable, NaN-free JSON
report.to_html("factsheet.html")  # static HTML
report.metrics["sharpe_ratio"]  # value, status, confidence, warnings, assumptions
```

With a benchmark, and for several investments:

```python
report = ofs.analyze(fund_returns, benchmark=benchmark_returns)

comparison = ofs.compare({"Fund A": fund_a, "Fund B": fund_b, "ETF": etf})
print(comparison.summary())  # side by side, never ranked
```

Inputs can be lists, NumPy arrays, pandas Series/DataFrames, CSV or Excel files,
wide monthly-return tables (Year × Jan…Dec, `%` labels understood) and pasted
table text. OpenFactsheet shows exactly which returns it believes it received
(`report.input_summary`, `report.returns_frame()`).

## What makes it different

- **Compute all, hide nothing.** Every canonical metric is computed for every
  report — drawdown, tail and downside statistics included. Metrics that cannot
  be computed are reported with a status and a reason, never silently dropped.
- **No unexplained NaN.** Each result is a structured `MetricResult` with
  `status` (`applicable`, `low_confidence`, `supplementary`, `not_applicable`,
  `insufficient_data`, `error`), `confidence`, `warnings` and `assumptions`.
- **Parameter-less, not assumption-less.** Annualization is inferred from
  calendar spacing (never from the number of observations); risk-free rate, VaR
  confidence, Sortino target and every other convention come from a versioned
  [methodology](docs/methodology.md) embedded in each report.
- **Humble about inference.** Data-quality diagnostics (missing periods, stale
  prices, outliers, serial correlation, return smoothing) feed a transparent
  confidence engine. A smoothed hedge-fund series with a high Sharpe ratio is
  shown — and flagged as low confidence.
- **Validated.** Metrics are cross-checked against R PerformanceAnalytics,
  empyrical-reloaded and QuantStats; every convention difference is documented
  and pinned by a test ([reference implementations](docs/validation/reference_implementations.md)).

## Metric coverage (methodology 0.1.0)

48 metrics across returns, volatility, drawdowns, risk-adjusted ratios, tail
risk, distribution shape, consistency, serial dependence and
benchmark-relative analysis. See the [metric catalog](docs/metric_catalog.md);
each metric has a page answering what it measures, its formula, assumptions,
when it misleads, minimum data, references and the OpenFactsheet convention.

## Documentation

- [Getting started](docs/getting_started.md)
- [Methodology](docs/methodology.md) and [assumptions](docs/assumptions.md)
- [Methodology decisions](docs/methodology/decisions/README.md)
- [Metric catalog](docs/metric_catalog.md)
- [Reference implementations & validation](docs/validation/reference_implementations.md)

## Roadmap

1. Phase 2 — broader catalog (Kappa, Sterling, Burke, CDaR/EDaR, lower partial
   moments, Probabilistic/Deflated Sharpe, confidence intervals).
2. Phase 4 — charts (wealth, underwater, heatmap, distribution, rolling statistics).
3. Phase 6 — optional PDF and screenshot ingestion with extraction confidence.
4. Phase 7 — factor models with explicitly supplied factor data.

## Development

```bash
python -m venv .venv && . .venv/bin/activate      # keep the venv out of synced folders
pip install -e ".[dev,validation]"
pytest                                            # unit, property, golden, cross-library
ruff check . && ruff format --check . && mypy
python scripts/generate_docs.py --check           # generated docs up to date
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the metric definition-of-done and the
formula-sourcing protocol.

## License

[Apache-2.0](LICENSE). OpenFactsheet explains measurements; it does not give
investment advice.
