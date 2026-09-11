"""Tail-risk metrics (CLAUDE.md section 12.5).

Confidence levels are canonical (95%) and not user-selectable in the canonical
report.
"""

from __future__ import annotations

import numpy as np

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import (
    ACERBI_TASCHE_2002,
    BACON,
    BOUDT_PETERSON_CROUX_2008,
    EMP,
    FAVRE_GALEANO_2002,
    HYNDMAN_FAN_1996,
    JORION_2006,
    NUMPY,
    PA,
    QS,
    ZANGARI_1996,
    lib,
)
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import Computed, MetricDocs

_TAIL_CAVEATS = (
    "Few observations fall in the 5% tail: with monthly data a 95% estimate rests on "
    "roughly n/20 points.",
    "The history does not contain a stress period.",
    "Returns are smoothed, which compresses the tail.",
)


def _alpha(ctx: MetricContext) -> float:
    return 1.0 - float(ctx.methodology.get("tail.var_confidence"))


@metric(
    id="var_historical_95",
    name="Value at Risk (historical, 95%)",
    category="tail",
    unit="decimal_return",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="tail",
    assumptions=("tail",),
    docs=MetricDocs(
        measures="Return threshold that was breached in the worst 5% of periods.",
        formula="Q_0.05(r), empirical quantile with linear interpolation (Hyndman-Fan type 7)",
        formula_latex=(
            r"\mathrm{VaR}_{95} = Q_{0.05}(r), \quad Q_p(r) = r_{(j)} + (h - j)"
            r"\left(r_{(j+1)} - r_{(j)}\right), \ h = (n-1)p + 1, \ j = \lfloor h \rfloor"
        ),
        inputs="Periodic simple returns.",
        retail="In about 1 period out of 20, the return was this bad or worse.",
        institutional="Historical-simulation VaR at 95% for one observation period; says "
        "nothing about losses beyond the threshold (see Expected Shortfall).",
        assumptions=("The supplied history is representative of the tail.",),
        misleading_when=_TAIL_CAVEATS,
        minimum_data="At least 2 observations; low confidence when fewer than 5 observations "
        "are expected in the tail (n < 100).",
        reference_implementations=(
            lib(
                PA,
                "VaR(p=0.95, method='historical')",
                note="Reports the negated quantile (loss as a positive number in 2.0.4 "
                "internals, negative in the public wrapper).",
            ),
            lib(NUMPY, "quantile(method='linear')"),
            lib(
                QS,
                "stats.value_at_risk",
                agrees=False,
                note="QuantStats defaults to a parametric (normal) VaR.",
            ),
        ),
        references=(JORION_2006, HYNDMAN_FAN_1996),
        convention="95% confidence, per observation period, signed return (negative = loss), "
        "linear interpolation (decision 0010).",
    ),
)
def var_historical_95(ctx: MetricContext) -> float:
    return float(np.quantile(ctx.r, _alpha(ctx), method="linear"))


