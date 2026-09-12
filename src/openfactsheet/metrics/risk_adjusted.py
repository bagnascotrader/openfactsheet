"""Risk-adjusted performance ratios (CLAUDE.md section 12.3)."""

from __future__ import annotations

import math

import numpy as np

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import (
    BACON,
    BURKE_1994,
    EMP,
    GLM_2004,
    KAPLAN_KNOWLES_2004,
    KEATING_SHADWICK_2002,
    KESTNER_1996,
    LO_2002,
    MARTIN_MCCANN_1989,
    PA,
    QS,
    SHARPE_1966,
    SHARPE_1994,
    SORTINO_PRICE_1994,
    SORTINO_VDM_PLANTINGA_1999,
    YOUNG_1991,
    lib,
)
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import Computed, MetricDocs


@metric(
    id="sharpe_ratio",
    name="Sharpe ratio",
    category="risk_adjusted",
    unit="ratio",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="ratio_standard",
    annualized=True,
    volatility_based=True,
    assumptions=("risk_free", "sample_std", "annualization"),
    docs=MetricDocs(
        measures="Average return per unit of total volatility, annualized.",
        formula="(mean(r_t) - rf) / std(r_t, ddof=1) * sqrt(P), rf = 0",
        formula_latex=r"\mathrm{SR} = \frac{\bar r - r_f}{s} \sqrt{P}, \quad r_f = 0",
        undefined_when=("Sample standard deviation is exactly zero (constant returns).",),
        inputs="Periodic simple returns with a regular frequency.",
        retail="The Sharpe ratio compares excess return with total return variability. Higher "
        "values indicate more return per unit of measured volatility, but the statistic can be "
        "misleading when returns are smoothed, strongly skewed, serially correlated, or have "
        "significant tail risk.",
        institutional="Ex-post Sharpe (1994) with arithmetic mean and square-root-of-time "
        "annualization. Serial dependence biases the annualized value (Lo, 2002); smoothed "
        "returns inflate it (Getmansky, Lo & Makarov, 2004). Standard error is roughly "
        "sqrt((1 + SR^2/2) / years) under i.i.d. normality.",
        assumptions=(
            "Risk-free rate 0% (methodology 0.1.0).",
            "Volatility is an adequate risk measure (approximately symmetric returns).",
            "Serially uncorrelated returns for annualization.",
        ),
        misleading_when=(
            "Returns are smoothed or stale (hedge funds, private assets): volatility is "
            "understated and the ratio overstated.",
            "Returns are negatively skewed or fat-tailed (e.g. option-selling strategies).",
            "The history is short: sampling error is large.",
            "Cash yields are materially positive (rf = 0 overstates the excess return).",
        ),
        minimum_data="At least 2 observations; low confidence below 3 years.",
        reference_implementations=(
            lib(
                PA,
                "SharpeRatio.annualized(geometric=FALSE)",
                note="The PerformanceAnalytics default (geometric=TRUE) uses the annualized "
                "geometric return in the numerator.",
            ),
            lib(EMP, "sharpe_ratio"),
            lib(QS, "stats.sharpe"),
        ),
        references=(SHARPE_1966, SHARPE_1994, LO_2002, GLM_2004),
        convention="Arithmetic mean / sample std x sqrt(P); rf = 0 (decisions 0005, 0008).",
    ),
)
def sharpe_ratio(ctx: MetricContext) -> float:
    std = ctx.cache.std
    if std == 0.0:
        raise UndefinedMetric("Volatility is zero; the Sharpe ratio is undefined.")
    return ctx.cache.mean / std * math.sqrt(ctx.ppy)


