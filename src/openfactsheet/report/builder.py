"""Assemble a :class:`FactsheetReport` from normalized inputs.

INPUT → NORMALIZATION → DIAGNOSTICS → METRICS → POLICY → INTERPRETATION → REPORT.
Normalization happens before this module; rendering happens after it.
"""

from __future__ import annotations

import hashlib
import json

from openfactsheet.compare.alignment import align_benchmark
from openfactsheet.diagnostics.data_quality import run_diagnostics
from openfactsheet.interpretation.engine import build_interpretations
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.engine import compute_all
from openfactsheet.models.input import InputDiagnostics, ReturnSeries
from openfactsheet.models.report import FactsheetReport, Provenance
from openfactsheet.policy.annualization import annualization_assumption
from openfactsheet.policy.defaults import canonical_methodology
from openfactsheet.version import __version__


def series_sha256(series: ReturnSeries) -> str:
    """Deterministic fingerprint of the analyzed returns (dates + shortest round-trip floats)."""
    dates = [d.strftime("%Y-%m-%d") for d in series.dates] if series.dates is not None else None
    payload = json.dumps(
        {"dates": dates, "values": [repr(float(v)) for v in series.values]},
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_report(
    series: ReturnSeries,
    input_diag: InputDiagnostics,
    benchmark: ReturnSeries | None = None,
    benchmark_diag: InputDiagnostics | None = None,
) -> FactsheetReport:
    methodology = canonical_methodology()
    diagnostics = run_diagnostics(series, input_diag)
    aligned = align_benchmark(series, benchmark) if benchmark is not None else None
    ctx = MetricContext(
        returns=series, diagnostics=diagnostics, methodology=methodology, benchmark=aligned
    )
    metrics = compute_all(ctx)
    interpretations = build_interpretations(metrics, ctx)
    episodes = () if diagnostics.impossible_return_count else ctx.cache.episodes

    provenance = Provenance(
        package_version=__version__,
        methodology_version=methodology.version,
        input_type=series.source_type,
        input_sha256=series_sha256(series),
        date_range=(input_diag.start, input_diag.end),
        frequency=series.frequency.value,
        annualization=annualization_assumption(
            series.frequency, series.periods_per_year, series.frequency_source
        ),
        observations=series.n,
        transformations=input_diag.transformations,
        benchmark_name=benchmark.name if benchmark is not None else None,
        benchmark_sha256=series_sha256(benchmark) if benchmark is not None else None,
    )
    return FactsheetReport(
        name=series.name,
        returns=series,
        input_summary=input_diag,
        diagnostics=diagnostics,
        metrics=metrics,
        assumptions=methodology,
        interpretations=interpretations,
        benchmark_summary=aligned.diagnostics if aligned is not None else None,
        benchmark_input_summary=benchmark_diag,
        provenance=provenance,
        drawdown_episodes=episodes,
    )
