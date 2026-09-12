"""Assemble a :class:`FactsheetReport` from normalized inputs.

INPUT → NORMALIZATION → DIAGNOSTICS → METRICS → POLICY → INTERPRETATION → REPORT.
Normalization happens before this module; rendering happens after it.
"""

from __future__ import annotations

import hashlib
import json

from openfactsheet.compare.alignment import align_benchmark
from openfactsheet.diagnostics.data_quality import run_diagnostics
from openfactsheet.documents.profile import DocumentProfile
from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.factors.models import FactorAnalysis, FactorModelFit, FactorSet
from openfactsheet.factors.regressions import AlignedFactors, align_factors
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


def factor_set_sha256(factor_set: FactorSet) -> str:
    """Fingerprint of the factor data: each column's fingerprint, keyed by column name."""
    columns = dict(factor_set.factors)
    if factor_set.risk_free is not None:
        columns["RF"] = factor_set.risk_free
    payload = json.dumps(
        {name: series_sha256(s) for name, s in columns.items()}, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _factor_analysis(aligned: AlignedFactors, factor_set: FactorSet) -> FactorAnalysis:
    fit: FactorModelFit | None = None
    reason: str | None = None
    try:
        fit = aligned.fit
    except UndefinedMetric as exc:
        reason = exc.reason
    except Exception as exc:  # captured, never raised out of the report
        reason = f"Estimation failed ({type(exc).__name__}: {exc}). Please report this as a bug."
    return FactorAnalysis(
        model=aligned.model,
        factor_names=aligned.names,
        dependent=aligned.dependent,
        return_scale=factor_set.return_scale,
        return_scale_evidence=factor_set.return_scale_evidence,
        alignment=aligned.alignment,
        fit=fit,
        reason=reason,
    )


def _document(series: ReturnSeries) -> DocumentProfile | None:
    doc = series.metadata.get("document")
    return doc if isinstance(doc, DocumentProfile) else None


def build_report(
    series: ReturnSeries,
    input_diag: InputDiagnostics,
    benchmark: ReturnSeries | None = None,
    benchmark_diag: InputDiagnostics | None = None,
    factor_set: FactorSet | None = None,
) -> FactsheetReport:
    methodology = canonical_methodology()
    diagnostics = run_diagnostics(series, input_diag)
    aligned = align_benchmark(series, benchmark) if benchmark is not None else None
    factors = align_factors(series, factor_set, methodology) if factor_set is not None else None
    ctx = MetricContext(
        returns=series,
        diagnostics=diagnostics,
        methodology=methodology,
        benchmark=aligned,
        factors=factors,
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
        factor_names=factor_set.names if factor_set is not None else None,
        factors_sha256=factor_set_sha256(factor_set) if factor_set is not None else None,
        extraction=series.metadata.get("extraction"),
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
        benchmark_returns=benchmark,
        document=_document(series),
        factor_analysis=(
            _factor_analysis(factors, factor_set)
            if factors is not None and factor_set is not None
            else None
        ),
    )
