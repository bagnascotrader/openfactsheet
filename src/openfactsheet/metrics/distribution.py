"""Distribution-shape metrics (CLAUDE.md section 12.6)."""

from __future__ import annotations

import numpy as np

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import (
    ABDULALI_2006,
    BACON,
    JARQUE_BERA_1987,
    JOANES_GILL_1998,
    PA,
    PANDAS,
    QS,
    SCIPY,
    WATANABE_2006,
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


@metric(
    id="skewness_kurtosis_ratio",
    name="Skewness-kurtosis ratio",
    category="distribution",
    unit="ratio",
    direction="context_dependent",
    nature="estimated",
    min_data_policy="kurtosis",
    docs=MetricDocs(
        measures="Skewness relative to (non-excess) kurtosis: asymmetry scaled by tail heaviness.",
        formula="SKR = G1 / (G2 + 3), G1 and G2 the canonical bias-corrected skewness and excess "
        "kurtosis",
        formula_latex=(
            r"\mathrm{SKR} = \frac{G_1}{G_2 + 3}, \quad "
            r"G_1 = \frac{\sqrt{n(n-1)}}{n-2} \, \frac{m_3}{m_2^{3/2}}, \quad "
            r"G_2 = \frac{n-1}{(n-2)(n-3)} \left[ (n+1) \frac{m_4}{m_2^2} - 3(n-1) \right]"
        ),
        undefined_when=(
            "Return variance is zero or underflows in floating point (e.g. identical returns).",
            "The bias-corrected kurtosis G2 + 3 is zero or negative (possible only in very small "
            "samples).",
        ),
        inputs="Periodic simple returns.",
        retail="Positive values mean the return distribution leans towards occasional large "
        "gains, negative values towards occasional large losses; dividing by kurtosis tempers "
        "the reading when extreme periods are common in both directions. It describes shape; "
        "it is not a measure of performance.",
        institutional="Watanabe's skewness-kurtosis ratio (Bacon 2nd ed., ch. 3, eq. 3.7): "
        "skewness over Pearson (non-excess) kurtosis, computed from the canonical bias-corrected "
        "G1 and G2 so that it is consistent with the reported skewness and excess kurtosis. "
        "It is not a substitute for a risk-adjusted return measure and inherits the large "
        "sampling error of both moment estimates.",
        assumptions=("Returns are identically distributed over the history.",),
        misleading_when=(
            "Samples are short: both skewness and kurtosis estimates are unstable.",
            "A single extreme observation dominates both moments.",
            "Compared with values computed from population moments (g1 / b2), which differ in "
            "small samples.",
        ),
        minimum_data="At least 4 observations; low confidence below 120, moderate below 240.",
        reference_implementations=(
            lib(
                PA,
                "SkewnessKurtosisRatio",
                agrees=False,
                note="PerformanceAnalytics divides the population (moment) skewness g1 by the "
                "population kurtosis m4/m2^2; OpenFactsheet uses the bias-corrected G1 / (G2 + "
                "3). The two converge as n grows.",
            ),
        ),
        references=(WATANABE_2006, BACON),
        convention="Bias-corrected G1 over G2 + 3 (estimators of decision 0011); not skewness "
        "over excess kurtosis (decision 0036).",
    ),
)
def skewness_kurtosis_ratio(ctx: MetricContext) -> float:
    pearson_kurtosis = ctx.cache.excess_kurtosis + 3.0
    if pearson_kurtosis <= 0.0:
        raise UndefinedMetric(
            f"The bias-corrected kurtosis G2 + 3 is {pearson_kurtosis:.3g} (not positive), which "
            "happens only in very small samples; the skewness-kurtosis ratio is undefined."
        )
    return ctx.cache.skewness / pearson_kurtosis


@metric(
    id="bias_ratio",
    name="Bias ratio",
    category="distribution",
    unit="ratio",
    direction="neutral",
    nature="estimated",
    min_data_policy="ratio_standard",
    docs=MetricDocs(
        measures="How many returns fall just above zero (within one standard deviation) "
        "compared with how many fall just below it.",
        formula="BR = #{t : 0 <= r_t <= s} / (1 + #{t : -s <= r_t <= 0}), s = std(r_t, ddof=1)",
        formula_latex=(
            r"\mathrm{BR} = \frac{\#\{t : 0 \le r_t \le s\}}{1 + \#\{t : -s \le r_t \le 0\}}, "
            r"\quad s = \sqrt{\frac{1}{n-1} \sum_{t=1}^{n} \left(r_t - \bar r\right)^2}"
        ),
        undefined_when=("All returns are identical (zero standard deviation).",),
        inputs="Periodic simple returns.",
        retail="A diagnostic of the shape of returns near zero. Values well above 1 mean small "
        "gains were much more common than small losses. That can come from a genuinely positive "
        "average return, from valuation smoothing of hard-to-price assets, or from rounding. It "
        "is not evidence of wrongdoing and is not a fraud detector.",
        institutional="Abdulali's bias ratio (Bacon 2nd ed., ch. 10, eq. 10.17) with the closed "
        "intervals as printed, so an exactly-zero return is counted in both numerator and "
        "denominator. Proposed to flag the asymmetry around zero typical of smoothed or "
        "discretionarily marked NAVs in illiquid strategies; a positive mean that is large "
        "relative to volatility also raises it mechanically. Read it alongside the "
        "autocorrelation, smoothing and zero-return diagnostics, never alone.",
        assumptions=(
            "Window of one sample standard deviation (n - 1) on each side of zero.",
            "Closed intervals: a zero return counts on both sides; returns equal to +s or -s "
            "count.",
        ),
        misleading_when=(
            "Few observations: the counts are small and the ratio jumps by large steps.",
            "Returns are reported with few decimals or many exact zeros (discrete NAVs).",
            "The mean return is large relative to volatility: most returns are then legitimately "
            "positive.",
            "Taken as proof of manipulation: it is only a shape diagnostic.",
        ),
        minimum_data="At least 2 observations, not all identical; low confidence below 3 years.",
        reference_implementations=(),
        references=(ABDULALI_2006, BACON),
        convention="s = sample standard deviation (decision 0003); closed intervals exactly as "
        "printed by Bacon, a zero return counted on both sides; per period (decision 0036).",
    ),
)
def bias_ratio(ctx: MetricContext) -> Computed:
    r = ctx.r
    if float(np.ptp(r)) == 0.0:
        raise UndefinedMetric(
            "All returns are identical; the standard deviation is zero and the bias ratio is "
            "undefined."
        )
    s = ctx.cache.std
    above = int(np.count_nonzero((r >= 0.0) & (r <= s)))
    below = int(np.count_nonzero((r >= -s) & (r <= 0.0)))
    zeros = int(np.count_nonzero(r == 0.0))
    return Computed(
        above / (1.0 + below),
        details={
            "count_0_to_s": above,
            "count_minus_s_to_0": below,
            "zero_returns_counted_both_sides": zeros,
            "standard_deviation": s,
        },
    )


@metric(
    id="volatility_skewness",
    name="Volatility skewness",
    category="distribution",
    unit="ratio",
    direction="context_dependent",
    nature="estimated",
    min_data_policy="ratio_standard",
    volatility_based=True,
    assumptions=("mar",),
    docs=MetricDocs(
        measures="Upside variance relative to downside variance around the 0% target.",
        formula="VS = UPM2 / LPM2, UPM2 = (1/n) sum max(r_t - tau, 0)^2, "
        "LPM2 = (1/n) sum max(tau - r_t, 0)^2, tau = 0",
        formula_latex=(
            r"\mathrm{VS} = \frac{\frac{1}{n} \sum_{t=1}^{n} \max(r_t - \tau, 0)^2}"
            r"{\frac{1}{n} \sum_{t=1}^{n} \max(\tau - r_t, 0)^2}, \quad \tau = 0"
        ),
        undefined_when=("No return is below the 0% target (zero downside variance).",),
        inputs="Periodic simple returns.",
        retail="Compares how much returns vary above zero with how much they vary below it. "
        "Above 1, the variability came more from gains; below 1, more from losses. It says "
        "nothing about the average return.",
        institutional="Bacon (2nd ed., ch. 6, eq. 6.32): second upper partial moment over "
        "second lower partial moment at the canonical target 0 with full-sample denominators "
        "(the n cancel). No square roots: Bacon's variability skewness (p. 131) is its square "
        "root, a monotonic transform not reported separately. The ratio is dominated by the "
        "largest deviations and explodes when losses are rare.",
        assumptions=("Target (MAR) of 0% per period.",),
        misleading_when=(
            "Very few losing periods: the denominator rests on a handful of values.",
            "Read as a performance ranking: it ignores the level of returns.",
            "Returns are smoothed, which dampens measured losses.",
        ),
        minimum_data="At least 2 observations and one loss; low confidence below 3 years.",
        reference_implementations=(lib(PA, "VolatilitySkewness(MAR=0, stat='volatility')"),),
        references=(BACON,),
        convention="Target 0 and full-sample denominators as for the other partial-moment "
        "measures (decision 0016); not annualized (decision 0036).",
    ),
)
def volatility_skewness(ctx: MetricContext) -> float:
    tau = float(ctx.methodology.get("lower_partial_moments.target"))
    upm2 = float(np.mean(np.maximum(ctx.r - tau, 0.0) ** 2))
    lpm2 = float(np.mean(np.maximum(tau - ctx.r, 0.0) ** 2))
    if lpm2 == 0.0:
        raise UndefinedMetric(
            "No returns below the 0% target; the volatility skewness is undefined."
        )
    return upm2 / lpm2
