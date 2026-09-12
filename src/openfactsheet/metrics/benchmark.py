"""Benchmark-relative metrics (CLAUDE.md section 12.9).

Only computed when a benchmark is explicitly supplied; always on the aligned
intersection of periods, whose size is reported separately.
"""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import (
    BACON,
    EMP,
    FABOZZI_FRANCIS_1977,
    GOODWIN_1998,
    GRINOLD_KAHN_2000,
    JENSEN_1968,
    MODIGLIANI_1997,
    MORNINGSTAR_BATTING,
    MORNINGSTAR_CAPTURE,
    NUMPY,
    PA,
    QS,
    STATSMODELS,
    TREYNOR_1965,
    TREYNOR_BLACK_1973,
    lib,
)
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import Computed, MetricDocs

_OVERLAP = "Computed on the aligned benchmark overlap only (never filled)."
_BENCH_CAVEATS = (
    "The benchmark is not representative of the strategy's opportunity set.",
    "The overlap with the benchmark is short.",
)


@metric(
    id="beta",
    name="Beta",
    category="benchmark",
    unit="beta",
    direction="context_dependent",
    nature="estimated",
    min_data_policy="benchmark_regression",
    requires_benchmark=True,
    assumptions=("benchmark", "regression"),
    docs=MetricDocs(
        measures="Sensitivity of fund returns to benchmark returns.",
        formula="slope b in OLS: r_fund,t = a + b * r_bench,t + e_t",
        formula_latex=(
            r"\hat\beta = \frac{\sum_{t=1}^{m} (r_t - \bar r)(b_t - \bar b)}"
            r"{\sum_{t=1}^{m} (b_t - \bar b)^2}"
            r" \quad \text{(OLS slope of } r_t = \alpha + \beta b_t + \varepsilon_t)"
        ),
        undefined_when=("Benchmark returns are constant over the aligned periods.",),
        inputs="Fund and benchmark returns on aligned periods.",
        retail="A beta of 1 means the fund tended to move one-for-one with the benchmark; 0.5 "
        "means about half as much.",
        institutional="OLS beta against the supplied benchmark with rf = 0; details include "
        "the standard error and t-statistic (conventional i.i.d. errors).",
        assumptions=("Linear, stable relationship over the overlap.", "Risk-free rate 0%."),
        misleading_when=(
            *_BENCH_CAVEATS,
            "Returns are smoothed: lagged benchmark exposure is missed and beta understated.",
            "The relationship is nonlinear (e.g. option-like strategies).",
        ),
        minimum_data="At least 3 aligned observations; low confidence below 3 years of overlap.",
        reference_implementations=(
            lib(PA, "CAPM.beta"),
            lib(EMP, "beta"),
            lib(STATSMODELS, "OLS"),
        ),
        references=(JENSEN_1968, BACON),
        convention="Total returns (rf = 0), OLS with intercept (decision 0012).",
    ),
)
def beta(ctx: MetricContext) -> Computed:
    ols = ctx.bench.ols
    return Computed(
        ols.beta,
        details={
            "standard_error": ols.beta_se,
            "t_statistic": ols.beta_t,
            "p_value": ols.beta_pvalue,
        },
    )


@metric(
    id="alpha",
    name="Alpha (annualized, CAPM regression)",
    category="benchmark",
    unit="decimal_return",
    direction="higher_is_better",
    nature="model_dependent",
    min_data_policy="benchmark_regression",
    requires_benchmark=True,
    annualized=True,
    assumptions=("benchmark", "regression", "annualization"),
    docs=MetricDocs(
        measures="Average return not explained by benchmark exposure, annualized.",
        formula="P * a, with a the intercept of OLS: r_fund,t = a + b * r_bench,t + e_t",
        formula_latex=(
            r"\alpha_{\text{ann}} = P \, \hat\alpha, \quad "
            r"\hat\alpha = \bar r - \hat\beta \, \bar b"
        ),
        undefined_when=("Benchmark returns are constant over the aligned periods.",),
        inputs="Fund and benchmark returns on aligned periods with a regular frequency.",
        retail="The part of the fund's yearly return that the benchmark does not explain; it "
        "depends heavily on which benchmark is used.",
        institutional="Jensen-style single-index alpha against the supplied benchmark with "
        "rf = 0, annualized arithmetically. Details report the per-period intercept, its "
        "standard error, t-statistic and p-value. Statistical significance, not the point "
        "estimate, indicates whether alpha is distinguishable from zero.",
        assumptions=(
            "Single-index (CAPM-style) model with the supplied benchmark.",
            "Risk-free rate 0%.",
            "Arithmetic annualization of the intercept.",
        ),
        misleading_when=(
            *_BENCH_CAVEATS,
            "Omitted risk factors (size, value, momentum, credit, illiquidity) masquerade as "
            "alpha.",
            "Returns are smoothed or the history is short.",
        ),
        minimum_data="At least 3 aligned observations; low confidence below 3 years of overlap.",
        reference_implementations=(
            lib(
                PA, "CAPM.alpha * P", note="PerformanceAnalytics reports the per-period intercept."
            ),
            lib(
                EMP,
                "alpha",
                agrees=False,
                note="empyrical annualizes geometrically: (1 + a)^P - 1.",
            ),
        ),
        references=(JENSEN_1968, BACON),
        convention="Per-period OLS intercept x periods per year (decision 0012).",
    ),
)
def alpha(ctx: MetricContext) -> Computed:
    ols = ctx.bench.ols
    return Computed(
        ols.alpha * ctx.ppy,
        details={
            "per_period": ols.alpha,
            "standard_error_per_period": ols.alpha_se,
            "t_statistic": ols.alpha_t,
            "p_value": ols.alpha_pvalue,
        },
    )


