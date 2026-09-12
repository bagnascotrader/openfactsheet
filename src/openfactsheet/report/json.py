"""Deterministic JSON export.

The output is stable for identical inputs: keys are sorted, no timestamps are
embedded, floats are written at full precision, and NaN/inf can never appear
(``allow_nan=False``).
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

import numpy as np

from openfactsheet.models.report import FactsheetReport

SCHEMA_VERSION = "0.1"


def to_jsonable(obj: Any) -> Any:
    """Convert numpy scalars/containers to plain Python; non-finite floats become ``None``."""
    if isinstance(obj, Mapping):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [to_jsonable(v) for v in obj.tolist()]
    if isinstance(obj, bool | np.bool_):
        return bool(obj)
    if isinstance(obj, int | np.integer):
        return int(obj)
    if isinstance(obj, float | np.floating):
        f = float(obj)
        return f if math.isfinite(f) else None
    return obj


def report_to_dict(report: FactsheetReport) -> dict[str, Any]:
    series = report.returns
    if series.dates is not None:
        returns = [
            {"date": d.strftime("%Y-%m-%d"), "value": float(v)}
            for d, v in zip(series.dates, series.values, strict=True)
        ]
    else:
        returns = [{"period": i + 1, "value": float(v)} for i, v in enumerate(series.values)]
    benchmark = None
    if report.benchmark_summary is not None:
        benchmark = {
            "alignment": report.benchmark_summary.to_dict(),
            "input": (
                report.benchmark_input_summary.to_dict()
                if report.benchmark_input_summary is not None
                else None
            ),
        }
    data = {
        "schema_version": SCHEMA_VERSION,
        "canonical": report.provenance.canonical,
        "name": report.name,
        "methodology": report.assumptions.to_dict(),
        "input": report.input_summary.to_dict(),
        "returns": returns,
        "data_quality": report.diagnostics.to_dict(),
        "metrics": [m.to_dict() for m in report.metrics],
        "drawdown_episodes": [e.to_dict() for e in report.drawdown_episodes],
        "benchmark": benchmark,
        "factor_analysis": (
            report.factor_analysis.to_dict() if report.factor_analysis is not None else None
        ),
        "interpretations": {k: v.to_dict() for k, v in report.interpretations.items()},
        "provenance": report.provenance.to_dict(),
    }
    return to_jsonable(data)  # type: ignore[no-any-return]


def report_to_json(report: FactsheetReport, indent: int = 2) -> str:
    return json.dumps(report_to_dict(report), indent=indent, sort_keys=True, allow_nan=False)
