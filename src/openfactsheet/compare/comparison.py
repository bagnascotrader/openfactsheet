"""Comparison engine (CLAUDE.md phase 5, minimal v0.1 implementation).

All investments are analyzed with the identical canonical methodology.
Nothing is ranked: rankings on a single metric recreate cherry-picking.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

import pandas as pd

from openfactsheet.exceptions import InputError
from openfactsheet.input.dispatcher import to_raw
from openfactsheet.models.input import ObservationFrequency, RawReturns, ReturnSeries, ReturnTable
from openfactsheet.models.report import FactsheetReport
from openfactsheet.normalization.scaling import DeclaredScale
from openfactsheet.report.json import report_to_dict
from openfactsheet.report.tables import format_value, status_label

_PERIOD = {
    ObservationFrequency.MONTHLY: "M",
    ObservationFrequency.QUARTERLY: "Q",
    ObservationFrequency.YEARLY: "Y",
}


@dataclass(frozen=True, eq=False)
class Comparison:
    """Several investments analyzed under one identical methodology, returned by :func:`compare`.

    Nothing is ranked or scored. Each investment keeps its full canonical report.

    Attributes:
        reports: The full-history :class:`FactsheetReport` of each investment, by name.
        common_period_reports: Reports restricted to the period all histories share,
            or ``None`` when the histories cover the same period or share fewer than two.
        common_period: First and last date of the common period, or ``None``.
        notes: Explanations of track-record and alignment differences.
    """

    reports: Mapping[str, FactsheetReport]
    common_period_reports: Mapping[str, FactsheetReport] | None
    common_period: tuple[str, str] | None
    notes: tuple[str, ...]

    def _source(self, common_period: bool) -> Mapping[str, FactsheetReport]:
        if common_period:
            if self.common_period_reports is None:
                raise ValueError("No common-period analysis is available for this comparison.")
            return self.common_period_reports
        return self.reports

    def table(self, *, common_period: bool = False) -> pd.DataFrame:
        """Raw metric values (rows) by investment (columns).

        Args:
            common_period: Use the common-period reports instead of the full histories.

        Returns:
            A DataFrame indexed by metric id with a ``name`` column and one column
            per investment; unavailable values are missing (see ``status_table``).
        """
        reports = self._source(common_period)
        first = next(iter(reports.values()))
        data = {name: [m.value for m in rep.metrics] for name, rep in reports.items()}
        index = pd.Index([m.id for m in first.metrics], name="metric")
        frame = pd.DataFrame(data, index=index)
        frame.insert(0, "name", [m.name for m in first.metrics])
        return frame

    def status_table(self, *, common_period: bool = False) -> pd.DataFrame:
        """Confidence / status labels by investment.

        Args:
            common_period: Use the common-period reports instead of the full histories.
        """
        reports = self._source(common_period)
        first = next(iter(reports.values()))
        data = {name: [status_label(m) for m in rep.metrics] for name, rep in reports.items()}
        return pd.DataFrame(data, index=pd.Index([m.id for m in first.metrics], name="metric"))

    def track_records(self) -> pd.DataFrame:
        """Start, end, length, frequency, smoothing risk and benchmark overlap by investment."""
        rows = []
        for name, rep in self.reports.items():
            s = rep.input_summary
            rows.append(
                {
                    "name": name,
                    "start": s.start,
                    "end": s.end,
                    "observations": s.observations,
                    "years": s.years,
                    "frequency": s.frequency.value,
                    "smoothing_risk": rep.diagnostics.smoothing_risk,
                    "benchmark_overlap": (
                        rep.benchmark_summary.aligned_observations
                        if rep.benchmark_summary is not None
                        else None
                    ),
                }
            )
        return pd.DataFrame(rows).set_index("name")

    def summary(self) -> str:
        """Track records and every metric side by side, as plain text."""
        reports = self.reports
        names = list(reports)
        first = next(iter(reports.values()))
        width = max(14, *(len(n) + 2 for n in names))
        lines = [
            "OPENFACTSHEET COMPARISON",
            f"{first.assumptions.name} (identical for all investments). Not a ranking.",
            "",
            "Track records:",
            self.track_records().to_string(),
            "",
        ]
        lines.extend(f"Note: {n}" for n in self.notes)
        header = f"{'Metric':<44}" + "".join(f"{n:>{width}}" for n in names)
        lines += ["", header, "-" * len(header)]
        for i, m in enumerate(first.metrics):
            cells = []
            for rep in reports.values():
                r = rep.metrics.results[i]
                text = format_value(r)
                if r.value is not None and r.confidence == "low":
                    text += "*"
                cells.append(f"{text:>{width}}")
            lines.append(f"{m.name:<44}" + "".join(cells))
        lines += ["", "* low confidence; '—' not available (see each report for reasons)."]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Every report (and common-period report) as JSON-compatible Python objects."""
        return {
            "reports": {k: report_to_dict(v) for k, v in self.reports.items()},
            "common_period": list(self.common_period) if self.common_period else None,
            "common_period_reports": (
                {k: report_to_dict(v) for k, v in self.common_period_reports.items()}
                if self.common_period_reports is not None
                else None
            ),
            "notes": list(self.notes),
        }

    def to_json(self, indent: int = 2) -> str:
        """The comparison as deterministic JSON.

        Args:
            indent: Indentation of the JSON text.
        """
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, allow_nan=False)

    def __str__(self) -> str:
        return self.summary()