@metric(
    id="r_squared",
    name="R-squared",
    category="benchmark",
    unit="fraction",
    direction="neutral",
    nature="estimated",
    min_data_policy="benchmark_regression",
    requires_benchmark=True,
    assumptions=("benchmark", "regression"),
    docs=MetricDocs(
        measures="Share of fund return variance explained by the benchmark.",
        formula="1 - SSR/SST of the OLS regression (equals correlation^2 for one regressor)",
        formula_latex=(
            r"R^2 = 1 - \frac{\sum_{t=1}^{m} \hat\varepsilon_t^2}{\sum_{t=1}^{m} (r_t - \bar r)^2},"
            r" \quad \hat\varepsilon_t = r_t - \hat\alpha - \hat\beta b_t"
        ),
        undefined_when=(
            "Benchmark returns are constant over the aligned periods.",
            "Fund returns are constant over the aligned periods (no variance to explain).",
        ),
        inputs="Fund and benchmark returns on aligned periods.",
        retail="How closely the fund's ups and downs followed the benchmark (1 = perfectly).",
        institutional="Low R-squared means beta and alpha say little about the fund; the "
        "benchmark may be inappropriate.",
        assumptions=("Linear relationship.",),
        misleading_when=_BENCH_CAVEATS,
        minimum_data="At least 3 aligned observations; low confidence below 3 years of overlap.",
        reference_implementations=(lib(STATSMODELS, "OLS.rsquared"),),
        references=(BACON,),
        convention="Regression with intercept.",
    ),
)
def r_squared(ctx: MetricContext) -> float:
    ols = ctx.bench.ols
    if float(np.ptp(ctx.bench.fund)) == 0.0:
        raise UndefinedMetric(
            "Fund returns are constant over the aligned periods; there is no variance to "
            "explain and R-squared is undefined."
        )
    return ols.r_squared


@metric(
    id="correlation",
    name="Correlation with benchmark",
    category="benchmark",
    unit="correlation",
    direction="neutral",
    nature="estimated",
    min_data_policy="benchmark_regression",
    requires_benchmark=True,
    assumptions=("benchmark",),
    docs=MetricDocs(
        measures="Linear co-movement of fund and benchmark returns.",
        formula="Pearson correlation of aligned returns",
        formula_latex=(
            r"\rho_{rb} = \frac{\sum_{t=1}^{m} (r_t - \bar r)(b_t - \bar b)}"
            r"{\sqrt{\sum_{t=1}^{m} (r_t - \bar r)^2 \, \sum_{t=1}^{m} (b_t - \bar b)^2}}"
        ),
        undefined_when=("Fund or benchmark returns are constant over the aligned periods.",),
        inputs="Fund and benchmark returns on aligned periods.",
        retail="+1 means the fund moved exactly with the benchmark, 0 no linear relation, -1 "
        "exactly opposite.",
        institutional="Pearson correlation; sensitive to outliers and to regime changes.",
        assumptions=("Linear dependence.",),
        misleading_when=(*_BENCH_CAVEATS, "Dependence is nonlinear or tail-specific."),
        minimum_data="At least 3 aligned observations; low confidence below 3 years of overlap.",
        reference_implementations=(lib(NUMPY, "corrcoef"),),
        references=(BACON,),
        convention="Pearson product-moment correlation.",
    ),
)
def correlation(ctx: MetricContext) -> float:
    b = ctx.bench
    if float(np.ptp(b.fund)) == 0.0 or float(np.ptp(b.bench)) == 0.0:
        raise UndefinedMetric("One of the series is constant; correlation is undefined.")
    return float(np.corrcoef(b.fund, b.bench)[0, 1])


@metric(
    id="tracking_error",
    name="Tracking error (annualized)",
    category="benchmark",
    unit="decimal_return",
    direction="context_dependent",
    nature="estimated",
    min_data_policy="benchmark_simple",
    requires_benchmark=True,
    annualized=True,
    volatility_based=True,
    assumptions=("benchmark", "sample_std", "annualization"),
    docs=MetricDocs(
        measures="Volatility of the difference between fund and benchmark returns, annualized.",
        formula="std(r_fund,t - r_bench,t, ddof=1) * sqrt(P)",
        formula_latex=(
            r"\mathrm{TE} = s_a \sqrt{P}, \quad s_a = \sqrt{\frac{1}{m-1} \sum_{t=1}^{m}"
            r" (a_t - \bar a)^2}, \quad a_t = r_t - b_t"
        ),
        inputs="Fund and benchmark returns on aligned periods with a regular frequency.",
        retail="How much the fund's results differed from the benchmark from period to period.",
        institutional="Ex-post tracking error (active risk); the Information Ratio denominator.",
        assumptions=("Square-root-of-time scaling.",),
        misleading_when=(*_BENCH_CAVEATS, "Returns are smoothed."),
        minimum_data="At least 2 aligned observations; low confidence below 3 years of overlap.",
        reference_implementations=(lib(PA, "TrackingError"), lib(EMP, "tracking_error")),
        references=(GRINOLD_KAHN_2000, BACON),
        convention="Sample standard deviation of arithmetic active returns x sqrt(P).",
    ),
)
def tracking_error(ctx: MetricContext) -> float:
    return float(np.std(ctx.bench.active, ddof=1)) * math.sqrt(ctx.ppy)


