"""Return metrics (CLAUDE.md section 12.1)."""

from __future__ import annotations

import numpy as np

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import (
    BACON,
    EMP,
    GIPS,
    NUMPY,
    PA,
    QS,
    SCHWAGER_2012,
    lib,
)
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import Computed, MetricDocs


def _date_of(ctx: MetricContext, position: int) -> str | None:
    dates = ctx.returns.dates
    return dates[position].strftime("%Y-%m-%d") if dates is not None else None


@metric(
    id="cumulative_return",
    name="Cumulative return",
    category="returns",
    unit="decimal_return",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="observed_point",
    uses_wealth_path=True,
    docs=MetricDocs(
        measures="Total compounded return over the full supplied history.",
        formula="prod_{t=1..n}(1 + r_t) - 1",
        formula_latex=r"\mathrm{CR} = W_n - 1 = \prod_{t=1}^{n} (1 + r_t) - 1",
        inputs="Periodic simple returns.",
        retail="How much 1 unit invested at the start would have gained or lost by the end, "
        "with all returns reinvested.",
        institutional="Path-independent summary of realized compounded performance over the "
        "full track record; not comparable across different history lengths.",
        assumptions=(
            "Returns are reinvested each period.",
            "Returns are net of whatever fees the supplied series reflects.",
        ),
        misleading_when=(
            "Histories of different lengths are compared.",
            "The track record starts at a favorable date (OpenFactsheet always uses the full "
            "supplied history, but the supplier chose the inception date).",
        ),
        minimum_data="Any non-empty history.",
        reference_implementations=(
            lib(PA, "Return.cumulative(geometric=TRUE)"),
            lib(EMP, "cum_returns_final"),
            lib(QS, "stats.comp"),
        ),
        references=(BACON,),
        convention="Geometric compounding of simple returns; no annualization.",
    ),
)
def cumulative_return(ctx: MetricContext) -> float:
    return ctx.cache.cumulative_return


@metric(
    id="cagr",
    name="Annualized return (CAGR)",
    category="returns",
    unit="decimal_return",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="location",
    annualized=True,
    uses_wealth_path=True,
    assumptions=("annualization",),
    docs=MetricDocs(
        measures="Constant yearly growth rate that would produce the observed cumulative return.",
        formula="(prod(1 + r_t))^(P / n) - 1, where P = periods per year and n = observations",
        formula_latex=(
            r"\mathrm{CAGR} = \begin{cases} W_n^{P/n} - 1 & W_n > 0 \\"
            r" -1 & W_n \le 0 \end{cases}"
        ),
        inputs="Periodic simple returns with a regular frequency.",
        retail="The average yearly growth rate, taking compounding and losses into account.",
        institutional="Geometric mean return annualized with the canonical periods-per-year "
        "factor; the standard GIPS-style annualized return. Always below the annualized "
        "arithmetic mean when returns vary.",
        assumptions=("Observation frequency is correctly established.",),
        misleading_when=(
            "The history is shorter than one year: annualizing extrapolates a partial year "
            "(GIPS prohibits presenting annualized returns for periods under one year).",
            "The history contains missing periods.",
        ),
        minimum_data="One observation mathematically; low confidence below 3 years.",
        reference_implementations=(
            lib(PA, "Return.annualized(geometric=TRUE)"),
            lib(EMP, "annual_return"),
            lib(
                QS,
                "stats.cagr(periods=12)",
                note="Agrees when periods=12 is passed for monthly data; the default "
                "(periods=252) treats every observation as a trading day.",
            ),
        ),
        references=(BACON, GIPS),
        convention="Observation count (not calendar span) with the canonical periods-per-year "
        "factor (decision 0004).",
    ),
)
def cagr(ctx: MetricContext) -> float:
    return ctx.cagr


@metric(
    id="arithmetic_mean",
    name="Mean return per period",
    category="returns",
    unit="decimal_return",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="location",
    docs=MetricDocs(
        measures="Average single-period return.",
        formula="(1/n) * sum(r_t)",
        formula_latex=r"\bar r = \frac{1}{n} \sum_{t=1}^{n} r_t",
        inputs="Periodic simple returns.",
        retail="The typical return in one period (e.g. one month), ignoring compounding.",
        institutional="Sample mean; the numerator of Sharpe-type ratios. An estimate of the "
        "expected return with standard error roughly sigma / sqrt(n).",
        assumptions=("Returns are identically distributed over the history.",),
        misleading_when=(
            "Returns are volatile: the arithmetic mean overstates compounded growth.",
            "Few observations are available: sampling error dominates.",
        ),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(lib(NUMPY, "mean"), lib(PA, "mean.arithmetic")),
        references=(BACON,),
        convention="Plain sample mean of per-period returns.",
    ),
)
def arithmetic_mean(ctx: MetricContext) -> float:
    return ctx.cache.mean


