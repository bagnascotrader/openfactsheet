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
    AHMADI_JAVID_2012,
    BACON,
    BOUDT_PETERSON_CROUX_2008,
    EMP,
    FAVRE_GALEANO_2002,
    HYNDMAN_FAN_1996,
    JORION_2006,
    NUMPY,
    PA,
    QS,
    SKFOLIO,
    ZANGARI_1996,
    lib,
)
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import Computed, MetricDocs
from openfactsheet.utils.math import entropic_value_at_risk

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
    signed_loss=True,
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
    signed_loss=True,
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
    signed_loss=True,
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
    signed_loss=True,
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


@metric(
    id="modified_es_95",
    name="Modified Expected Shortfall (Cornish-Fisher, 95%)",
    category="tail",
    unit="decimal_return",
    direction="higher_is_better",
    signed_loss=True,
    nature="model_dependent",
    min_data_policy="kurtosis",
    volatility_based=True,
    supplementary=True,
    assumptions=("parametric",),
    docs=MetricDocs(
        measures="Parametric 95% Expected Shortfall adjusted for skewness and excess kurtosis.",
        formula="mean - sqrt(m2)/a * phi(h) * [1 + h^3 S/6 + (h^6 - 9h^4 + 9h^2 + 3) S^2/72 "
        "+ (h^4 - 2h^2 - 1) K/24], h = Cornish-Fisher quantile, a = 0.05",
        formula_latex=(
            r"\mathrm{mES}_{95} = \bar r - \frac{\sqrt{m_2}}{a}\,\varphi(h)\left[1 + "
            r"\frac{h^3 S}{6} + \frac{(h^6 - 9h^4 + 9h^2 + 3) S^2}{72} + "
            r"\frac{(h^4 - 2h^2 - 1) K}{24}\right], \quad a = 0.05, \ h = \text{CF quantile of "
            r"modified\_var\_95}"
        ),
        undefined_when=(
            "Return variance is zero or underflows in floating point (e.g. identical returns).",
        ),
        inputs="Periodic simple returns.",
        retail="The average loss in the worst 5% of periods implied by a skew- and fat-tail-"
        "adjusted distribution. Compare with the historical Expected Shortfall.",
        institutional="Modified ES of Boudt, Peterson & Croux (2008), the Cornish-Fisher "
        "analogue of the historical ES, with population moments and the full second-order "
        "expansion. Supplementary and model-dependent; for extreme skewness or kurtosis the "
        "expansion can make it less severe than the modified VaR, which is flagged.",
        assumptions=("The Cornish-Fisher expansion adequately approximates the tail.",),
        misleading_when=(
            "Skewness or kurtosis are extreme (the expansion breaks down).",
            "Samples are short: higher moments are estimated imprecisely.",
        ),
        minimum_data="At least 4 observations; low confidence below 120 observations.",
        reference_implementations=(lib(PA, "ES(p=0.95, method='modified')"),),
        references=(BOUDT_PETERSON_CROUX_2008,),
        convention="Population moments, full expansion, signed return, per period (decision 0022).",
    ),
)
def modified_es_95(ctx: MetricContext) -> Computed:
    from scipy.stats import norm

    a = 1.0 - float(ctx.methodology.get("modified_es.confidence"))
    z = float(norm.ppf(a))
    s = ctx.cache.population_skewness
    k = ctx.cache.population_kurtosis - 3.0
    h = z + (z**2 - 1) * s / 6 + (z**3 - 3 * z) * k / 24 - (2 * z**3 - 5 * z) * s**2 / 36
    bracket = (
        1
        + h**3 * s / 6
        + (h**6 - 9 * h**4 + 9 * h**2 + 3) * s**2 / 72
        + (h**4 - 2 * h**2 - 1) * k / 24
    )
    sigma = float(np.sqrt(ctx.cache.central_moment(2)))
    value = ctx.cache.mean - sigma / a * float(norm.pdf(h)) * bracket
    modified_var = ctx.cache.mean + h * sigma
    notes: tuple[str, ...] = ()
    if value > modified_var:
        notes = (
            "Modified ES is less severe than the modified VaR: the Cornish-Fisher expansion is "
            "unreliable for these moments; rely on the historical Expected Shortfall.",
        )
    return Computed(value, details={"cornish_fisher_quantile": h}, notes=notes)


@metric(
    id="evar_95",
    name="Entropic Value at Risk (95%)",
    category="tail",
    unit="decimal_return",
    direction="higher_is_better",
    signed_loss=True,
    nature="estimated",
    min_data_policy="tail",
    assumptions=("entropic",),
    docs=MetricDocs(
        measures="Entropic (exponential-moment) bound on the 5% tail of single-period returns.",
        formula="-EVaR_0.05(-r), EVaR_a(X) = inf_{z>0} z * ln( mean(exp(X/z)) / a )",
        formula_latex=(
            r"\mathrm{EVaR}_{95} = -\mathrm{EVaR}_{0.05}(-r), \quad "
            r"\mathrm{EVaR}_{a}(X) = \inf_{z > 0} \, z \ln\!\left( \frac{1}{a\,n} "
            r"\sum_{t=1}^{n} e^{X_t / z} \right)"
        ),
        inputs="Periodic simple returns.",
        retail="A conservative loss threshold for bad periods, at least as severe as the "
        "Expected Shortfall and never worse than the worst period.",
        institutional="Entropic VaR (Ahmadi-Javid 2012) of the empirical loss distribution: "
        "the tightest Chernoff bound on VaR, coherent, and more sensitive to extreme losses than "
        "ES. Computed by one-dimensional convex minimization; signed return.",
        assumptions=("The supplied history is representative of the tail.",),
        misleading_when=(
            *_TAIL_CAVEATS,
            "With 20 or fewer observations (n <= 1/0.05) the empirical EVaR equals the worst "
            "period exactly.",
        ),
        minimum_data="At least 2 observations; low confidence below n = 100.",
        reference_implementations=(
            lib(SKFOLIO, "measures.evar", note="Agrees to solver tolerance (about 1e-8)."),
        ),
        references=(AHMADI_JAVID_2012,),
        convention="Empirical distribution of per-period returns, 95%, signed (decision 0021).",
    ),
)
def evar_95(ctx: MetricContext) -> float:
    alpha = 1.0 - float(ctx.methodology.get("entropic.confidence"))
    return -entropic_value_at_risk(-ctx.r, alpha)