@metric(
    id="active_return",
    name="Active return (annualized, arithmetic)",
    category="benchmark",
    unit="decimal_return",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="benchmark_simple",
    requires_benchmark=True,
    annualized=True,
    assumptions=("benchmark", "annualization"),
    docs=MetricDocs(
        measures="Average fund-minus-benchmark return, annualized.",
        formula="P * mean(r_fund,t - r_bench,t)",
        formula_latex=r"\mathrm{AR} = P \, \bar a = \frac{P}{m} \sum_{t=1}^{m} (r_t - b_t)",
        inputs="Fund and benchmark returns on aligned periods with a regular frequency.",
        retail="How much the fund returned above (or below) the benchmark per year, on average.",
        institutional="Arithmetic active return, consistent with the Information Ratio "
        "numerator; differs from the difference of geometric annualized returns (the "
        "PerformanceAnalytics ActivePremium).",
        assumptions=("Linear annualization of the mean.",),
        misleading_when=_BENCH_CAVEATS,
        minimum_data="At least 2 aligned observations; low confidence below 3 years of overlap.",
        reference_implementations=(
            lib(
                PA,
                "ActivePremium",
                agrees=False,
                note="Difference of geometric annualized returns.",
            ),
        ),
        references=(GRINOLD_KAHN_2000,),
        convention="Arithmetic mean of active returns x periods per year (decision 0012).",
    ),
)
def active_return(ctx: MetricContext) -> float:
    return float(np.mean(ctx.bench.active)) * ctx.ppy


@metric(
    id="information_ratio",
    name="Information ratio",
    category="benchmark",
    unit="ratio",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="benchmark_simple",
    requires_benchmark=True,
    annualized=True,
    volatility_based=True,
    assumptions=("benchmark", "sample_std", "annualization"),
    docs=MetricDocs(
        measures="Active return per unit of tracking error, annualized.",
        formula="P * mean(a_t) / (std(a_t, ddof=1) * sqrt(P)), a_t = r_fund,t - r_bench,t",
        formula_latex=(
            r"\mathrm{IR} = \frac{P \, \bar a}{s_a \sqrt{P}} = \frac{\bar a}{s_a} \sqrt{P}"
        ),
        undefined_when=("Tracking error is exactly zero (fund equals benchmark plus a constant).",),
        inputs="Fund and benchmark returns on aligned periods with a regular frequency.",
        retail="How consistently the fund beat (or lagged) its benchmark relative to how much "
        "it deviated from it.",
        institutional="Arithmetic ex-post Information Ratio (Grinold & Kahn), equal to the "
        "Sharpe ratio of active returns. PerformanceAnalytics divides the difference of "
        "geometric annualized returns instead.",
        assumptions=("Square-root-of-time scaling.",),
        misleading_when=(*_BENCH_CAVEATS, "Returns are smoothed.", "Tracking error is tiny."),
        minimum_data="At least 2 aligned observations; low confidence below 3 years of overlap.",
        reference_implementations=(
            lib(
                PA,
                "InformationRatio",
                agrees=False,
                note="Uses ActivePremium (geometric) / TrackingError.",
            ),
            lib(
                QS,
                "stats.information_ratio",
                agrees=False,
                note="QuantStats reports the non-annualized per-period ratio.",
            ),
        ),
        references=(GRINOLD_KAHN_2000, GOODWIN_1998),
        convention="Arithmetic active mean over tracking error (decision 0012).",
    ),
)
def information_ratio(ctx: MetricContext) -> float:
    active = ctx.bench.active
    te = float(np.std(active, ddof=1))
    if te == 0.0:
        raise UndefinedMetric("Tracking error is zero; the Information ratio is undefined.")
    return float(np.mean(active)) / te * math.sqrt(ctx.ppy)


@metric(
    id="treynor_ratio",
    name="Treynor ratio",
    category="benchmark",
    unit="ratio",
    direction="higher_is_better",
    nature="model_dependent",
    min_data_policy="benchmark_regression",
    requires_benchmark=True,
    annualized=True,
    assumptions=("benchmark", "regression", "risk_free", "annualization"),
    docs=MetricDocs(
        measures="Annualized return per unit of benchmark beta.",
        formula="P * mean(r_fund,t - rf) / beta, rf = 0",
        formula_latex=(
            r"\mathrm{TR} = \frac{P\,(\bar r^{(m)} - r_f)}{\hat\beta}, \quad r_f = 0, \quad "
            r"\bar r^{(m)} = \frac{1}{m} \sum_{t=1}^{m} r_t \text{ (aligned periods)}"
        ),
        undefined_when=(
            "Benchmark returns are constant (beta undefined).",
            "Estimated beta is exactly zero.",
        ),
        inputs="Fund and benchmark returns on aligned periods with a regular frequency.",
        retail="Return earned per unit of market (benchmark) risk taken.",
        institutional="Treynor (1965) with arithmetic annualized mean on the aligned sample; "
        "only meaningful for well-diversified portfolios with a stable, clearly positive beta.",
        assumptions=("Risk-free rate 0%.", "Beta is the relevant risk measure."),
        misleading_when=(
            *_BENCH_CAVEATS,
            "Beta is close to zero or negative: the ratio explodes or changes sign.",
            "The portfolio is not diversified (idiosyncratic risk is ignored).",
        ),
        minimum_data="At least 3 aligned observations; low confidence below 3 years of overlap.",
        reference_implementations=(
            lib(
                PA,
                "TreynorRatio",
                agrees=False,
                note="Uses the geometric annualized return in the numerator.",
            ),
        ),
        references=(TREYNOR_1965, BACON),
        convention="Arithmetic annualized mean / OLS beta on aligned periods (decision 0012).",
    ),
)
def treynor_ratio(ctx: MetricContext) -> Computed:
    b = ctx.bench
    beta_ = b.ols.beta
    if beta_ == 0.0:
        raise UndefinedMetric("Beta is zero; the Treynor ratio is undefined.")
    notes: tuple[str, ...] = ()
    if beta_ < 0.3:
        notes = (
            f"Beta is {beta_:.2f}; the Treynor ratio is unstable or not meaningful for "
            "small or negative betas.",
        )
    return Computed(float(np.mean(b.fund)) * ctx.ppy / beta_, details={"beta": beta_}, notes=notes)


