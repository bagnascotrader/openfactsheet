"""Compare investments under one identical methodology (no ranking)."""

from pathlib import Path

import openfactsheet as ofs

FIXTURES = Path(__file__).parents[1] / "tests" / "fixtures"

comparison = ofs.compare(
    {
        "Smoothed hedge fund": FIXTURES / "smoothed_hedge_fund.csv",
        "Long-only fund": FIXTURES / "monthly_fund_10y.csv",
    }
)
print(comparison.summary())

# The hedge fund's high Sharpe ratio is shown, but flagged: its returns are smoothed.
hf = comparison.reports["Smoothed hedge fund"]
print("\nSmoothing risk:", hf.diagnostics.smoothing_risk)
print("Sharpe status:", hf.metrics["sharpe_ratio"].status)
