"""Generate the synthetic, committed test fixtures (run once; outputs are committed).

Fixtures are generated from a fixed seed but *committed as CSV* so that tests
never depend on a random-number generator's implementation. Re-running this
script is only needed when adding fixtures; changing existing fixtures requires
regenerating golden reports and cross-library references consciously.

    python scripts/make_fixtures.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
EXAMPLES = ROOT / "examples"
SEED = 20260910


def _t(rng: np.random.Generator, n: int, df: int = 5) -> np.ndarray:
    """Unit-variance Student-t draws (fat-tailed like real returns)."""
    return rng.standard_t(df, n) / np.sqrt(df / (df - 2))


def _write(frame: pd.DataFrame, name: str) -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    frame.to_csv(FIXTURES / name, index=False, float_format="%.6f")


def month_ends(start: str, periods: int) -> pd.DatetimeIndex:
    return pd.date_range(start, periods=periods, freq="ME")


def main() -> None:
    rng = np.random.default_rng(SEED)

    # 1. Ten years of monthly fund returns, fat-tailed.
    dates = month_ends("2015-01-31", 120)
    r = 0.006 + 0.035 * _t(rng, 120)
    _write(pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "return": r}), "monthly_fund_10y.csv")

    # 2. A losing fund (5 years).
    dates = month_ends("2019-01-31", 60)
    r = -0.008 + 0.03 * _t(rng, 60)
    _write(pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "return": r}), "negative_fund.csv")

    # 3. Suspicious hedge fund: smoothed (MA(2) of latent returns), low volatility,
    #    many small positive months, occasional large losses (CLAUDE.md section 50).
    #    Smoothed losses unfold over consecutive months, as reported marks do.
    n = 96
    latent = rng.normal(0.008, 0.009, n + 2)
    smoothed = 0.4 * latent[2:] + 0.35 * latent[1:-1] + 0.25 * latent[:-2]
    smoothed[39:42] = [-0.045, -0.032, -0.014]
    smoothed[79:81] = [-0.041, -0.019]
    dates = month_ends("2017-01-31", n)
    _write(
        pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "return": smoothed}),
        "smoothed_hedge_fund.csv",
    )

    # 4. Benchmark case: fund is month-end dated, benchmark month-start dated and
    #    shifted by six months, so alignment must match calendar months and drop
    #    six periods at each end.
    bench_all = 0.007 + 0.04 * _t(rng, 108)
    bench_dates = pd.date_range("2016-01-01", periods=108, freq="MS")
    fund_bench = bench_all[6:]
    fund = 0.0015 + 0.8 * fund_bench + rng.normal(0.0, 0.015, fund_bench.size)
    fund = np.concatenate([fund[:-6], 0.002 + 0.015 * rng.standard_normal(6)])
    fund_dates = month_ends("2016-07-31", fund.size)
    _write(
        pd.DataFrame({"date": fund_dates.strftime("%Y-%m-%d"), "return": fund}),
        "benchmark_case_fund.csv",
    )
    bench = bench_all[:102]
    _write(
        pd.DataFrame({"date": bench_dates[:102].strftime("%Y-%m-%d"), "return": bench}),
        "benchmark_case_benchmark.csv",
    )

    # 5. Example wide monthly table in percent, with empty future cells.
    EXAMPLES.mkdir(exist_ok=True)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    table = np.round(100 * (0.007 + 0.03 * _t(rng, 36)), 2).reshape(3, 12)
    rows = []
    for year, vals in zip((2022, 2023, 2024), table, strict=True):
        cells = [f"{v:.2f}%" for v in vals]
        if year == 2024:
            cells[9:] = ["", "", ""]
        ytd = np.prod([1 + float(c[:-1]) / 100 for c in cells if c]) - 1
        rows.append([year, *cells, f"{100 * ytd:.2f}%"])
    pd.DataFrame(rows, columns=["Year", *months, "YTD"]).to_csv(
        EXAMPLES / "monthly_table.csv", index=False
    )
    print(f"Fixtures written to {FIXTURES} and {EXAMPLES / 'monthly_table.csv'}")


if __name__ == "__main__":
    main()