@metric(
    id="expected_shortfall_historical_95",
    name="Expected Shortfall / CVaR (historical, 95%)",
    category="tail",
    unit="decimal_return",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="tail",
    assumptions=("tail",),
    docs=MetricDocs(
        measures="Average return in the periods at or below the 95% VaR threshold.",
        formula="mean(r_t | r_t <= Q_0.05(r))",
        formula_latex=(
            r"\mathrm{ES}_{95} = \frac{1}{|T|} \sum_{t \in T} r_t, \quad "
            r"T = \{t : r_t \le Q_{0.05}(r)\}"
        ),
        inputs="Periodic simple returns.",
        retail="When things went badly (the worst 5% of periods), this was the average return.",
        institutional="Historical Expected Shortfall (CVaR); a coherent risk measure (Acerbi & "
        "Tasche, 2002) that accounts for the severity of tail losses.",
        assumptions=("The supplied history is representative of the tail.",),
        misleading_when=_TAIL_CAVEATS,
        minimum_data="At least 2 observations; low confidence when fewer than 5 observations "
        "are expected in the tail (n < 100).",
        reference_implementations=(
            lib(
                PA,
                "ES(p=0.95, method='historical')",
                note="Uses returns strictly below the quantile; identical unless an "
                "observation equals the quantile exactly.",
            ),
            lib(
                QS,
                "stats.cvar",
                agrees=False,
                note="QuantStats conditions on a parametric VaR threshold.",
            ),
            lib(
                EMP,
                "conditional_value_at_risk",
                note="Uses returns at or below the 5th percentile.",
            ),
        ),
        references=(ACERBI_TASCHE_2002, JORION_2006, BACON),
        convention="Mean of returns at or below the linear-interpolated 5% quantile; signed.",
    ),
)
def expected_shortfall_historical_95(ctx: MetricContext) -> Computed:
    q = float(np.quantile(ctx.r, _alpha(ctx), method="linear"))
    tail = ctx.r[ctx.r <= q]
    return Computed(float(np.mean(tail)), details={"tail_observations": int(tail.size)})


@metric(
    id="tail_ratio",
    name="Tail ratio (95th / 5th percentile)",
    category="tail",
    unit="ratio",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="tail",
    docs=MetricDocs(
        measures="Size of the right tail relative to the left tail.",
        formula="|Q_0.95(r)| / |Q_0.05(r)|",
        formula_latex=(
            r"\mathrm{TR} = \frac{\left| Q_{0.95}(r) \right|}{\left| Q_{0.05}(r) \right|}"
        ),
        undefined_when=("The 5th percentile return is exactly zero.",),
        inputs="Periodic simple returns.",
        retail="Above 1: the best periods were larger than the worst periods were bad.",
        institutional="Quantile-based asymmetry measure, robust to single extremes but noisy "
        "in short samples.",
        assumptions=("Linear-interpolated empirical quantiles.",),
        misleading_when=_TAIL_CAVEATS[:2],
        minimum_data="At least 2 observations; low confidence below n = 100.",
        reference_implementations=(lib(EMP, "tail_ratio"), lib(QS, "stats.tail_ratio")),
        references=(BACON,),
        convention="Absolute values of the 95th and 5th percentiles (decision 0010).",
    ),
)
def tail_ratio(ctx: MetricContext) -> float:
    alpha = _alpha(ctx)
    lo = float(np.quantile(ctx.r, alpha, method="linear"))
    hi = float(np.quantile(ctx.r, 1.0 - alpha, method="linear"))
    if lo == 0.0:
        raise UndefinedMetric("The 5th percentile return is zero; the tail ratio is undefined.")
    return abs(hi) / abs(lo)


def _parametric_z(ctx: MetricContext) -> float:
    from scipy.stats import norm

    return float(norm.ppf(1.0 - float(ctx.methodology.get("parametric_var.confidence"))))


@metric(
    id="gaussian_var_95",
    name="Value at Risk (Gaussian, 95%)",
    category="tail",
    unit="decimal_return",
    direction="higher_is_better",
    nature="model_dependent",
    min_data_policy="dispersion",
    volatility_based=True,
    supplementary=True,
    assumptions=("parametric",),
    docs=MetricDocs(
        measures="The 5% quantile of a normal distribution with the series' mean and variance.",
        formula="mean + z_0.05 * sqrt(m2), m2 = (1/n) sum (r_t - mean)^2, z_0.05 = -1.645",
        formula_latex=(
            r"\mathrm{VaR}^{N}_{95} = \bar r + z_{0.05} \sqrt{m_2}, \quad "
            r"z_{0.05} = \Phi^{-1}(0.05) \approx -1.645"
        ),
        inputs="Periodic simple returns.",
        retail="The 1-in-20 loss threshold if returns followed a bell curve. Compare it with the "
        "historical VaR: a large gap means the bell curve does not fit.",
        institutional="Parametric (delta-normal) VaR with population moments. Supplementary and "
        "model-dependent: it ignores skewness and fat tails, which the historical and "
        "Cornish-Fisher VaR capture.",
        assumptions=("Normally distributed, i.i.d. returns.",),
        misleading_when=(
            "Returns are skewed or fat-tailed (typical for hedge funds and options strategies).",
            "Returns are smoothed, which understates the variance.",
        ),
        minimum_data="At least 2 observations; low confidence below 3 years.",
        reference_implementations=(
            lib(PA, "VaR(p=0.95, method='gaussian')"),
            lib(
                QS,
                "stats.value_at_risk",
                agrees=False,
                note="QuantStats uses the sample (n - 1) standard deviation.",
            ),
        ),
        references=(JORION_2006, BOUDT_PETERSON_CROUX_2008),
        convention="Population standard deviation sqrt(m2), signed return, per period "
        "(decision 0018).",
    ),
)
def gaussian_var_95(ctx: MetricContext) -> float:
    return ctx.cache.mean + _parametric_z(ctx) * float(np.sqrt(ctx.cache.central_moment(2)))