@metric(
    id="sortino_ratio",
    name="Sortino ratio",
    category="risk_adjusted",
    unit="ratio",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="ratio_standard",
    annualized=True,
    volatility_based=True,
    assumptions=("risk_free", "mar", "annualization"),
    docs=MetricDocs(
        measures="Average return in excess of the target per unit of downside deviation, "
        "annualized.",
        formula="P * mean(r_t - MAR) / ( sqrt((1/n) sum min(r_t - MAR, 0)^2) * sqrt(P) ), MAR = 0",
        formula_latex=(
            r"\mathrm{Sortino} = \frac{P\,(\bar r - \tau)}{\mathrm{DD}\,\sqrt{P}}"
            r" = \frac{\bar r - \tau}{\mathrm{DD}} \sqrt{P}, \quad \tau = 0"
        ),
        undefined_when=("No return is below the 0% target (downside deviation is zero).",),
        inputs="Periodic simple returns with a regular frequency.",
        retail="Like the Sharpe ratio, but only losing periods count as risk.",
        institutional="Sortino & Price (1994) with MAR = 0 and full-sample downside deviation. "
        "Downside deviation from few losses is noisy; the ratio is undefined without losses.",
        assumptions=("Target (MAR) of 0% per period.", "Square-root-of-time scaling."),
        misleading_when=(
            "Very few losing periods: the denominator is unstable.",
            "Returns are smoothed or stale.",
        ),
        minimum_data="At least 2 observations and at least one period below the target; low "
        "confidence below 3 years.",
        reference_implementations=(
            lib(
                PA,
                "SortinoRatio(MAR=0) * sqrt(P)",
                note="PerformanceAnalytics reports the per-period ratio.",
            ),
            lib(EMP, "sortino_ratio"),
            lib(QS, "stats.sortino"),
        ),
        references=(SORTINO_PRICE_1994, BACON),
        convention="MAR = 0 per period; full-sample denominator; annualized by sqrt(P) "
        "(decision 0006).",
    ),
)
def sortino_ratio(ctx: MetricContext) -> float:
    dd = ctx.cache.downside_deviation
    if dd == 0.0:
        raise UndefinedMetric(
            "No returns below the 0% target: downside deviation is zero and the Sortino ratio "
            "is undefined."
        )
    return ctx.cache.mean / dd * math.sqrt(ctx.ppy)


@metric(
    id="calmar_ratio",
    name="Calmar ratio",
    category="risk_adjusted",
    unit="ratio",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="ratio_standard",
    annualized=True,
    uses_wealth_path=True,
    assumptions=("annualization", "drawdown", "risk_free"),
    docs=MetricDocs(
        measures="Annualized return per unit of maximum drawdown.",
        formula="CAGR / |max drawdown|",
        formula_latex=r"\mathrm{Calmar} = \frac{\mathrm{CAGR}}{\left| \mathrm{MDD} \right|}",
        undefined_when=("No drawdown occurred (maximum drawdown is zero).",),
        inputs="Periodic simple returns with a regular frequency.",
        retail="How much yearly return was earned relative to the worst peak-to-trough loss.",
        institutional="Young (1991) defined Calmar on a trailing 36-month window; OpenFactsheet "
        "canonically uses the full history so that no window is chosen. Maximum drawdown "
        "grows with history length, so values fall as track records lengthen.",
        assumptions=("Full-history window.", "Risk-free rate 0%."),
        misleading_when=(
            "Histories of different lengths are compared.",
            "The maximum drawdown is a single unrepresentative event.",
        ),
        minimum_data="At least 2 observations and a non-zero drawdown; low confidence below "
        "3 years.",
        reference_implementations=(
            lib(PA, "CalmarRatio"),
            lib(EMP, "calmar_ratio"),
            lib(
                QS,
                "stats.calmar",
                agrees=False,
                note="QuantStats' default CAGR assumes 252 periods per year whatever the data "
                "frequency, so monthly results differ unless periods are adjusted.",
            ),
        ),
        references=(YOUNG_1991, BACON),
        convention="Full history, geometric CAGR, signed max drawdown in absolute value "
        "(decision 0009).",
    ),
)
def calmar_ratio(ctx: MetricContext) -> float:
    mdd = ctx.cache.max_drawdown
    if mdd == 0.0:
        raise UndefinedMetric("No drawdown occurred; the Calmar ratio is undefined (zero divisor).")
    return ctx.cagr / abs(mdd)


