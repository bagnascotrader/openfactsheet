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
    GOODWIN_1998,
    GRINOLD_KAHN_2000,
    JENSEN_1968,
    MORNINGSTAR_CAPTURE,
    NUMPY,
    PA,
    QS,
    STATSMODELS,
    TREYNOR_1965,
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
    return ctx.bench.ols.r_squared


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
