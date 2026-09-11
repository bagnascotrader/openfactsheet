"""Distribution-shape metrics (CLAUDE.md section 12.6)."""

from __future__ import annotations

from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import (
    JARQUE_BERA_1987,
    JOANES_GILL_1998,
    PA,
    PANDAS,
    QS,
    SCIPY,
    lib,
)
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import Computed, MetricDocs


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
        undefined_when=(
            "Return variance is zero or underflows in floating point (e.g. identical returns).",
        ),
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
        undefined_when=(
            "Return variance is zero or underflows in floating point (e.g. identical returns).",
        ),
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


@metric(
    id="jarque_bera_pvalue",
    name="Jarque-Bera normality p-value",
    category="distribution",
    unit="probability",
    direction="context_dependent",
    nature="model_dependent",
    min_data_policy="skewness",
    supplementary=True,
    docs=MetricDocs(
        measures="Evidence against normally distributed returns from skewness and kurtosis.",
        formula="JB = n/6 * (g1^2 + g2^2 / 4), g1 = m3/m2^1.5, g2 = m4/m2^2 - 3; p = 1 - F_chi2(2)",
        formula_latex=(
            r"JB = \frac{n}{6}\left( g_1^2 + \frac{g_2^2}{4} \right), \quad "
            r"g_1 = \frac{m_3}{m_2^{3/2}}, \ g_2 = \frac{m_4}{m_2^2} - 3, \quad "
            r"p = 1 - F_{\chi^2_2}(JB)"
        ),
        undefined_when=(
            "Return variance is zero or underflows in floating point (e.g. identical returns).",
        ),
        inputs="Periodic simple returns.",
        retail="A small value (below 0.05) indicates the returns are not bell-shaped, so "
        "volatility-based statistics tell only part of the story.",
        institutional="Jarque & Bera (1987) test with population moments and its asymptotic "
        "chi-squared(2) p-value. A diagnostic, not a performance measure: in small samples the "
        "test has low power and poor size; in very large samples trivial departures are "
        "significant.",
        assumptions=("i.i.d. returns; asymptotic chi-squared distribution of the statistic.",),
        misleading_when=(
            "Samples are short (the asymptotic p-value is unreliable).",
            "Returns are serially correlated or heteroskedastic.",
        ),
        minimum_data="At least 3 observations; low confidence below 60, moderate below 120.",
        reference_implementations=(lib(SCIPY, "stats.jarque_bera"),),
        references=(JARQUE_BERA_1987,),
        convention="Population (biased) skewness and excess kurtosis, as in the original test "
        "(decision 0020).",
    ),
)
def jarque_bera_pvalue(ctx: MetricContext) -> Computed:
    from scipy.stats import chi2

    g1 = ctx.cache.population_skewness
    g2 = ctx.cache.population_kurtosis - 3.0
    stat = ctx.n / 6.0 * (g1**2 + g2**2 / 4.0)
    return Computed(float(chi2.sf(stat, 2)), details={"statistic": stat})