@metric(
    id="martin_ratio",
    name="Martin ratio (Ulcer Performance Index)",
    category="risk_adjusted",
    unit="ratio",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="ratio_standard",
    annualized=True,
    uses_wealth_path=True,
    assumptions=("annualization", "drawdown", "risk_free"),
    docs=MetricDocs(
        measures="Annualized return per unit of Ulcer Index.",
        formula="(CAGR - rf) / UlcerIndex, rf = 0",
        formula_latex=r"\mathrm{Martin} = \frac{\mathrm{CAGR} - r_f}{\mathrm{UI}}, \quad r_f = 0",
        undefined_when=("No drawdown occurred (Ulcer Index is zero).",),
        inputs="Periodic simple returns with a regular frequency.",
        retail="Return relative to how deep and prolonged the declines were.",
        institutional="Ulcer Performance Index (Martin & McCann, 1989); penalizes both depth "
        "and duration of drawdowns rather than volatility.",
        assumptions=("Risk-free rate 0%.",),
        misleading_when=("Short histories with few drawdowns.",),
        minimum_data="At least 2 observations and at least one drawdown; low confidence below "
        "3 years.",
        reference_implementations=(
            lib(
                PA,
                "MartinRatio",
                agrees=False,
                note="Inherits the UlcerIndex percent-input issue in PerformanceAnalytics "
                "2.0.4; agreement verified with the drawdown-path Ulcer Index.",
            ),
        ),
        references=(MARTIN_MCCANN_1989, BACON),
        convention="Geometric CAGR over the canonical Ulcer Index.",
    ),
)
def martin_ratio(ctx: MetricContext) -> float:
    ui = ctx.cache.ulcer_index
    if ui == 0.0:
        raise UndefinedMetric(
            "No drawdown occurred; the Ulcer Index is zero and the ratio undefined."
        )
    return ctx.cagr / ui


@metric(
    id="omega_ratio",
    name="Omega ratio",
    category="risk_adjusted",
    unit="ratio",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="ratio_standard",
    assumptions=("omega_threshold",),
    docs=MetricDocs(
        measures="Probability-weighted gains above the threshold relative to probability-"
        "weighted losses below it.",
        formula="sum(max(r_t - L, 0)) / sum(max(L - r_t, 0)), L = 0",
        formula_latex=(
            r"\Omega(L) = \frac{\sum_{t=1}^{n} \max(r_t - L, 0)}"
            r"{\sum_{t=1}^{n} \max(L - r_t, 0)}, \quad L = 0"
        ),
        undefined_when=("No return is below the 0% threshold (zero denominator).",),
        inputs="Periodic simple returns.",
        retail="Total gains divided by total losses; above 1 means gains outweighed losses.",
        institutional="Keating & Shadwick (2002) Omega at threshold 0, using the full empirical "
        "distribution (all moments). Equals 1 + mean / lower partial moment of order 1.",
        assumptions=("Threshold of 0% per period.",),
        misleading_when=(
            "Few losing periods: the denominator is tiny.",
            "Compared across data frequencies.",
        ),
        minimum_data="At least 2 observations and at least one loss; low confidence below 3 years.",
        reference_implementations=(
            lib(PA, "Omega(L=0, method='simple')"),
            lib(EMP, "omega_ratio(required_return=0)"),
            lib(QS, "stats.omega"),
        ),
        references=(KEATING_SHADWICK_2002, BACON),
        convention="Threshold 0 per period; simple empirical estimator; not annualized.",
    ),
)
def omega_ratio(ctx: MetricContext) -> float:
    gains = float(np.sum(np.maximum(ctx.r, 0.0)))
    losses = float(np.sum(np.maximum(-ctx.r, 0.0)))
    if losses == 0.0:
        raise UndefinedMetric("No returns below the 0% threshold; the Omega ratio is undefined.")
    return gains / losses


