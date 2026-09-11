"""Downside-risk metrics (CLAUDE.md sections 12.2 / 12.3)."""

from __future__ import annotations

import math

from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import BACON, EMP, PA, QS, SORTINO_PRICE_1994, lib
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import MetricDocs


@metric(
    id="downside_deviation",
    name="Downside deviation (annualized)",
    category="volatility",
    unit="decimal_return",
    direction="lower_is_better",
    nature="estimated",
    min_data_policy="dispersion",
    annualized=True,
    volatility_based=True,
    assumptions=("mar", "annualization"),
    docs=MetricDocs(
        measures="Variability of returns below the target (0% per period), scaled to a year.",
        formula="sqrt( (1/n) * sum(min(r_t - MAR, 0)^2) ) * sqrt(P), MAR = 0",
        formula_latex=(
            r"\mathrm{DD}_{\text{ann}} = \sqrt{P}\,\mathrm{DD}, \quad "
            r"\mathrm{DD} = \sqrt{\frac{1}{n} \sum_{t=1}^{n} \min(r_t - \tau, 0)^2}, "
            r"\quad \tau = 0"
        ),
        inputs="Periodic simple returns with a regular frequency.",
        retail="How large the losing periods typically are; gains do not count as risk here.",
        institutional="Lower partial moment of order 2 (root), full-sample denominator as in "
        "Sortino & Price (1994); the Sortino ratio denominator.",
        assumptions=("Target (MAR) of 0% per period.", "Square-root-of-time scaling."),
        misleading_when=(
            "Very few losing periods exist: the estimate rests on a handful of observations.",
            "Returns are smoothed, which dampens measured losses.",
        ),
        minimum_data="At least 2 observations; low confidence below 3 years.",
        reference_implementations=(
            lib(PA, "DownsideDeviation(MAR=0, method='full') * sqrt(P)"),
            lib(EMP, "downside_risk(required_return=0)"),
            lib(QS, "stats.sortino (denominator)"),
        ),
        references=(SORTINO_PRICE_1994, BACON),
        convention="MAR = 0; denominator n (all observations), not the number of losing "
        "periods (decision 0006).",
    ),
)
def downside_deviation(ctx: MetricContext) -> float:
    return ctx.cache.downside_deviation * math.sqrt(ctx.ppy)
