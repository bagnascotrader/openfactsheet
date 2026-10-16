"""Volatility / dispersion metrics (CLAUDE.md section 12.2)."""

from __future__ import annotations

import math

import numpy as np

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import (
    BACON,
    EMP,
    GINI_1912,
    LO_2002,
    NUMPY,
    PA,
    QS,
    SKFOLIO,
    YITZHAKI_2003,
    lib,
)
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
        formula_latex=r"s = \sqrt{\frac{1}{n-1} \sum_{t=1}^{n} \left(r_t - \bar r\right)^2}",
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
        formula_latex=r"\sigma_{\text{ann}} = s \sqrt{P}",
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


@metric(
    id="mean_absolute_deviation",
    name="Mean absolute deviation",
    category="volatility",
    unit="decimal_return",
    direction="lower_is_better",
    nature="estimated",
    min_data_policy="dispersion",
    volatility_based=True,
    docs=MetricDocs(
        measures="Average absolute distance of single-period returns from their mean.",
        formula="(1/n) * sum |r_t - mean|",
        formula_latex=r"\mathrm{MAD} = \frac{1}{n} \sum_{t=1}^{n} \left| r_t - \bar r \right|",
        inputs="Periodic simple returns.",
        retail="The typical size of a period's deviation from the average, without squaring "
        "(so single extreme periods weigh less than in volatility).",
        institutional="Mean absolute deviation around the mean (the L1 dispersion used in "
        "Konno-Yamazaki portfolio models); for normal returns MAD = sqrt(2/pi) sigma. Per period.",
        assumptions=("Returns are identically distributed over the history.",),
        misleading_when=(
            "Returns are smoothed or stale.",
            "Compared across data frequencies (per-period quantity).",
        ),
        minimum_data="At least 2 observations; low confidence below 3 years.",
        reference_implementations=(lib(PA, "MeanAbsoluteDeviation"),),
        references=(BACON,),
        convention="Deviation from the sample mean, denominator n, per period.",
    ),
)
def mean_absolute_deviation(ctx: MetricContext) -> float:
    return float(np.mean(np.abs(ctx.r - ctx.cache.mean)))


@metric(
    id="gini_mean_difference",
    name="Gini mean difference",
    category="volatility",
    unit="decimal_return",
    direction="lower_is_better",
    nature="estimated",
    min_data_policy="dispersion",
    volatility_based=True,
    docs=MetricDocs(
        measures="Average absolute difference between the returns of two different periods.",
        formula="MD = sum_{i != j} |r_i - r_j| / (n(n-1)) "
        "= 2 / (n(n-1)) * sum_k (2k - n - 1) r_(k), r_(k) sorted ascending",
        formula_latex=(
            r"\mathrm{MD} = \frac{1}{n(n-1)} \sum_{i=1}^{n} \sum_{j \ne i} \left| r_i - r_j "
            r"\right| = \frac{2}{n(n-1)} \sum_{k=1}^{n} (2k - n - 1)\, r_{(k)}"
        ),
        inputs="Periodic simple returns.",
        retail="How far apart the returns of two periods picked at random typically are; "
        "higher means a bumpier ride. It needs no average to measure from.",
        institutional="Gini's mean difference (Bacon 2nd ed., ch. 2, eq. 2.8), the unbiased "
        "U-statistic over all n(n-1) ordered pairs. Unlike the mean absolute deviation it "
        "measures pairwise distances, not distances from the mean; for normal returns "
        "MD = 2 sigma / sqrt(pi). Yitzhaki (2003) recommends it for non-normal distributions. "
        "Per period, not annualized.",
        assumptions=("Returns are identically distributed over the history.",),
        misleading_when=(
            _SMOOTHING_CAVEAT,
            "Compared across data frequencies (per-period quantity).",
            "Read as a tail-risk measure: like volatility it treats gains and losses alike.",
        ),
        minimum_data="At least 2 observations; low confidence below 3 years.",
        reference_implementations=(lib(SKFOLIO, "measures.gini_mean_difference"),),
        references=(GINI_1912, BACON, YITZHAKI_2003),
        convention="Pair denominator n(n-1) (not n^2), per period, computed from the sorted "
        "returns in O(n log n) (decision 0036).",
    ),
)
def gini_mean_difference(ctx: MetricContext) -> float:
    return ctx.cache.gini_mean_difference