@metric(
    id="kappa_3_ratio",
    name="Kappa 3 ratio",
    category="risk_adjusted",
    unit="ratio",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="ratio_standard",
    volatility_based=True,
    assumptions=("mar",),
    docs=MetricDocs(
        measures="Mean excess return over the target per unit of third-order lower partial "
        "moment, penalizing large losses more than the Sortino ratio does.",
        formula="(mean(r_t) - tau) / ( (1/n) sum max(tau - r_t, 0)^3 )^(1/3), tau = 0",
        formula_latex=(
            r"K_3 = \frac{\bar r - \tau}{\left( \frac{1}{n} \sum_{t=1}^{n} "
            r"\max(\tau - r_t, 0)^3 \right)^{1/3}}, \quad \tau = 0"
        ),
        undefined_when=("No return is below the 0% target (zero lower partial moment).",),
        inputs="Periodic simple returns.",
        retail="Return per unit of downside risk, where large losses count much more than small "
        "ones.",
        institutional="Kaplan & Knowles (2004) Kappa of order 3 (Sortino is Kappa 2; Omega - 1 is "
        "Kappa 1). The cubic lower partial moment emphasizes tail losses. Per-period, not "
        "annualized.",
        assumptions=("Target (MAR) of 0% per period.",),
        misleading_when=(
            "Very few losing periods: the lower partial moment rests on a handful of values.",
            "Compared across data frequencies (per-period ratio).",
        ),
        minimum_data="At least 2 observations and one loss; low confidence below 3 years.",
        reference_implementations=(lib(PA, "Kappa(MAR=0, l=3)"),),
        references=(KAPLAN_KNOWLES_2004, BACON),
        convention="Target 0, full-sample denominator n, per period (decision 0016).",
    ),
)
def kappa_3_ratio(ctx: MetricContext) -> float:
    order = int(ctx.methodology.get("lower_partial_moments.kappa_order"))
    lpm = float(np.mean(np.maximum(-ctx.r, 0.0) ** order))
    if lpm == 0.0:
        raise UndefinedMetric("No returns below the 0% target; the Kappa 3 ratio is undefined.")
    return float(ctx.cache.mean / lpm ** (1.0 / order))


@metric(
    id="upside_potential_ratio",
    name="Upside potential ratio",
    category="risk_adjusted",
    unit="ratio",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="ratio_standard",
    volatility_based=True,
    assumptions=("mar",),
    docs=MetricDocs(
        measures="Average gain above the target per unit of downside deviation.",
        formula="( (1/n) sum max(r_t - tau, 0) ) / sqrt( (1/n) sum min(r_t - tau, 0)^2 ), tau = 0",
        formula_latex=(
            r"\mathrm{UPR} = \frac{\frac{1}{n} \sum_{t=1}^{n} \max(r_t - \tau, 0)}{\mathrm{DD}},"
            r" \quad \tau = 0"
        ),
        undefined_when=("No return is below the 0% target (downside deviation is zero).",),
        inputs="Periodic simple returns.",
        retail="How much upside the investment delivered for each unit of downside it exposed "
        "investors to.",
        institutional="Sortino, van der Meer & Plantinga (1999): first upper partial moment over "
        "the square root of the second lower partial moment, both at target 0 with full-sample "
        "denominators. Per-period, not annualized.",
        assumptions=("Target (MAR) of 0% per period.",),
        misleading_when=(
            "Very few losing periods: the denominator is unstable.",
            "Compared across data frequencies (per-period ratio).",
        ),
        minimum_data="At least 2 observations and one loss; low confidence below 3 years.",
        reference_implementations=(
            lib(
                PA,
                "UpsidePotentialRatio(MAR=0, method='full')",
                note="The PerformanceAnalytics default method='subset' divides by the number of "
                "gains / losses instead of n.",
            ),
        ),
        references=(SORTINO_VDM_PLANTINGA_1999, BACON),
        convention="Target 0, full-sample denominators (decision 0016).",
    ),
)
def upside_potential_ratio(ctx: MetricContext) -> float:
    dd = ctx.cache.downside_deviation
    if dd == 0.0:
        raise UndefinedMetric(
            "No returns below the 0% target; the upside potential ratio is undefined."
        )
    return float(np.mean(np.maximum(ctx.r, 0.0))) / dd