def _annualized_geometric(x: npt.NDArray[np.float64], ppy: float) -> float:
    growth = float(np.prod(1.0 + x))
    if growth <= 0.0:
        return -1.0
    return float(growth ** (ppy / x.shape[0]) - 1.0)


def _capture(ctx: MetricContext, up: bool) -> Computed:
    b = ctx.bench
    mask = b.bench > 0.0 if up else b.bench < 0.0
    side = "up" if up else "down"
    k = int(mask.sum())
    if k == 0:
        raise UndefinedMetric(f"The benchmark has no {side} periods in the overlap.")
    fund_ann = _annualized_geometric(b.fund[mask], ctx.ppy)
    bench_ann = _annualized_geometric(b.bench[mask], ctx.ppy)
    if bench_ann == 0.0:
        raise UndefinedMetric(f"Benchmark {side}-period return is zero; capture is undefined.")
    notes: tuple[str, ...] = ()
    if k < 12:
        notes = (f"Only {k} benchmark {side} periods in the overlap.",)
    return Computed(
        fund_ann / bench_ann,
        details={
            f"{side}_periods": k,
            "fund_annualized": fund_ann,
            "benchmark_annualized": bench_ann,
        },
        notes=notes,
    )


_CAPTURE_REFS = (
    lib(EMP, "up_capture / down_capture"),
    lib(
        PA,
        "UpDownRatios(method='Capture')",
        agrees=False,
        note="PerformanceAnalytics divides sums of returns and counts zero-benchmark periods "
        "as down periods.",
    ),
)


@metric(
    id="upside_capture",
    name="Upside capture ratio",
    category="benchmark",
    unit="ratio",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="benchmark_simple",
    requires_benchmark=True,
    annualized=True,
    assumptions=("benchmark", "annualization"),
    docs=MetricDocs(
        measures="Fund return in benchmark up periods relative to the benchmark's, compounded.",
        formula="annualized geometric fund return over {t : r_bench,t > 0} / same for benchmark",
        formula_latex=(
            r"\mathrm{UC} = \frac{G(U, r)}{G(U, b)}, \quad U = \{t : b_t > 0\}, \quad "
            r"G(S, x) = \begin{cases} \left(\prod_{t \in S} (1 + x_t)\right)^{P/|S|} - 1"
            r" & \prod_{t \in S} (1 + x_t) > 0 \\ -1 & \text{otherwise} \end{cases}"
        ),
        undefined_when=(
            "The benchmark has no up periods in the overlap.",
            "The benchmark's compounded up-period return is exactly zero.",
        ),
        inputs="Fund and benchmark returns on aligned periods with a regular frequency.",
        retail="Above 1 (100%): the fund gained more than the benchmark when the benchmark rose.",
        institutional="Morningstar-style geometric upside capture; read together with downside "
        "capture.",
        assumptions=("Up periods defined by strictly positive benchmark returns.",),
        misleading_when=(*_BENCH_CAVEATS, "Few up periods in the overlap."),
        minimum_data="At least 2 aligned observations and one up period; low confidence below "
        "3 years of overlap.",
        reference_implementations=_CAPTURE_REFS,
        references=(MORNINGSTAR_CAPTURE, BACON),
        convention="Geometric, annualized over the up periods (decision 0012).",
    ),
)
def upside_capture(ctx: MetricContext) -> Computed:
    return _capture(ctx, up=True)


@metric(
    id="downside_capture",
    name="Downside capture ratio",
    category="benchmark",
    unit="ratio",
    direction="lower_is_better",
    nature="derived",
    min_data_policy="benchmark_simple",
    requires_benchmark=True,
    annualized=True,
    assumptions=("benchmark", "annualization"),
    docs=MetricDocs(
        measures="Fund return in benchmark down periods relative to the benchmark's, compounded.",
        formula="annualized geometric fund return over {t : r_bench,t < 0} / same for benchmark",
        formula_latex=(
            r"\mathrm{DC} = \frac{G(D, r)}{G(D, b)}, \quad D = \{t : b_t < 0\}"
            r" \quad (G \text{ as for upside capture})"
        ),
        undefined_when=(
            "The benchmark has no down periods in the overlap.",
            "The benchmark's compounded down-period return is exactly zero.",
        ),
        inputs="Fund and benchmark returns on aligned periods with a regular frequency.",
        retail="Below 1 (100%): the fund lost less than the benchmark when the benchmark fell. "
        "Negative: the fund gained on average when the benchmark fell.",
        institutional="Morningstar-style geometric downside capture; read together with upside "
        "capture.",
        assumptions=("Down periods defined by strictly negative benchmark returns.",),
        misleading_when=(*_BENCH_CAVEATS, "Few down periods in the overlap."),
        minimum_data="At least 2 aligned observations and one down period; low confidence below "
        "3 years of overlap.",
        reference_implementations=_CAPTURE_REFS,
        references=(MORNINGSTAR_CAPTURE, BACON),
        convention="Geometric, annualized over the down periods (decision 0012).",
    ),
)
def downside_capture(ctx: MetricContext) -> Computed:
    return _capture(ctx, up=False)