@metric(
    id="geometric_mean_return",
    name="Geometric mean return per period",
    category="returns",
    unit="decimal_return",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="location",
    uses_wealth_path=True,
    docs=MetricDocs(
        measures="Constant per-period growth rate that reproduces the cumulative return.",
        formula="(prod(1 + r_t))^(1/n) - 1",
        formula_latex=(
            r"\bar r_g = \begin{cases} W_n^{1/n} - 1 & W_n > 0 \\ -1 & W_n \le 0 \end{cases}"
        ),
        inputs="Periodic simple returns.",
        retail="The average compounded return per period (e.g. per month).",
        institutional="Per-period geometric mean; CAGR is its annualized form. Lies below the "
        "arithmetic mean by roughly half the variance (volatility drag). Needs no frequency.",
        assumptions=("Returns are reinvested each period.",),
        misleading_when=("Histories of different lengths or frequencies are compared.",),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(lib(PA, "mean.geometric"),),
        references=(BACON,),
        convention="Geometric compounding of simple returns; -100% after a total loss.",
    ),
)
def geometric_mean_return(ctx: MetricContext) -> float:
    wealth_end = float(ctx.cache.wealth[-1])
    if wealth_end <= 0.0:
        return -1.0
    return float(wealth_end ** (1.0 / ctx.n) - 1.0)


@metric(
    id="annualized_arithmetic_mean",
    name="Annualized mean return (arithmetic)",
    category="returns",
    unit="decimal_return",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="location",
    annualized=True,
    assumptions=("annualization",),
    docs=MetricDocs(
        measures="Average per-period return scaled to a year without compounding.",
        formula="P * mean(r_t)",
        formula_latex=r"\bar r_{\text{ann}} = P \, \bar r",
        inputs="Periodic simple returns with a regular frequency.",
        retail="The average return per year if yearly results were simply added up; usually "
        "higher than the compounded annual return.",
        institutional="Linear annualization of the sample mean; the return component of the "
        "canonical annualized Sharpe ratio. Differs from CAGR by roughly half the variance.",
        assumptions=("Linear time scaling of the mean.",),
        misleading_when=("Used as a proxy for realized compounded growth.",),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(lib(PA, "Return.annualized(geometric=FALSE)"),),
        references=(BACON,),
        convention="mean x periods per year (decision 0004).",
    ),
)
def annualized_arithmetic_mean(ctx: MetricContext) -> float:
    return ctx.cache.mean * ctx.ppy


@metric(
    id="median_return",
    name="Median return per period",
    category="returns",
    unit="decimal_return",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="location",
    docs=MetricDocs(
        measures="Middle value of the per-period returns.",
        formula="median(r_t)",
        formula_latex=(
            r"\operatorname{med}(r) = \begin{cases} r_{((n+1)/2)} & n \text{ odd} \\"
            r" \tfrac{1}{2}\left(r_{(n/2)} + r_{(n/2+1)}\right) & n \text{ even} \end{cases}"
        ),
        inputs="Periodic simple returns.",
        retail="Half of the periods did better than this and half did worse.",
        institutional="Robust location estimate, insensitive to a few extreme periods. A median "
        "well above the mean indicates occasional large losses (negative skew).",
        assumptions=(),
        misleading_when=("Many periods have identical or zero returns.",),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(lib(NUMPY, "median"),),
        references=(BACON,),
        convention="Sample median (average of the two middle values when n is even).",
    ),
)
def median_return(ctx: MetricContext) -> float:
    return float(np.median(ctx.r))


@metric(
    id="best_period",
    name="Best period",
    category="returns",
    unit="decimal_return",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="observed_point",
    docs=MetricDocs(
        measures="Highest single-period return in the history.",
        formula="max(r_t)",
        formula_latex=r"\max_{1 \le t \le n} r_t = r_{(n)}",
        inputs="Periodic simple returns.",
        retail="The best single period (e.g. month) the investment had.",
        institutional="Observed upper extreme; context for the dispersion and tail statistics.",
        assumptions=(),
        misleading_when=("Histories of different lengths are compared.",),
        minimum_data="Any non-empty history.",
        reference_implementations=(lib(QS, "stats.best"), lib(NUMPY, "max")),
        references=(BACON,),
        convention="Per observation period of the supplied data (not calendar aggregated).",
    ),
)
def best_period(ctx: MetricContext) -> Computed:
    pos = int(np.argmax(ctx.r))
    return Computed(float(ctx.r[pos]), details={"date": _date_of(ctx, pos), "position": pos + 1})


