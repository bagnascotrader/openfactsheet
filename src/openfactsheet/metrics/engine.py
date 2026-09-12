"""Metric engine: iterate the registry, calculate, then apply policy.

This is the single place that guarantees CLAUDE.md principle 1.7: every metric
yields a structured :class:`MetricResult`; no unexplained NaN/inf ever escapes.
"""

from __future__ import annotations

import math
import warnings as pywarnings

import numpy as np

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.registry import all_metrics
from openfactsheet.models.metric import (
    Computed,
    MetricCollection,
    MetricDefinition,
    MetricResult,
    MetricStatus,
)
from openfactsheet.policy.applicability import observations_for, precheck
from openfactsheet.policy.confidence import assess, assumption_texts


def _empty(
    definition: MetricDefinition,
    ctx: MetricContext,
    status: MetricStatus,
    reason: str,
) -> MetricResult:
    return MetricResult(
        id=definition.id,
        name=definition.name,
        category=definition.category,
        value=None,
        unit=definition.unit,
        status=status,
        direction=definition.direction,
        confidence="not_assessable",
        nature=definition.nature,
        observations=observations_for(definition, ctx),
        formula_id=definition.formula_id,
        methodology_version=ctx.methodology.version,
        assumptions=assumption_texts(definition, ctx),
        reason=reason,
    )


def evaluate(definition: MetricDefinition, ctx: MetricContext) -> MetricResult:
    blocked = precheck(definition, ctx)
    if blocked is not None:
        return _empty(definition, ctx, blocked.status, blocked.reason)

    try:
        with np.errstate(all="ignore"), pywarnings.catch_warnings():
            pywarnings.simplefilter("ignore", RuntimeWarning)
            out = definition.func(ctx)
    except UndefinedMetric as exc:
        return _empty(definition, ctx, "not_applicable", exc.reason)
    except Exception as exc:  # captured, never raised out of the report
        return _empty(
            definition,
            ctx,
            "error",
            f"Calculation failed ({type(exc).__name__}: {exc}). Please report this as a bug.",
        )

    computed = out if isinstance(out, Computed) else Computed(value=float(out))
    value = float(computed.value)
    if math.isinf(value):
        # A ratio whose denominator is non-zero but below floating-point resolution (e.g. a
        # single subnormal loss) overflows: the metric is undefined for these data.
        return _empty(
            definition,
            ctx,
            "not_applicable",
            "The result overflows floating point because a denominator is effectively zero "
            "(below numerical resolution); the metric is undefined for these data.",
        )
    if not math.isfinite(value):
        return _empty(
            definition,
            ctx,
            "error",
            f"Calculation produced a non-finite value ({value}); it is withheld rather than "
            "shown. Please report this as a bug.",
        )

    a = assess(definition, ctx, computed.notes)
    return MetricResult(
        id=definition.id,
        name=definition.name,
        category=definition.category,
        value=value,
        unit=definition.unit,
        status=a.status,
        direction=definition.direction,
        confidence=a.confidence,
        nature=definition.nature,
        observations=observations_for(definition, ctx),
        formula_id=definition.formula_id,
        methodology_version=ctx.methodology.version,
        assumptions=a.assumptions,
        warnings=a.warnings,
        details=computed.details,
    )


def compute_all(ctx: MetricContext) -> MetricCollection:
    """Compute every registered metric (the canonical metric universe)."""
    return MetricCollection(tuple(evaluate(d, ctx) for d in all_metrics()))