@metric(
    id="capture_ratio",
    name="Capture ratio (upside / downside capture)",
    category="benchmark",
    unit="ratio",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="benchmark_simple",
    requires_benchmark=True,
    annualized=True,
    assumptions=("benchmark", "annualization"),
    docs=MetricDocs(
        measures="Upside capture divided by downside capture: how much of the benchmark's gains "
        "the fund kept per unit of the benchmark's losses it took.",
        formula="upside_capture / downside_capture",
        formula_latex=r"\mathrm{CR} = \frac{\mathrm{UC}}{\mathrm{DC}}, \quad \mathrm{DC} > 0",
        undefined_when=(
            "Upside or downside capture is undefined (no up or no down benchmark periods, or a "
            "zero compounded benchmark return on one side).",
            "Downside capture is zero or negative (the fund gained on average when the benchmark "
            "fell); the ratio's sign would then be meaningless. Upside and downside capture are "
            "still reported.",
        ),
        inputs="Fund and benchmark returns on aligned periods with a regular frequency.",
        retail="Above 1: the fund participated more in rising markets than in falling ones. A "
        "fund with 80% upside and 60% downside capture has a capture ratio of about 1.33.",
        institutional="Ratio of the Morningstar-style geometric capture ratios of this report. "
        "It hides the level of participation (a fund with 10% / 5% capture has the same ratio "
        "as one with 120% / 60%); always read it with both components.",
        assumptions=("Up / down periods defined by the sign of the benchmark return.",),
        misleading_when=(
            *_BENCH_CAVEATS,
            "Few up or down periods in the overlap.",
            "Participation levels differ greatly: the ratio discards them.",
        ),
        minimum_data="At least 2 aligned observations with at least one up and one down period; "
        "low confidence below 3 years of overlap.",
        reference_implementations=(
            lib(EMP, "up_down_capture"),
            lib(
                PA,
                "UpDownRatios(method='Capture')",
                agrees=False,
                note="Ratio of PerformanceAnalytics' arithmetic (summed) capture ratios.",
            ),
        ),
        references=(MORNINGSTAR_CAPTURE, BACON),
        convention="Geometric annualized capture ratios; downside capture must be positive "
        "(decision 0027).",
    ),
)
def capture_ratio(ctx: MetricContext) -> Computed:
    up = _capture(ctx, up=True)
    down = _capture(ctx, up=False)
    if down.value <= 0.0:
        raise UndefinedMetric(
            f"Downside capture is {down.value:.2f} (the fund did not lose, on average, when the "
            "benchmark fell); a capture ratio with a non-positive denominator is not meaningful. "
            "See upside and downside capture."
        )
    return Computed(
        up.value / down.value,
        details={"upside_capture": up.value, "downside_capture": down.value},
        notes=up.notes + down.notes,
    )


@metric(
    id="batting_average",
    name="Batting average (share of periods beating the benchmark)",
    category="benchmark",
    unit="fraction",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="benchmark_simple",
    requires_benchmark=True,
    assumptions=("benchmark",),
    docs=MetricDocs(
        measures="Share of aligned periods in which the fund's return exceeded the benchmark's.",
        formula="(1/m) * #{t : r_fund,t > r_bench,t}",
        formula_latex=(
            r"\mathrm{BA} = \frac{1}{m} \sum_{t=1}^{m} \mathbf{1}[\,r_t > b_t\,]; \quad "
            r"\mathrm{BA}^{\uparrow} = \frac{\#\{t : r_t > b_t,\ b_t > 0\}}{\#\{t : b_t > 0\}},"
            r" \ \mathrm{BA}^{\downarrow} = \frac{\#\{t : r_t > b_t,\ b_t < 0\}}{\#\{t : b_t < 0\}}"
        ),
        inputs="Fund and benchmark returns on aligned periods.",
        retail="How often the fund beat its benchmark: 0.6 means in 6 periods out of 10. It says "
        "nothing about by how much it won or lost.",
        institutional="Frequency of positive active returns (ties count as not beating). Details "
        "give the up- and down-market batting averages (PerformanceAnalytics UpDownRatios "
        "'Percent'). A high batting average with a negative active return indicates small "
        "frequent wins and large occasional losses.",
        assumptions=(
            "A period counts only if the fund's return strictly exceeds the benchmark's.",
        ),
        misleading_when=(
            *_BENCH_CAVEATS,
            "The size of wins and losses differs greatly (see active return).",
        ),
        minimum_data="At least 2 aligned observations; low confidence below 3 years of overlap.",
        reference_implementations=(
            lib(
                PA,
                "UpDownRatios(method='Percent', side='Up' / 'Down')",
                note="Agrees for the up- and down-market components in the details.",
            ),
        ),
        references=(MORNINGSTAR_BATTING, BACON),
        convention="Strict outperformance; all aligned periods in the denominator (decision 0027).",
    ),
)
def batting_average(ctx: MetricContext) -> Computed:
    b = ctx.bench
    beat = b.fund > b.bench
    up, down = b.bench > 0.0, b.bench < 0.0
    n_up, n_down = int(up.sum()), int(down.sum())
    return Computed(
        float(np.mean(beat)),
        details={
            "periods_beating": int(beat.sum()),
            "ties": int(np.sum(b.fund == b.bench)),
            "up_market_batting_average": float(np.mean(beat[up])) if n_up else None,
            "down_market_batting_average": float(np.mean(beat[down])) if n_down else None,
            "up_periods": n_up,
            "down_periods": n_down,
        },
    )


