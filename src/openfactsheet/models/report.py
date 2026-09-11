"""Structured report model (CLAUDE.md section 28). Rendering lives in ``openfactsheet.report``."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from openfactsheet.models.assumptions import Methodology
from openfactsheet.models.diagnostics import DataQualityReport
from openfactsheet.models.input import InputDiagnostics, ReturnSeries
from openfactsheet.models.metric import MetricCollection

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True)
class BenchmarkDiagnostics:
    """How fund and benchmark returns were aligned (overlap is always disclosed)."""

    name: str
    fund_observations: int
    benchmark_observations: int
    aligned_observations: int
    fund_only_periods: int
    benchmark_only_periods: int
    overlap_start: str | None
    overlap_end: str | None
    alignment_method: str
    warnings: tuple[str, ...] = ()

    @property
    def fund_coverage(self) -> float:
        """Share of the fund's observations that have a matching benchmark return."""
        if self.fund_observations == 0:
            return 0.0
        return self.aligned_observations / self.fund_observations

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "fund_observations": self.fund_observations,
            "benchmark_observations": self.benchmark_observations,
            "aligned_observations": self.aligned_observations,
            "fund_only_periods": self.fund_only_periods,
            "benchmark_only_periods": self.benchmark_only_periods,
            "fund_coverage": self.fund_coverage,
            "overlap_start": self.overlap_start,
            "overlap_end": self.overlap_end,
            "alignment_method": self.alignment_method,
            "warnings": list(self.warnings),
        }

    def to_text(self) -> str:
        lines = [
            f"Benchmark:                 {self.name}",
            f"Alignment:                 {self.alignment_method}",
            f"Fund observations:         {self.fund_observations}",
            f"Benchmark observations:    {self.benchmark_observations}",
            f"Aligned observations:      {self.aligned_observations} "
            f"({self.fund_coverage:.0%} of fund history)",
            f"Fund-only periods dropped: {self.fund_only_periods}",
            f"Benchmark-only periods:    {self.benchmark_only_periods}",
            f"Overlap:                   {self.overlap_start or 'n/a'} to "
            f"{self.overlap_end or 'n/a'}",
        ]
        lines.extend(f"  - {w}" for w in self.warnings)
        return "\n".join(lines)


@dataclass(frozen=True)
class Interpretation:
    """Two-layer interpretation (CLAUDE.md section 16). Explains; never advises."""

    metric_id: str
    plain: str
    professional: str
    context: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "plain": self.plain,
            "professional": self.professional,
            "context": list(self.context),
        }


@dataclass(frozen=True)
class Provenance:
    """Everything needed to audit how a report was produced (CLAUDE.md section 36)."""

    package_version: str
    methodology_version: str
    input_type: str
    input_sha256: str
    date_range: tuple[str | None, str | None]
    frequency: str
    annualization: str
    observations: int
    transformations: tuple[str, ...]
    benchmark_name: str | None
    benchmark_sha256: str | None
    canonical: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_version": self.package_version,
            "methodology_version": self.methodology_version,
            "input_type": self.input_type,
            "input_sha256": self.input_sha256,
            "date_range": list(self.date_range),
            "frequency": self.frequency,
            "annualization": self.annualization,
            "observations": self.observations,
            "transformations": list(self.transformations),
            "benchmark_name": self.benchmark_name,
            "benchmark_sha256": self.benchmark_sha256,
            "canonical": self.canonical,
        }


@dataclass(frozen=True, eq=False)
class FactsheetReport:
    """The canonical OpenFactsheet report. Calculations know nothing about rendering."""

    name: str
    returns: ReturnSeries
    input_summary: InputDiagnostics
    diagnostics: DataQualityReport
    metrics: MetricCollection
    assumptions: Methodology
    interpretations: Mapping[str, Interpretation]
    benchmark_summary: BenchmarkDiagnostics | None
    benchmark_input_summary: InputDiagnostics | None
    provenance: Provenance
    drawdown_episodes: tuple[Any, ...] = field(default_factory=tuple)

    # -- convenience ------------------------------------------------------
    @property
    def methodology_version(self) -> str:
        return self.assumptions.version

    def returns_frame(self) -> pd.Series:
        """Exactly the returns OpenFactsheet analyzed (decimal, after normalization)."""
        return self.returns.to_pandas()

    # -- rendering (delegated) ---------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        from openfactsheet.report.json import report_to_dict

        return report_to_dict(self)

    def to_json(self, path: str | Path | None = None, *, indent: int = 2) -> str:
        from openfactsheet.report.json import report_to_json

        text = report_to_json(self, indent=indent)
        if path is not None:
            Path(path).write_text(text, encoding="utf-8")
        return text

    def summary(self) -> str:
        from openfactsheet.report.terminal import render_terminal

        return render_terminal(self)

    def to_markdown(self, path: str | Path | None = None) -> str:
        from openfactsheet.report.markdown import render_markdown

        text = render_markdown(self)
        if path is not None:
            Path(path).write_text(text, encoding="utf-8")
        return text

    def to_html(self, path: str | Path | None = None) -> str:
        from openfactsheet.report.html import render_html

        text = render_html(self)
        if path is not None:
            Path(path).write_text(text, encoding="utf-8")
        return text

    def __str__(self) -> str:
        return self.summary()

    def __repr__(self) -> str:
        return (
            f"FactsheetReport(name={self.name!r}, observations={self.returns.n}, "
            f"frequency={self.returns.frequency.value!r}, metrics={len(self.metrics)}, "
            f"methodology={self.methodology_version!r})"
        )