@metric(
    id="relative_mean_difference",
    name="Relative mean difference",
    category="volatility",
    unit="ratio",
    direction="context_dependent",
    nature="estimated",
    min_data_policy="dispersion",
    volatility_based=True,
    docs=MetricDocs(
        measures="Gini mean difference per unit of the (signed) arithmetic mean return.",
        formula="RMD = MD / mean(r_t), signed",
        formula_latex=(
            r"\mathrm{RMD} = \frac{\mathrm{MD}}{\bar r}, \quad "
            r"\mathrm{MD} = \frac{1}{n(n-1)} \sum_{i=1}^{n} \sum_{j \ne i} \left| r_i - r_j "
            r"\right|"
        ),
        undefined_when=("The arithmetic mean return is exactly zero.",),
        inputs="Periodic simple returns.",
        retail="How large the typical gap between two periods' returns is compared with the "
        "average return. A value of 5 means returns typically differ by five times the average "
        "return. A negative value means the average return was negative; it does not mean "
        "dispersion was low.",
        institutional="Bacon (2nd ed., ch. 2, eq. 2.9): mean difference over the signed "
        "arithmetic mean, a coefficient-of-variation analogue built on Gini's mean difference. "
        "Neither higher nor lower is uniformly better: with a positive mean a smaller value means "
        "less dispersion per unit of return, but the sign flips with the mean and the ratio "
        "explodes as the mean approaches zero. Per period, dimensionless.",
        assumptions=("Returns are identically distributed over the history.",),
        misleading_when=(
            "The mean return is close to zero: the ratio becomes arbitrarily large and unstable.",
            "The mean return is negative: the value is negative, and a larger dispersion gives a "
            "more negative number.",
            _SMOOTHING_CAVEAT,
        ),
        minimum_data="At least 2 observations; low confidence below 3 years.",
        reference_implementations=(),
        references=(BACON, GINI_1912),
        convention="Signed arithmetic mean in the denominator, as printed by Bacon (never "
        "|mean|); not annualized (decision 0036).",
    ),
)
def relative_mean_difference(ctx: MetricContext) -> float:
    mean = ctx.cache.mean
    if mean == 0.0:
        raise UndefinedMetric(
            "The mean return is exactly zero; the relative mean difference is undefined."
        )
    return ctx.cache.gini_mean_difference / mean


@metric(
    id="interquartile_range",
    name="Interquartile range",
    category="volatility",
    unit="decimal_return",
    direction="lower_is_better",
    nature="estimated",
    min_data_policy="dispersion",
    volatility_based=True,
    docs=MetricDocs(
        measures="Spread of the middle 50% of single-period returns.",
        formula="Q_0.75(r) - Q_0.25(r), linear interpolation",
        formula_latex=r"\mathrm{IQR} = Q_{0.75}(r) - Q_{0.25}(r)",
        inputs="Periodic simple returns.",
        retail="How far apart typical good and typical bad periods are, ignoring the extremes.",
        institutional="Robust dispersion measure, insensitive to the tails (for normal returns "
        "IQR = 1.349 sigma). Contrast with volatility to see how much the tails drive risk. Per "
        "period.",
        assumptions=("Linear-interpolated empirical quantiles (Hyndman-Fan type 7).",),
        misleading_when=(
            "It deliberately ignores tail risk; never use it alone.",
            "Compared across data frequencies (per-period quantity).",
        ),
        minimum_data="At least 2 observations; low confidence below 3 years.",
        reference_implementations=(lib(NUMPY, "quantile(method='linear')"), lib(PA, "R IQR()")),
        references=(BACON,),
        convention="Linear quantiles, per period (decision 0025).",
    ),
)
def interquartile_range(ctx: MetricContext) -> float:
    q75, q25 = np.quantile(ctx.r, [0.75, 0.25], method="linear")
    return float(q75 - q25)
