"""Volatility / dispersion metrics (CLAUDE.md section 12.2)."""

from __future__ import annotations

import math

from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import BACON, EMP, LO_2002, NUMPY, PA, QS, lib
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import MetricDocs

_SMOOTHING_CAVEAT = (
    "Returns are smoothed or stale (illiquid assets, appraisal pricing): measured volatility "
    "is understated."
)


@metric(
    id="volatility",
    name="Volatility per period",
    category="volatility",
    unit="decimal_return",
    direction="lower_is_better",
    nature="estimated",
    min_data_policy="dispersion",
    volatility_based=True,
    assumptions=("sample_std",),
    docs=MetricDocs(
        measures="Dispersion of single-period returns around their mean.",
        formula="sqrt( sum((r_t - mean)^2) / (n - 1) )",
        inputs="Periodic simple returns.",
        retail="How much returns typically swing from one period to the next; higher means a "
        "bumpier ride.",
        institutional="Sample standard deviation of per-period returns; symmetric, treats "
        "upside and downside deviations alike.",
        assumptions=("Returns are identically distributed over the history.",),
        misleading_when=(
            _SMOOTHING_CAVEAT,
            "Returns are skewed or fat-tailed: volatility does not describe tail losses.",
        ),
        minimum_data="At least 2 observations; low confidence below 3 years.",
        reference_implementations=(lib(NUMPY, "std(ddof=1)"), lib(PA, "StdDev")),
        references=(BACON,),
        convention="Sample standard deviation (n - 1), decision 0003.",
    ),
)
def volatility(ctx: MetricContext) -> float:
    return ctx.cache.std


@metric(
    id="annualized_volatility",
    name="Annualized volatility",
    category="volatility",
    unit="decimal_return",
    direction="lower_is_better",
    nature="estimated",
    min_data_policy="dispersion",
    annualized=True,
    volatility_based=True,
    assumptions=("sample_std", "annualization"),
    docs=MetricDocs(
        measures="Per-period volatility scaled to one year.",
        formula="std(r_t, ddof=1) * sqrt(P)",
        inputs="Periodic simple returns with a regular frequency.",
        retail="The typical size of yearly swings implied by the period-to-period variability.",
        institutional="Square-root-of-time scaling assumes serially uncorrelated returns; "
        "positive autocorrelation makes it understate true annual volatility (Lo, 2002).",
        assumptions=("Returns are serially uncorrelated (square-root-of-time rule).",),
        misleading_when=(
            _SMOOTHING_CAVEAT,
            "Returns are serially correlated or volatility changes over time.",
        ),
        minimum_data="At least 2 observations; low confidence below 3 years.",
        reference_implementations=(
            lib(PA, "StdDev.annualized"),
            lib(EMP, "annual_volatility"),
            lib(QS, "stats.volatility"),
        ),
        references=(BACON, LO_2002),
        convention="Sample standard deviation x sqrt(periods per year).",
    ),
)
def annualized_volatility(ctx: MetricContext) -> float:
    return ctx.cache.std * math.sqrt(ctx.ppy)