@metric(
    id="residual_volatility",
    name="Residual (specific) volatility (annualized)",
    category="benchmark",
    unit="decimal_return",
    direction="context_dependent",
    nature="model_dependent",
    min_data_policy="benchmark_regression",
    requires_benchmark=True,
    annualized=True,
    volatility_based=True,
    assumptions=("benchmark", "regression", "annualization"),
    docs=MetricDocs(
        measures="Volatility of the part of fund returns not explained by the benchmark "
        "(regression residuals), annualized.",
        formula="sqrt( sum(e_t^2) / (m - 2) ) * sqrt(P), e_t the OLS residuals",
        formula_latex=(
            r"\hat\sigma_\varepsilon \sqrt{P}, \quad \hat\sigma_\varepsilon = \sqrt{\frac{1}{m-2}"
            r" \sum_{t=1}^{m} \hat\varepsilon_t^2}, \quad \hat\varepsilon_t = r_t - \hat\alpha -"
            r" \hat\beta b_t"
        ),
        undefined_when=("Benchmark returns are constant over the aligned periods.",),
        inputs="Fund and benchmark returns on aligned periods with a regular frequency.",
        retail="How much the fund moved for reasons unrelated to its benchmark. Near zero means "
        "the fund behaves like the benchmark (scaled by beta).",
        institutional="Specific (idiosyncratic, non-systematic) risk: the regression standard "
        "error of the single-index model, annualized by sqrt(P). Details give the systematic "
        "risk |beta| x benchmark volatility. Unlike tracking error it is measured after scaling "
        "by beta.",
        assumptions=(
            "Linear single-index model with the supplied benchmark.",
            "Square-root-of-time scaling.",
        ),
        misleading_when=(
            *_BENCH_CAVEATS,
            "Returns are smoothed: lagged benchmark exposure appears as residual risk.",
        ),
        minimum_data="At least 3 aligned observations; low confidence below 3 years of overlap.",
        reference_implementations=(
            lib(STATSMODELS, "OLS.mse_resid"),
            lib(
                PA,
                "SpecificRisk",
                agrees=False,
                note="PerformanceAnalytics divides the residual sum of squares by m instead of "
                "m - 2.",
            ),
        ),
        references=(TREYNOR_BLACK_1973, BACON),
        convention="Regression standard error (m - 2 degrees of freedom) x sqrt(P) "
        "(decision 0027).",
    ),
)
def residual_volatility(ctx: MetricContext) -> Computed:
    b = ctx.bench
    ols = b.ols
    if ols.residual_std is None:  # pragma: no cover - n >= 3 guarantees degrees of freedom
        raise UndefinedMetric("The residual standard deviation is not computable.")
    systematic = abs(ols.beta) * float(np.std(b.bench, ddof=1)) * math.sqrt(ctx.ppy)
    return Computed(
        ols.residual_std * math.sqrt(ctx.ppy),
        details={"systematic_volatility": systematic, "beta": ols.beta},
    )


@metric(
    id="appraisal_ratio",
    name="Appraisal ratio",
    category="benchmark",
    unit="ratio",
    direction="higher_is_better",
    nature="model_dependent",
    min_data_policy="benchmark_regression",
    requires_benchmark=True,
    annualized=True,
    volatility_based=True,
    assumptions=("benchmark", "regression", "risk_free", "annualization"),
    docs=MetricDocs(
        measures="Alpha per unit of residual (specific) risk, annualized.",
        formula="(P * a) / (sigma_e * sqrt(P)) = a / sigma_e * sqrt(P)",
        formula_latex=(
            r"\mathrm{AppR} = \frac{P \, \hat\alpha}{\hat\sigma_\varepsilon \sqrt{P}} = "
            r"\frac{\hat\alpha}{\hat\sigma_\varepsilon} \sqrt{P}"
        ),
        undefined_when=(
            "Benchmark returns are constant over the aligned periods.",
            "Residual volatility is zero to floating-point precision (below sqrt(machine "
            "epsilon) x fund volatility, i.e. 1 - R-squared below machine epsilon): the "
            "benchmark explains the fund exactly.",
        ),
        inputs="Fund and benchmark returns on aligned periods with a regular frequency.",
        retail="How much benchmark-independent return the fund earned for each unit of "
        "benchmark-independent risk it took.",
        institutional="Treynor & Black (1973) appraisal ratio: annualized OLS alpha over "
        "annualized residual volatility (the Information ratio of the beta-adjusted active "
        "return). It is approximately the alpha t-statistic divided by the square root of the "
        "overlap in years (exactly so when the benchmark's mean return is zero); details give "
        "that t-statistic and its p-value.",
        assumptions=(
            "Single-index (CAPM-style) model with the supplied benchmark.",
            "Risk-free rate 0%.",
        ),
        misleading_when=(
            *_BENCH_CAVEATS,
            "Omitted risk factors masquerade as alpha.",
            "Returns are smoothed or the history is short.",
        ),
        minimum_data="At least 3 aligned observations; low confidence below 3 years of overlap.",
        reference_implementations=(
            lib(
                PA,
                "AppraisalRatio(method='appraisal')",
                agrees=False,
                note="PerformanceAnalytics uses Jensen's alpha from geometric annualized returns "
                "and the m-denominator SpecificRisk.",
            ),
        ),
        references=(TREYNOR_BLACK_1973, GRINOLD_KAHN_2000, BACON),
        convention="Arithmetic annualized OLS alpha / residual volatility, rf = 0 (decision 0027).",
    ),
)
def appraisal_ratio(ctx: MetricContext) -> Computed:
    b = ctx.bench
    ols = b.ols
    # Residuals below sqrt(machine epsilon) x fund volatility mean 1 - R^2 < epsilon: the
    # fit is exact to floating-point precision and alpha / residual risk is rounding noise.
    resolution = math.sqrt(float(np.finfo(np.float64).eps)) * float(np.std(b.fund, ddof=1))
    if ols.residual_std is None or ols.residual_std <= resolution:
        raise UndefinedMetric(
            "Residual volatility is zero to floating-point precision (the benchmark explains "
            "the fund exactly); the appraisal ratio is undefined."
        )
    return Computed(
        ols.alpha / ols.residual_std * math.sqrt(ctx.ppy),
        details={"alpha_t_statistic": ols.alpha_t, "alpha_p_value": ols.alpha_pvalue},
    )


