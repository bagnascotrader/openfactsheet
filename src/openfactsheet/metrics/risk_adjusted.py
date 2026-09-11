"""Risk-adjusted performance ratios (CLAUDE.md section 12.3)."""

from __future__ import annotations

import math

import numpy as np

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import (
    BACON,
    EMP,
    GLM_2004,
    KEATING_SHADWICK_2002,
    LO_2002,
    MARTIN_MCCANN_1989,
    PA,
    QS,
    SHARPE_1966,
    SHARPE_1994,
    SORTINO_PRICE_1994,
    YOUNG_1991,
    lib,
)
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import MetricDocs


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
            lib(QS, "stats.calmar", agrees=False, note="QuantStats CAGR uses calendar years."),
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