@metric(
    id="modified_var_95",
    name="Modified VaR (Cornish-Fisher, 95%)",
    category="tail",
    unit="decimal_return",
    direction="higher_is_better",
    nature="model_dependent",
    min_data_policy="kurtosis",
    volatility_based=True,
    supplementary=True,
    assumptions=("parametric",),
    docs=MetricDocs(
        measures="Parametric 95% VaR adjusted for the skewness and excess kurtosis of returns.",
        formula="mean + h * sqrt(m2), h = z + (z^2-1) S/6 + (z^3-3z) K/24 - (2z^3-5z) S^2/36",
        formula_latex=(
            r"\mathrm{mVaR}_{95} = \bar r + h \sqrt{m_2}, \quad "
            r"h = z + \frac{(z^2 - 1) S}{6} + \frac{(z^3 - 3z) K}{24} - \frac{(2z^3 - 5z) S^2}{36},"
            r" \quad z = \Phi^{-1}(0.05), \ S = \frac{m_3}{m_2^{3/2}}, \ K = \frac{m_4}{m_2^2} - 3"
        ),
        undefined_when=(
            "Return variance is zero or underflows in floating point (e.g. identical returns).",
        ),
        inputs="Periodic simple returns.",
        retail="A 1-in-20 loss threshold that accounts for lopsided and fat-tailed returns.",
        institutional="Cornish-Fisher modified VaR (Zangari 1996; Favre & Galeano 2002) with "
        "population moments as in Boudt, Peterson & Croux (2008). Reduces to the Gaussian VaR "
        "when S = K = 0. Supplementary and model-dependent.",
        assumptions=("The Cornish-Fisher expansion adequately approximates the quantile.",),
        misleading_when=(
            "Skewness or kurtosis are extreme: the expansion can become non-monotonic and "
            "unreliable.",
            "Samples are short: higher moments are estimated imprecisely.",
        ),
        minimum_data="At least 4 observations; low confidence below 120 observations (kurtosis "
        "is unstable).",
        reference_implementations=(lib(PA, "VaR(p=0.95, method='modified')"),),
        references=(ZANGARI_1996, FAVRE_GALEANO_2002, BOUDT_PETERSON_CROUX_2008),
        convention="Population moments, signed return, per period (decision 0018).",
    ),
)
def modified_var_95(ctx: MetricContext) -> Computed:
    z = _parametric_z(ctx)
    s = ctx.cache.population_skewness
    k = ctx.cache.population_kurtosis - 3.0
    h = z + (z**2 - 1) * s / 6 + (z**3 - 3 * z) * k / 24 - (2 * z**3 - 5 * z) * s**2 / 36
    value = ctx.cache.mean + h * float(np.sqrt(ctx.cache.central_moment(2)))
    return Computed(
        value, details={"cornish_fisher_quantile": h, "skewness": s, "excess_kurtosis": k}
    )
