"""Public API: ``analyze``, ``compare``, ``load``, ``metric_catalog``, ``methodology``.

The API is intentionally small. There are no knobs for metric windows,
thresholds, confidence levels or metric subsets: the canonical methodology
decides. The only optional arguments *describe the input* when it cannot be
established from the data itself (percent vs decimal scale, frequency of
undated values); such declarations are recorded in the report.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import TYPE_CHECKING, Any

import pandas as pd

from openfactsheet.exceptions import InputError
from openfactsheet.factors.data import load_factor_set
from openfactsheet.input.dispatcher import to_raw
from openfactsheet.metrics.registry import all_metrics
from openfactsheet.models.assumptions import Methodology
from openfactsheet.models.input import (
    InputDiagnostics,
    ObservationFrequency,
    RawReturns,
    ReturnSeries,
    ReturnTable,
)
from openfactsheet.models.report import FactsheetReport
from openfactsheet.normalization.returns import normalize_returns
from openfactsheet.normalization.scaling import DeclaredScale
from openfactsheet.policy.defaults import canonical_methodology
from openfactsheet.policy.thresholds import get_policy
from openfactsheet.report.builder import build_report

if TYPE_CHECKING:
    from openfactsheet.compare.comparison import Comparison


def _normalize_one(
    source: Any,
    *,
    name: str | None,
    return_scale: DeclaredScale | None,
    frequency: str | ObservationFrequency | None,
    role: str,
) -> tuple[ReturnSeries, InputDiagnostics]:
    if isinstance(source, RawReturns) and name is not None:
        source = replace(source, name=name)
    if isinstance(source, ReturnSeries):
        if source.input_diagnostics is not None and return_scale is None and frequency is None:
            if name is not None and name != source.name:
                diag = replace(source.input_diagnostics, name=name)
                return replace(source, name=name, input_diagnostics=diag), diag
            return source, source.input_diagnostics
        source = RawReturns(
            values=source.values,
            dates=source.dates,
            name=name or source.name,
            source_type=source.source_type,
        )
        return_scale = return_scale or "decimal"
    raws = to_raw(source, name=name)
    if len(raws) != 1:
        names = ", ".join(r.name for r in raws)
        raise InputError(
            f"The {role} input contains {len(raws)} return series ({names}); analyze() expects "
            "exactly one. Select a column, or use ofs.compare() for several series."
        )
    return normalize_returns(raws[0], return_scale=return_scale, frequency=frequency)


def normalize_benchmark(
    benchmark: Any,
    *,
    return_scale: DeclaredScale | None = None,
    frequency: str | ObservationFrequency | None = None,
) -> tuple[ReturnSeries, InputDiagnostics]:
    """Normalize benchmark input as :func:`analyze` does (named ``Benchmark`` by default)."""
    bench_name = (
        str(benchmark.name)
        if isinstance(benchmark, pd.Series) and benchmark.name is not None
        else None
    )
    return _normalize_one(
        benchmark,
        name=bench_name or (None if isinstance(benchmark, ReturnSeries) else "Benchmark"),
        return_scale=return_scale,
        frequency=frequency,
        role="benchmark",
    )


def load(
    source: Any,
    *,
    name: str | None = None,
    return_scale: DeclaredScale | None = None,
    frequency: str | ObservationFrequency | None = None,
) -> ReturnSeries | ReturnTable:
    """Parse and normalize input without computing metrics.

    Returns a :class:`ReturnSeries` for a single series or a :class:`ReturnTable`
    when the source contains several return columns. Inspect
    ``series.input_diagnostics`` to see exactly what OpenFactsheet believes it
    received.
    """
    raws = to_raw(source, name=name)
    normalized = [
        normalize_returns(r, return_scale=return_scale, frequency=frequency)[0] for r in raws
    ]
    if len(normalized) == 1:
        return normalized[0]
    return ReturnTable({s.name: s for s in normalized})


def analyze(
    returns: Any,
    benchmark: Any = None,
    *,
    factors: Any = None,
    name: str | None = None,
    return_scale: DeclaredScale | None = None,
    frequency: str | ObservationFrequency | None = None,
) -> FactsheetReport:
    """Produce the canonical OpenFactsheet report for one return history.

    Args:
        returns: A list/tuple/array of returns, a pandas Series (ideally with a
            DatetimeIndex), a one-column DataFrame, a CSV/Excel path, pasted table
            text, or a :class:`ReturnSeries` from :func:`load`.
        benchmark: Optional benchmark returns in any of the same forms. Benchmark-
            relative metrics are computed only when a benchmark is supplied.
        factors: Optional factor returns, one column per factor (a DataFrame, a
            CSV/Excel path or table text, e.g. Fama-French factors). A column named
            ``RF`` is the risk-free rate and is subtracted from fund returns. Factor-
            model metrics are computed only when factors are supplied; OpenFactsheet
            never downloads factor data.
        name: Display name for the report.
        return_scale: Declare ``"decimal"`` or ``"percent"`` only when automatic
            detection reports ambiguity. Applies to fund, benchmark and factors.
        frequency: Declare the observation frequency of *undated* values. It is
            checked against dates when dates exist. Applies to fund, benchmark and
            factors.

    Returns:
        A :class:`FactsheetReport` containing every canonical metric with its
        status, confidence, warnings and assumptions.
    """
    series, diag = _normalize_one(
        returns, name=name, return_scale=return_scale, frequency=frequency, role="returns"
    )
    bench_series = bench_diag = None
    if benchmark is not None:
        bench_series, bench_diag = normalize_benchmark(
            benchmark, return_scale=return_scale, frequency=frequency
        )
    factor_set = (
        load_factor_set(factors, return_scale=return_scale, frequency=frequency)
        if factors is not None
        else None
    )
    return build_report(series, diag, bench_series, bench_diag, factor_set)


def compare(
    funds: Mapping[str, Any] | pd.DataFrame | Sequence[Any] | ReturnTable,
    benchmark: Any = None,
    *,
    factors: Any = None,
    return_scale: DeclaredScale | None = None,
    frequency: str | ObservationFrequency | None = None,
) -> Comparison:
    """Analyze several return histories under one identical methodology.

    Metrics are shown side by side; nothing is ranked. When the histories cover
    different periods, an additional common-period analysis (the intersection of
    all histories) is provided so that track-record differences are visible. The
    same benchmark and factor returns, if supplied, are used for every investment.
    """
    from openfactsheet.compare.comparison import build_comparison

    return build_comparison(
        funds,
        benchmark=benchmark,
        factors=factors,
        return_scale=return_scale,
        frequency=frequency,
    )


def metric_catalog() -> pd.DataFrame:
    """Every canonical metric with its definition, conventions and data requirements."""
    rows = []
    for d in all_metrics():
        row = d.to_dict()
        row["minimum_data"] = get_policy(d.min_data_policy).description
        row["references"] = "; ".join(r.citation for r in d.docs.references)
        rows.append(row)
    return pd.DataFrame(rows).set_index("id")


def methodology() -> Methodology:
    """The canonical, versioned methodology used by every report."""
    return canonical_methodology()
