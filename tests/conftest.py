from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = Path(__file__).parent / "golden"
REFERENCE = FIXTURES / "reference"

SINGLE_FIXTURES = ("monthly_fund_10y", "negative_fund", "smoothed_hedge_fund")


def fixture_series(name: str) -> pd.Series:
    df = pd.read_csv(FIXTURES / f"{name}.csv", parse_dates=["date"])
    return pd.Series(df["return"].to_numpy(), index=pd.DatetimeIndex(df["date"]), name=name)


def monthly(values: list[float], start: str = "2020-01-31") -> pd.Series:
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="ME"))


@pytest.fixture(scope="session")
def pa_reference() -> dict[str, Any]:
    return json.loads((REFERENCE / "performanceanalytics.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def fund_10y() -> pd.Series:
    return fixture_series("monthly_fund_10y")


@pytest.fixture(scope="session")
def hedge_fund() -> pd.Series:
    return fixture_series("smoothed_hedge_fund")


@pytest.fixture(scope="session")
def benchmark_pair() -> tuple[pd.Series, pd.Series]:
    return fixture_series("benchmark_case_fund"), fixture_series("benchmark_case_benchmark")
