"""Downside-risk metrics (CLAUDE.md sections 12.2 / 12.3)."""

from __future__ import annotations

import math

import numpy as np

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


@metric(
    id="semi_deviation",
    name="Semi-deviation (annualized)",
    category="volatility",
    unit="decimal_return",
    direction="lower_is_better",
    nature="estimated",
    min_data_policy="dispersion",
    annualized=True,
    volatility_based=True,
    assumptions=("annualization",),
    docs=MetricDocs(
        measures="Variability of returns below their own mean, scaled to a year.",
        formula="sqrt( (1/n) * sum over r_t < mean of (r_t - mean)^2 ) * sqrt(P)",
        formula_latex=(
            r"\mathrm{SemiDev}_{\text{ann}} = \sqrt{P} \, \sqrt{\frac{1}{n} \sum_{t=1}^{n}"
            r" \min(r_t - \bar r, 0)^2}"
        ),
        inputs="Periodic simple returns with a regular frequency.",
        retail="How large the below-average periods typically are.",
        institutional="Downside deviation with the sample mean as target (Markowitz "
        "semi-variance, square root), full-sample denominator. Unlike downside deviation it "
        "measures dispersion below the mean, not losses.",
        assumptions=("Target equals the sample mean.", "Square-root-of-time scaling."),
        misleading_when=(
            "Returns are smoothed, which compresses deviations.",
            "Compared with semi-deviations that divide by the number of below-mean periods.",
        ),
        minimum_data="At least 2 observations; low confidence below 3 years.",
        reference_implementations=(lib(PA, "SemiDeviation x sqrt(P)"),),
        references=(BACON,),
        convention="Full-sample denominator n, target = mean, annualized by sqrt(P) "
        "(decision 0016).",
    ),
)
def semi_deviation(ctx: MetricContext) -> float:
    below = np.minimum(ctx.r - ctx.cache.mean, 0.0)
    return float(np.sqrt(np.mean(below**2))) * math.sqrt(ctx.ppy)


@metric(
    id="downside_potential",
    name="Downside potential (LPM 1)",
    category="volatility",
    unit="decimal_return",
    direction="lower_is_better",
    nature="estimated",
    min_data_policy="dispersion",
    assumptions=("mar",),
    docs=MetricDocs(
        measures="Average shortfall below the 0% target per period (first lower partial moment).",
        formula="(1/n) * sum max(tau - r_t, 0), tau = 0",
        formula_latex=r"\mathrm{LPM}_1 = \frac{1}{n} \sum_{t=1}^{n} \max(\tau - r_t, 0), \quad"
        r" \tau = 0",
        inputs="Periodic simple returns.",
        retail="The average loss per period, counting gains as zero.",
        institutional="First lower partial moment at target 0; the denominator of the Omega "
        "ratio (Omega = 1 + mean / LPM1 at threshold 0). Per period, not annualized.",
        assumptions=("Target (MAR) of 0% per period.",),
        misleading_when=("Compared across data frequencies (per-period quantity).",),
        minimum_data="At least 2 observations; low confidence below 3 years.",
        reference_implementations=(lib(PA, "DownsideDeviation(MAR=0, potential=TRUE)"),),
        references=(SORTINO_PRICE_1994, BACON),
        convention="Target 0, full-sample denominator n, per period (decision 0016).",
    ),
)
def downside_potential(ctx: MetricContext) -> float:
    return ctx.cache.lower_partial_moment_1