def _collect(funds: Any) -> list[Any]:
    """Return a list of (name, source) pairs as objects accepted by ``analyze``."""
    if isinstance(funds, ReturnTable):
        return list(funds.series.items())
    if isinstance(funds, Mapping):
        return list(funds.items())
    if isinstance(funds, pd.DataFrame):
        raws = to_raw(funds)
        return [(r.name, r) for r in raws]
    if isinstance(funds, Sequence) and not isinstance(funds, str):
        out = []
        for i, item in enumerate(funds, start=1):
            label = getattr(item, "name", None) or f"Series {i}"
            out.append((str(label), item))
        return out
    raise InputError("compare() expects a mapping of name -> returns, a DataFrame, or a list.")


def _keys(series: ReturnSeries) -> pd.Index:
    assert series.dates is not None
    code = _PERIOD.get(series.frequency)
    return pd.Index(series.dates.to_period(code)) if code else pd.Index(series.dates.normalize())


def build_comparison(
    funds: Any,
    *,
    benchmark: Any = None,
    factors: Any = None,
    return_scale: DeclaredScale | None = None,
    frequency: str | ObservationFrequency | None = None,
) -> Comparison:
    from openfactsheet.api import analyze, normalize_benchmark
    from openfactsheet.factors.data import load_factor_set
    from openfactsheet.normalization.returns import normalize_returns
    from openfactsheet.report.builder import build_report

    # Factor data are parsed once so every investment is regressed on identical factors.
    factor_set = (
        load_factor_set(factors, return_scale=return_scale, frequency=frequency)
        if factors is not None
        else None
    )

    pairs = _collect(funds)
    if len(pairs) < 2:
        raise InputError("compare() needs at least two return histories.")
    names = [str(n) for n, _ in pairs]
    if len(set(names)) != len(names):
        raise InputError("Investment names in compare() must be unique.")

    reports: dict[str, FactsheetReport] = {}
    for label, source in pairs:
        reports[str(label)] = analyze(
            source,
            benchmark,
            factors=factor_set,
            name=str(label),
            return_scale=return_scale,
            frequency=frequency,
        )

    notes: list[str] = []
    series = [r.returns for r in reports.values()]
    common_reports: dict[str, FactsheetReport] | None = None
    common_period: tuple[str, str] | None = None
    freqs = {s.frequency for s in series}
    dated = all(s.dates is not None for s in series)
    if len(freqs) > 1:
        notes.append(
            "Investments have different observation frequencies ("
            + ", ".join(sorted(f.value for f in freqs))
            + "); per-period statistics are not directly comparable."
        )
    ranges = {(r.input_summary.start, r.input_summary.end) for r in reports.values()}
    if dated and len(freqs) == 1 and next(iter(freqs)).is_regular and len(ranges) > 1:
        notes.append(
            "Histories cover different periods; full-history metrics are not directly "
            "comparable. A common-period analysis (intersection of all histories) is provided."
        )
        common = _keys(series[0])
        for s in series[1:]:
            common = common.intersection(_keys(s))
        if len(common) >= 2:
            common_reports = {}
            # The benchmark is normalized once, exactly as for the full-history reports:
            # re-reading it with the decimal declaration used for the (already decimal)
            # fund subsets would misread a percent benchmark by a factor of 100.
            bench = bench_diag = None
            if benchmark is not None:
                bench, bench_diag = normalize_benchmark(
                    benchmark, return_scale=return_scale, frequency=frequency
                )
            for label, rep in reports.items():
                s = rep.returns
                keys = _keys(s)
                mask = keys.isin(common)
                sub = RawReturns(
                    values=s.values[mask],
                    dates=pd.DatetimeIndex(s.dates[mask]) if s.dates is not None else None,
                    name=label,
                    source_type=s.source_type,
                    transformations=("restricted to the common period of all compared histories",),
                )
                sub_series, sub_diag = normalize_returns(sub, return_scale="decimal")
                # The subset is already decimal; keep the original scale evidence.
                original = rep.input_summary
                evidence = (
                    f"{original.return_scale_evidence} (common-period subset of the normalized "
                    "series)"
                )
                sub_diag = replace(
                    sub_diag,
                    return_scale=original.return_scale,
                    return_scale_evidence=evidence,
                )
                sub_series = replace(
                    sub_series, return_scale=original.return_scale, input_diagnostics=sub_diag
                )
                common_reports[label] = build_report(
                    sub_series, sub_diag, bench, bench_diag, factor_set
                )
            first = next(iter(common_reports.values())).input_summary
            common_period = (first.start or "", first.end or "")
        else:
            notes.append("The histories have fewer than 2 periods in common.")
    return Comparison(
        reports=reports,
        common_period_reports=common_reports,
        common_period=common_period,
        notes=tuple(notes),
    )