@metric(
    id="burke_ratio",
    name="Burke ratio",
    category="risk_adjusted",
    unit="ratio",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="ratio_standard",
    annualized=True,
    uses_wealth_path=True,
    assumptions=("annualization", "drawdown", "risk_free"),
    docs=MetricDocs(
        measures="Annualized return per unit of the root sum of squared drawdown depths.",
        formula="(CAGR - rf) / sqrt( sum_k depth_k^2 ), rf = 0",
        formula_latex=(
            r"\mathrm{Burke} = \frac{\mathrm{CAGR} - r_f}{\sqrt{\sum_{k=1}^{K} \delta_k^2}},"
            r" \quad r_f = 0"
        ),
        undefined_when=("No drawdown occurred (K = 0).",),
        inputs="Periodic simple returns with a regular frequency.",
        retail="Return relative to the drawdowns suffered, where deep drawdowns weigh more than "
        "shallow ones.",
        institutional="Burke (1994): penalizes the square of every drawdown episode rather than "
        "only the worst one (Calmar) or their time-average (Martin, Pain).",
        assumptions=("Risk-free rate 0%.", "Every peak-to-recovery episode counts once."),
        misleading_when=(
            "Short histories with few drawdown episodes.",
            "Compared across frequencies or history lengths (the sum grows with both).",
        ),
        minimum_data="At least 2 observations and one drawdown; low confidence below 3 years.",
        reference_implementations=(
            lib(
                PA,
                "BurkeRatio",
                agrees=False,
                note="PerformanceAnalytics 2.0.4 treats runs of negative returns as drawdowns "
                "and multiplies returns by 0.01 (percent-input assumption); agreement is verified "
                "against CAGR / sqrt(sum of findDrawdowns depths squared).",
            ),
        ),
        references=(BURKE_1994, BACON),
        convention="Episode depths from the canonical drawdown engine; geometric CAGR "
        "(decision 0017).",
    ),
)
def burke_ratio(ctx: MetricContext) -> float:
    depths = np.array([e.depth for e in ctx.cache.episodes], dtype=np.float64)
    if depths.size == 0:
        raise UndefinedMetric("No drawdown occurred; the Burke ratio is undefined.")
    return ctx.cagr / float(np.sqrt(np.sum(depths**2)))


@metric(
    id="sterling_ratio",
    name="Sterling ratio",
    category="risk_adjusted",
    unit="ratio",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="ratio_standard",
    annualized=True,
    uses_wealth_path=True,
    assumptions=("annualization", "drawdown", "sterling_excess", "risk_free"),
    docs=MetricDocs(
        measures="Annualized return per unit of maximum drawdown plus a fixed 10% adjustment.",
        formula="CAGR / ( |max drawdown| + 0.10 )",
        formula_latex=(
            r"\mathrm{Sterling} = \frac{\mathrm{CAGR}}{\left| \mathrm{MDD} \right| + e},"
            r" \quad e = 0.10"
        ),
        inputs="Periodic simple returns with a regular frequency.",
        retail="Like the Calmar ratio, but the fixed 10% added to the worst loss keeps the ratio "
        "from exploding for investments with tiny drawdowns.",
        institutional="Sterling-type ratio in the form popularized by Kestner (1996) and Bacon, "
        "using the full-history maximum drawdown. The 10% adjustment is a historical convention, "
        "not an estimate; definitions in the literature vary (e.g. averages of annual maximum "
        "drawdowns).",
        assumptions=("Full-history maximum drawdown.", "Fixed 10% adjustment."),
        misleading_when=(
            "Compared with Sterling ratios computed from averaged annual drawdowns.",
            "Histories of different lengths are compared.",
        ),
        minimum_data="At least 2 observations; low confidence below 3 years.",
        reference_implementations=(lib(PA, "SterlingRatio(excess=0.1)"),),
        references=(KESTNER_1996, BACON),
        convention="CAGR / (|MDD| + 10%), full history (decision 0017).",
    ),
)
def sterling_ratio(ctx: MetricContext) -> float:
    excess = float(ctx.methodology.get("sterling.excess"))
    return ctx.cagr / (abs(ctx.cache.max_drawdown) + excess)


