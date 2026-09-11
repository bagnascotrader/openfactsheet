"""Distribution-shape metrics (CLAUDE.md section 12.6)."""

from __future__ import annotations

from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import JOANES_GILL_1998, PA, PANDAS, QS, SCIPY, lib
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import MetricDocs


@metric(
    id="skewness",
    name="Skewness",
    category="distribution",
    unit="ratio",
    direction="context_dependent",
    nature="estimated",
    min_data_policy="skewness",
    docs=MetricDocs(
        measures="Asymmetry of the return distribution.",
        formula="G1 = sqrt(n(n-1))/(n-2) * m3 / m2^(3/2), m_k = (1/n) sum (r_t - mean)^k",
        formula_latex=(
            r"G_1 = \frac{\sqrt{n(n-1)}}{n-2} \, \frac{m_3}{m_2^{3/2}}, \quad "
            r"m_k = \frac{1}{n} \sum_{t=1}^{n} (r_t - \bar r)^k"
        ),
        undefined_when=("All returns are identical (m_2 = 0).",),
        inputs="Periodic simple returns.",
        retail="Negative values mean occasional large losses and many small gains; positive "
        "values mean occasional large gains.",
        institutional="Bias-corrected sample skewness (Joanes & Gill type G1). Negative skew "
        "combined with a high Sharpe ratio is a classic signature of hidden tail risk.",
        assumptions=("Returns are identically distributed over the history.",),
        misleading_when=(
            "Samples are short: standard error is roughly sqrt(6/n) (about 0.3 at n = 60).",
            "A single extreme observation dominates the estimate.",
        ),
        minimum_data="At least 3 observations; low confidence below 60, moderate below 120.",
        reference_implementations=(
            lib(SCIPY, "stats.skew(bias=False)"),
            lib(PANDAS, "Series.skew"),
            lib(QS, "stats.skew"),
            lib(
                PA,
                "skewness(method='sample')",
                agrees=False,
                note="PerformanceAnalytics 'sample' uses the population standard deviation, "
                "giving G1 * (n/(n-1))^1.5; its 'moment' method equals the biased g1.",
            ),
        ),
        references=(JOANES_GILL_1998,),
        convention="Adjusted Fisher-Pearson G1, as in pandas and Excel SKEW (decision 0011).",
    ),
)
def skewness(ctx: MetricContext) -> float:
    return ctx.cache.skewness


@metric(
    id="excess_kurtosis",
    name="Excess kurtosis",
    category="distribution",
    unit="ratio",
    direction="context_dependent",
    nature="estimated",
    min_data_policy="kurtosis",
    docs=MetricDocs(
        measures="Tail heaviness relative to a normal distribution (normal = 0).",
        formula="G2 = (n-1)/((n-2)(n-3)) * ((n+1) * m4/m2^2 - 3(n-1))",
        formula_latex=(
            r"G_2 = \frac{n-1}{(n-2)(n-3)} \left[ (n+1) \frac{m_4}{m_2^2} - 3(n-1) \right]"
        ),
        undefined_when=("All returns are identical (m_2 = 0).",),
        inputs="Periodic simple returns.",
        retail="Positive values mean extreme periods (good or bad) happen more often than a "
        "bell curve would suggest.",
        institutional="Bias-corrected sample excess kurtosis (G2). Fat tails make volatility-"
        "based risk measures understate tail risk.",
        assumptions=("Returns are identically distributed over the history.",),
        misleading_when=(
            "Samples are short: kurtosis estimates are extremely unstable.",
            "A single extreme observation dominates the estimate.",
        ),
        minimum_data="At least 4 observations; low confidence below 120, moderate below 240.",
        reference_implementations=(
            lib(SCIPY, "stats.kurtosis(fisher=True, bias=False)"),
            lib(PANDAS, "Series.kurt"),
            lib(QS, "stats.kurtosis"),
            lib(PA, "kurtosis(method='sample_excess')"),
        ),
        references=(JOANES_GILL_1998,),
        convention="Excess (normal = 0) G2, as in pandas and Excel KURT (decision 0011).",
    ),
)
def excess_kurtosis(ctx: MetricContext) -> float:
    return ctx.cache.excess_kurtosis
