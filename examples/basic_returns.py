"""Analyze a short monthly return series (CLAUDE.md first acceptance test)."""

import pandas as pd

import openfactsheet as ofs

returns = pd.Series(
    [0.01, -0.02, 0.015, 0.005, -0.01, 0.03],
    index=pd.date_range("2025-01-31", periods=6, freq="ME"),
    name="Example fund",
)

report = ofs.analyze(returns)
print(report.summary())

sharpe = report.metrics["sharpe_ratio"]
print(f"\nSharpe: {sharpe.value:.2f} ({sharpe.status}); warnings: {list(sharpe.warnings)}")