@metric(
    id="pain_ratio",
    name="Pain ratio",
    category="risk_adjusted",
    unit="ratio",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="ratio_standard",
    annualized=True,
    uses_wealth_path=True,
    assumptions=("annualization", "drawdown", "risk_free"),
    docs=MetricDocs(
        measures="Annualized return per unit of Pain Index (average drawdown over time).",
        formula="(CAGR - rf) / PainIndex, rf = 0",
        formula_latex=r"\mathrm{PR} = \frac{\mathrm{CAGR} - r_f}{\mathrm{PI}}, \quad r_f = 0",
        undefined_when=("No drawdown occurred (Pain Index is zero).",),
        inputs="Periodic simple returns with a regular frequency.",
        retail="Return relative to how far below its previous highs the investment typically was.",
        institutional="Zephyr Pain ratio (see Bacon): like the Martin ratio but with the mean "
        "rather than the root-mean-square drawdown, so deep drawdowns weigh less.",
        assumptions=("Risk-free rate 0%.",),
        misleading_when=("Short histories with few drawdowns.",),
        minimum_data="At least 2 observations and one drawdown; low confidence below 3 years.",
        reference_implementations=(
            lib(
                PA,
                "PainRatio",
                agrees=False,
                note="Inherits the PainIndex percent-input issue in PerformanceAnalytics 2.0.4; "
                "agreement is verified against CAGR / mean(|Drawdowns(R)|).",
            ),
        ),
        references=(BACON,),
        convention="Geometric CAGR over the canonical Pain Index (decision 0017).",
    ),
)
def pain_ratio(ctx: MetricContext) -> Computed:
    pain = float(np.mean(np.abs(ctx.cache.drawdown)))
    if pain == 0.0:
        raise UndefinedMetric("No drawdown occurred; the Pain ratio is undefined.")
    return Computed(ctx.cagr / pain, details={"pain_index": pain})


@metric(
    id="recovery_factor",
    name="Recovery factor",
    category="risk_adjusted",
    unit="ratio",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="ratio_standard",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Total compounded return relative to the maximum drawdown.",
        formula="cumulative return / |max drawdown|",
        formula_latex=r"\mathrm{RF} = \frac{W_n - 1}{\left| \mathrm{MDD} \right|}",
        undefined_when=("No drawdown occurred (maximum drawdown is zero).",),
        inputs="Periodic simple returns.",
        retail="How many times over the investment earned back its worst decline.",
        institutional="Net compounded profit over the maximum drawdown (a practitioner "
        "measure used in trading-system evaluation). Not annualized, so it grows with the "
        "length of the track record; compare only across equal histories.",
        assumptions=("Full history.",),
        misleading_when=(
            "Histories of different lengths are compared.",
            "Compared with implementations that use the arithmetic sum of returns.",
        ),
        minimum_data="At least 2 observations and one drawdown; low confidence below 3 years.",
        reference_implementations=(
            lib(
                QS,
                "stats.recovery_factor",
                agrees=False,
                note="QuantStats uses the arithmetic sum of returns in the numerator.",
            ),
        ),
        references=(BACON,),
        convention="Compounded cumulative return over |MDD| (decision 0025).",
    ),
)
def recovery_factor(ctx: MetricContext) -> float:
    mdd = ctx.cache.max_drawdown
    if mdd == 0.0:
        raise UndefinedMetric("No drawdown occurred; the recovery factor is undefined.")
    return ctx.cache.cumulative_return / abs(mdd)


