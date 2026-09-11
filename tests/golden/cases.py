"""Golden report cases shared by the golden test and ``scripts/update_golden.py``."""

from __future__ import annotations

from pathlib import Path

import openfactsheet as ofs
from tests.conftest import fixture_series

GOLDEN_DIR = Path(__file__).parent


def case_names() -> tuple[str, ...]:
    return ("monthly_fund_10y", "negative_fund", "smoothed_hedge_fund", "benchmark_case")


def build_case(name: str) -> ofs.FactsheetReport:
    if name == "benchmark_case":
        return ofs.analyze(
            fixture_series("benchmark_case_fund"),
            benchmark=fixture_series("benchmark_case_benchmark"),
            name="benchmark_case",
        )
    return ofs.analyze(fixture_series(name))