@metric(
    id="m_squared",
    name="M-squared (Modigliani risk-adjusted return)",
    category="benchmark",
    unit="decimal_return",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="benchmark_simple",
    requires_benchmark=True,
    annualized=True,
    volatility_based=True,
    assumptions=("benchmark", "risk_free", "sample_std", "annualization"),
    docs=MetricDocs(
        measures="The fund's annualized return had it been leveraged or de-leveraged to the "
        "benchmark's volatility.",
        formula="P * (mean(r_fund,t) / std(r_fund,t)) * std(r_bench,t), aligned periods, rf = 0",
        formula_latex=(
            r"M^2 = P \, \frac{\bar r^{(m)} - r_f}{s_r^{(m)}} \, s_b + P\, r_f, \quad r_f = 0; "
            r"\quad M^2 - P \bar b \ \text{(details)}"
        ),
        undefined_when=(
            "Fund returns are constant over the aligned periods (zero volatility).",
            "Benchmark returns are constant over the aligned periods (zero volatility).",
        ),
        inputs="Fund and benchmark returns on aligned periods with a regular frequency.",
        retail="Puts the fund and the benchmark on the same risk footing: the return the fund "
        "would have delivered at the benchmark's volatility. Compare it with the benchmark's own "
        "return (details).",
        institutional="Modigliani & Modigliani (1997) M-squared with rf = 0 on the aligned "
        "overlap: the aligned-sample Sharpe ratio times the benchmark's annualized volatility. "
        "It ranks funds exactly as the Sharpe ratio does, but in return units. Details give "
        "the benchmark's annualized mean and the difference (M-squared excess).",
        assumptions=(
            "Risk-free rate 0%: leverage is assumed costless.",
            "Volatility is the relevant risk measure.",
        ),
        misleading_when=(
            *_BENCH_CAVEATS,
            "Returns are smoothed or strongly non-normal (inherits the Sharpe ratio's caveats).",
            "Borrowing costs are material (rf = 0 understates the cost of leverage).",
        ),
        minimum_data="At least 2 aligned observations; low confidence below 3 years of overlap.",
        reference_implementations=(
            lib(
                PA,
                "Modigliani * P",
                note="PerformanceAnalytics reports the per-period value.",
            ),
        ),
        references=(MODIGLIANI_1997, BACON),
        convention="Arithmetic annualization, sample standard deviations on aligned periods, "
        "rf = 0 (decision 0027).",
    ),
)
def m_squared(ctx: MetricContext) -> Computed:
    b = ctx.bench
    # Constancy is tested on the values (a computed std of identical values can be rounding
    # noise rather than exactly zero).
    if float(np.ptp(b.fund)) == 0.0:
        raise UndefinedMetric(
            "Fund returns are constant over the aligned periods (zero volatility); M-squared "
            "is undefined."
        )
    if float(np.ptp(b.bench)) == 0.0:
        raise UndefinedMetric(
            "Benchmark returns are constant over the aligned periods (zero volatility); "
            "M-squared is undefined."
        )
    s_fund = float(np.std(b.fund, ddof=1))
    s_bench = float(np.std(b.bench, ddof=1))
    value = float(np.mean(b.fund)) / s_fund * s_bench * ctx.ppy
    bench_mean = float(np.mean(b.bench)) * ctx.ppy
    return Computed(
        value,
        details={
            "benchmark_annualized_mean": bench_mean,
            "m_squared_excess": value - bench_mean,
            "fund_sharpe_ratio_aligned": float(np.mean(b.fund)) / s_fund * math.sqrt(ctx.ppy),
        },
    )


def _regime_beta(ctx: MetricContext, up: bool) -> Computed:
    b = ctx.bench
    ols = b.bull_ols if up else b.bear_ols
    side = "up" if up else "down"
    notes: tuple[str, ...] = ()
    if ols.n < 12:
        notes = (f"Estimated from only {ols.n} benchmark {side} periods.",)
    return Computed(
        ols.beta,
        details={
            f"{side}_periods": ols.n,
            "standard_error": ols.beta_se,
            "t_statistic": ols.beta_t,
            "intercept_per_period": ols.alpha,
        },
        notes=notes,
    )


_REGIME_CAVEATS = (
    *_BENCH_CAVEATS,
    "Few up or down periods: the subset regression is very noisy.",
    "Conditioning on the sign of the benchmark truncates the regressor, which biases subset "
    "betas towards zero when the true relationship is noisy.",
)