@metric(
    id="sharpe_ratio_autocorrelation_adjusted",
    name="Sharpe ratio (serial-correlation adjusted, Lo 2002)",
    category="risk_adjusted",
    unit="ratio",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="long_horizon_dependence",
    annualized=True,
    assumptions=("risk_free", "sample_std", "annualization"),
    docs=MetricDocs(
        measures="The annualized Sharpe ratio with the square-root-of-time factor replaced by "
        "Lo's (2002) factor, which accounts for serial correlation up to one year.",
        formula="(mean(r_t) / std(r_t, ddof=1)) * q / sqrt(q + 2 sum_{k=1}^{q-1} (q - k) rho_k), "
        "q = round(P)",
        formula_latex=(
            r"\mathrm{SR}_{\mathrm{Lo}} = \frac{\bar r - r_f}{s} \, \eta(q), \quad "
            r"\eta(q) = \frac{q}{\sqrt{q + 2 \sum_{k=1}^{q-1} (q-k) \hat\rho_k}}"
            r" = \sqrt{\frac{q}{\mathrm{VR}(q)}}, \quad q = \operatorname{round}(P), \quad r_f = 0"
        ),
        undefined_when=(
            "The frequency is not regular or there is one observation per year (q = 1).",
            "Fewer than two years of observations (n < 2q).",
            "Sample standard deviation is exactly zero (constant returns).",
            "q + 2 sum (q - k) rho_k <= 0 (estimated autocorrelations imply a non-positive "
            "one-year variance).",
        ),
        inputs="Periodic simple returns with a regular frequency.",
        retail="The Sharpe ratio after allowing for gains or losses that persist from one "
        "period to the next. When returns are smoothed (common for hedge funds and private "
        "assets) this is usually lower than the conventional Sharpe ratio.",
        institutional="Lo (2002) annualization of the per-period Sharpe ratio: eta(q) replaces "
        "sqrt(q); with no autocorrelation the two coincide. Positive autocorrelation (for "
        "example from smoothing) lowers it. The adjustment rests on q - 1 estimated "
        "autocorrelations and is itself noisy for short histories; details report eta, "
        "sqrt(q) and the variance ratio.",
        assumptions=(
            "Risk-free rate 0% (methodology 0.1.0).",
            "Stationary returns; sample autocorrelations up to lag q - 1.",
        ),
        misleading_when=(
            "The history is short relative to one year (the autocorrelations are noisy).",
            "Serial correlation changes over time.",
            "Returns are skewed or fat-tailed (as for the conventional Sharpe ratio).",
        ),
        minimum_data="At least two years of observations; low confidence below 5 years, "
        "moderate below 10 years.",
        reference_implementations=(),
        references=(LO_2002, GLM_2004, SHARPE_1994),
        convention="Horizon one year (q = round(P)); per-period Sharpe ratio as in decision "
        "0008; autocorrelations of the dependence metrics (decision 0029).",
    ),
)
def sharpe_ratio_autocorrelation_adjusted(ctx: MetricContext) -> Computed:
    std = ctx.cache.std
    if std == 0.0:
        raise UndefinedMetric("Volatility is zero; the Sharpe ratio is undefined.")
    dep = ctx.one_year_dependence
    if dep.variance_ratio <= 0.0:
        raise UndefinedMetric(
            "The estimated autocorrelations imply a non-positive one-year variance "
            f"(variance ratio {dep.variance_ratio:.2f}); Lo's adjustment is undefined."
        )
    eta = math.sqrt(dep.q / dep.variance_ratio)
    return Computed(
        ctx.cache.mean / std * eta,
        details={
            "eta": eta,
            "sqrt_q": math.sqrt(dep.q),
            "horizon_periods": dep.q,
            "variance_ratio": dep.variance_ratio,
            "sharpe_per_period": ctx.cache.mean / std,
        },
    )