@metric(
    id="worst_period",
    name="Worst period",
    category="returns",
    unit="decimal_return",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="observed_point",
    docs=MetricDocs(
        measures="Lowest single-period return in the history.",
        formula="min(r_t)",
        formula_latex=r"\min_{1 \le t \le n} r_t = r_{(1)}",
        inputs="Periodic simple returns.",
        retail="The worst single period (e.g. month) the investment had.",
        institutional="Observed lower extreme; a model-free loss statistic that is always shown.",
        assumptions=(),
        misleading_when=(
            "Histories of different lengths are compared; longer histories tend to contain "
            "worse periods.",
        ),
        minimum_data="Any non-empty history.",
        reference_implementations=(lib(QS, "stats.worst"), lib(NUMPY, "min")),
        references=(BACON,),
        convention="Per observation period; signed (negative = loss).",
    ),
)
def worst_period(ctx: MetricContext) -> Computed:
    pos = int(np.argmin(ctx.r))
    return Computed(float(ctx.r[pos]), details={"date": _date_of(ctx, pos), "position": pos + 1})


@metric(
    id="gain_to_pain_ratio",
    name="Gain-to-pain ratio",
    category="returns",
    unit="ratio",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="ratio_standard",
    docs=MetricDocs(
        measures="Sum of all returns relative to the sum of losing-period returns.",
        formula="sum(r_t) / |sum(r_t for r_t < 0)|",
        formula_latex=(
            r"\mathrm{GPR} = \frac{\sum_{t=1}^{n} r_t}{\left| \sum_{t:\, r_t < 0} r_t \right|}"
        ),
        undefined_when=("No period has a negative return (zero denominator).",),
        inputs="Periodic simple returns.",
        retail="How much net return was earned for each unit of losses suffered along the way.",
        institutional="Schwager's gain-to-pain ratio on per-period returns; a simple, "
        "distribution-free complement to volatility-based ratios.",
        assumptions=("Per-period returns are summed (not compounded).",),
        misleading_when=(
            "Very few losing periods exist: the denominator is tiny and the ratio unstable.",
            "Compared across data frequencies (monthly vs daily values differ).",
        ),
        minimum_data="At least 2 observations and at least one losing period; low confidence "
        "below 3 years.",
        reference_implementations=(
            lib(
                QS,
                "stats.gain_to_pain_ratio",
                note="Agrees on the monthly test fixtures.",
            ),
        ),
        references=(SCHWAGER_2012,),
        convention="Computed on the supplied observation frequency; undefined (not "
        "applicable) when no period is negative.",
    ),
)
def gain_to_pain_ratio(ctx: MetricContext) -> float:
    losses = ctx.r[ctx.r < 0.0]
    if losses.size == 0:
        raise UndefinedMetric("No losing periods: the gain-to-pain denominator is zero.")
    return float(np.sum(ctx.r) / abs(np.sum(losses)))


@metric(
    id="payoff_ratio",
    name="Payoff ratio (average win / average loss)",
    category="returns",
    unit="ratio",
    direction="higher_is_better",
    nature="derived",
    min_data_policy="ratio_standard",
    docs=MetricDocs(
        measures="Size of the average winning period relative to the average losing period.",
        formula="mean(r_t | r_t > 0) / |mean(r_t | r_t < 0)|",
        formula_latex=(
            r"\mathrm{Payoff} = \frac{\frac{1}{|G|} \sum_{t \in G} r_t}"
            r"{\left| \frac{1}{|L|} \sum_{t \in L} r_t \right|}, \quad "
            r"G = \{t : r_t > 0\}, \ L = \{t : r_t < 0\}"
        ),
        undefined_when=("No positive period or no negative period exists.",),
        inputs="Periodic simple returns.",
        retail="How big the typical gain is compared with the typical loss. Read it together "
        "with the share of positive periods: a low payoff with a high hit rate can still be "
        "profitable, and vice versa.",
        institutional="Win/loss (payoff) ratio on the supplied frequency; zero-return periods "
        "are excluded from both averages. The expectation per period equals hit rate x average "
        "win - loss rate x average loss.",
        assumptions=("Zero returns count as neither wins nor losses.",),
        misleading_when=(
            "Very few winning or losing periods.",
            "Returns are smoothed (many small gains, rare large losses).",
        ),
        minimum_data="At least 2 observations with one gain and one loss; low confidence below "
        "3 years.",
        reference_implementations=(lib(QS, "stats.payoff_ratio"),),
        references=(BACON,),
        convention="Arithmetic averages of strictly positive and strictly negative periods.",
    ),
)
def payoff_ratio(ctx: MetricContext) -> Computed:
    gains = ctx.r[ctx.r > 0.0]
    losses = ctx.r[ctx.r < 0.0]
    if gains.size == 0 or losses.size == 0:
        raise UndefinedMetric("The payoff ratio needs at least one gain and one loss.")
    return Computed(
        float(np.mean(gains)) / abs(float(np.mean(losses))),
        details={"average_gain": float(np.mean(gains)), "average_loss": float(np.mean(losses))},
    )