@metric(
    id="bull_beta",
    name="Bull-market beta",
    category="benchmark",
    unit="beta",
    direction="context_dependent",
    nature="estimated",
    min_data_policy="benchmark_regression",
    requires_benchmark=True,
    assumptions=("benchmark", "regression"),
    docs=MetricDocs(
        measures="Sensitivity of fund returns to benchmark returns in periods when the benchmark "
        "rose.",
        formula="slope of OLS r_fund,t = a + b * r_bench,t + e_t over {t : r_bench,t > 0}",
        formula_latex=(
            r"\hat\beta^{+} = \text{OLS slope of } r_t = \alpha^{+} + \beta^{+} b_t + "
            r"\varepsilon_t \text{ over } \{t : b_t > 0\}"
        ),
        undefined_when=(
            "Fewer than 3 benchmark up periods in the overlap.",
            "Benchmark returns are constant over the up periods.",
        ),
        inputs="Fund and benchmark returns on aligned periods.",
        retail="How strongly the fund followed the benchmark when the benchmark went up.",
        institutional="Single-index beta estimated on the benchmark-up subsample (Fabozzi & "
        "Francis 1977), rf = 0; compare with bear-market beta for asymmetric participation. "
        "Details give the standard error and number of periods.",
        assumptions=("Linear relationship within each market regime.", "Risk-free rate 0%."),
        misleading_when=_REGIME_CAVEATS,
        minimum_data="At least 3 benchmark up periods; low confidence below 3 years of overlap.",
        reference_implementations=(lib(PA, "CAPM.beta.bull"),),
        references=(FABOZZI_FRANCIS_1977, BACON),
        convention="OLS with intercept on periods with benchmark return > 0 (decision 0027).",
    ),
)
def bull_beta(ctx: MetricContext) -> Computed:
    return _regime_beta(ctx, up=True)


@metric(
    id="bear_beta",
    name="Bear-market beta",
    category="benchmark",
    unit="beta",
    direction="context_dependent",
    nature="estimated",
    min_data_policy="benchmark_regression",
    requires_benchmark=True,
    assumptions=("benchmark", "regression"),
    docs=MetricDocs(
        measures="Sensitivity of fund returns to benchmark returns in periods when the benchmark "
        "fell.",
        formula="slope of OLS r_fund,t = a + b * r_bench,t + e_t over {t : r_bench,t < 0}",
        formula_latex=(
            r"\hat\beta^{-} = \text{OLS slope of } r_t = \alpha^{-} + \beta^{-} b_t + "
            r"\varepsilon_t \text{ over } \{t : b_t < 0\}"
        ),
        undefined_when=(
            "Fewer than 3 benchmark down periods in the overlap.",
            "Benchmark returns are constant over the down periods.",
        ),
        inputs="Fund and benchmark returns on aligned periods.",
        retail="How strongly the fund followed the benchmark when the benchmark went down; "
        "lower means better protection in falling markets.",
        institutional="Single-index beta estimated on the benchmark-down subsample (Fabozzi & "
        "Francis 1977), rf = 0. Details give the standard error and number of periods.",
        assumptions=("Linear relationship within each market regime.", "Risk-free rate 0%."),
        misleading_when=_REGIME_CAVEATS,
        minimum_data="At least 3 benchmark down periods; low confidence below 3 years of overlap.",
        reference_implementations=(lib(PA, "CAPM.beta.bear"),),
        references=(FABOZZI_FRANCIS_1977, BACON),
        convention="OLS with intercept on periods with benchmark return < 0 (decision 0027).",
    ),
)
def bear_beta(ctx: MetricContext) -> Computed:
    return _regime_beta(ctx, up=False)


@metric(
    id="timing_ratio",
    name="Timing ratio (bull beta / bear beta)",
    category="benchmark",
    unit="ratio",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="benchmark_regression",
    requires_benchmark=True,
    assumptions=("benchmark", "regression"),
    docs=MetricDocs(
        measures="Bull-market beta divided by bear-market beta: asymmetry of market participation.",
        formula="bull_beta / bear_beta, bear_beta > 0",
        formula_latex=r"\mathrm{TR}_{\text{timing}} = \frac{\hat\beta^{+}}{\hat\beta^{-}}, "
        r"\quad \hat\beta^{-} > 0",
        undefined_when=(
            "Bull-market or bear-market beta is undefined (fewer than 3 up or down periods, or "
            "a constant benchmark within a regime).",
            "Bear-market beta is zero or negative; the ratio's sign would be meaningless. Both "
            "betas are still reported.",
        ),
        inputs="Fund and benchmark returns on aligned periods.",
        retail="Above 1: the fund was more sensitive to rising than to falling markets.",
        institutional="Ratio of subsample betas (PerformanceAnalytics TimingRatio). Both betas "
        "are noisy, so the ratio is very noisy; it is descriptive, not evidence of timing "
        "skill. Formal timing tests (Treynor-Mazuy, Henriksson-Merton) are not part of "
        "methodology 0.1.0.",
        assumptions=("Linear relationship within each market regime.", "Risk-free rate 0%."),
        misleading_when=(
            *_REGIME_CAVEATS,
            "Option-like or dynamically hedged strategies: asymmetry need not reflect skill.",
        ),
        minimum_data="At least 3 benchmark up and 3 down periods; low confidence below 3 years "
        "of overlap.",
        reference_implementations=(lib(PA, "TimingRatio"),),
        references=(BACON, FABOZZI_FRANCIS_1977),
        convention="Ratio of OLS subsample betas; bear beta must be positive (decision 0027).",
    ),
)
def timing_ratio(ctx: MetricContext) -> Computed:
    bull = _regime_beta(ctx, up=True)
    bear = _regime_beta(ctx, up=False)
    if bear.value <= 0.0:
        raise UndefinedMetric(
            f"Bear-market beta is {bear.value:.2f}; a timing ratio with a non-positive "
            "denominator is not meaningful. See bull- and bear-market beta."
        )
    return Computed(
        bull.value / bear.value,
        details={"bull_beta": bull.value, "bear_beta": bear.value},
        notes=bull.notes + bear.notes,
    )
