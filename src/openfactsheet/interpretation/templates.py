"""Context-specific interpretation notes.

Rules here add caution where the data warrant it. They never grade an
investment ("excellent", "poor") and never give advice.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from openfactsheet.models.metric import MetricCollection, MetricResult

if TYPE_CHECKING:
    from openfactsheet.metrics.context import MetricContext

ContextRule = Callable[[MetricResult, MetricCollection, "MetricContext"], "str | None"]

_VOL_BASED = frozenset(
    {"sharpe_ratio", "sortino_ratio", "information_ratio", "annualized_volatility", "volatility"}
)


def _smoothing(result: MetricResult, _: MetricCollection, ctx: MetricContext) -> str | None:
    if result.id not in _VOL_BASED or result.value is None:
        return None
    risk = ctx.diagnostics.smoothing_risk
    if risk not in ("moderate", "high"):
        return None
    rho = ctx.diagnostics.autocorrelation[0]
    return (
        f"Lag-1 autocorrelation is {rho:.2f} ({risk} smoothing risk). Smoothed or stale returns "
        "understate volatility, so treat this figure as an optimistic bound rather than as "
        "evidence of skill; the drawdown and tail sections are less affected."
    )


def _hidden_tail(result: MetricResult, metrics: MetricCollection, _: MetricContext) -> str | None:
    if result.id != "sharpe_ratio" or result.value is None:
        return None
    skew = metrics.get("skewness")
    kurt = metrics.get("excess_kurtosis")
    skew_v = skew.value if skew is not None else None
    kurt_v = kurt.value if kurt is not None else None
    if (skew_v is not None and skew_v <= -1.0) or (kurt_v is not None and kurt_v >= 3.0):
        return (
            "The return distribution is negatively skewed and/or fat-tailed. Volatility-based "
            "ratios such as Sharpe do not reflect such tail risk; compare with maximum drawdown "
            "and Expected Shortfall."
        )
    return None


def _alpha_significance(result: MetricResult, _: MetricCollection, __: MetricContext) -> str | None:
    if result.id != "alpha" or result.value is None:
        return None
    p = result.details.get("p_value")
    t = result.details.get("t_statistic")
    if p is None or t is None:
        return None
    if p >= 0.05:
        return (
            f"Alpha is not statistically distinguishable from zero at the 5% level "
            f"(t = {t:.2f}, p = {p:.2f}); the point estimate may reflect noise."
        )
    return (
        f"Alpha is statistically different from zero at the 5% level (t = {t:.2f}, p = {p:.3f}) "
        "under the single-index model with the supplied benchmark; omitted factors can still "
        "explain it."
    )


def _short_path(result: MetricResult, _: MetricCollection, ctx: MetricContext) -> str | None:
    if result.category != "drawdown" or result.value is None:
        return None
    years = ctx.returns.years
    if years is not None and years < 3:
        return (
            f"Only {years:.1f} years of history: drawdowns observed so far are likely milder "
            "than those a longer history would reveal."
        )
    return None


def _hit_rate_smoothing(
    result: MetricResult, _: MetricCollection, ctx: MetricContext
) -> str | None:
    if result.id != "positive_period_pct" or result.value is None:
        return None
    if ctx.diagnostics.smoothing_risk == "high" and result.value >= 0.75:
        return (
            "A very high share of positive periods together with strong serial correlation is a "
            "pattern associated with smoothed returns."
        )
    return None


def _annualized_short(result: MetricResult, _: MetricCollection, ctx: MetricContext) -> str | None:
    if result.id not in ("cagr", "annualized_arithmetic_mean") or result.value is None:
        return None
    years = ctx.returns.years
    if years is not None and years < 1:
        return (
            f"The history covers only {years:.1f} years; annualizing extrapolates a partial year. "
            "GIPS prohibits presenting annualized returns for periods shorter than one year."
        )
    return None


def _sharpe_significance(
    result: MetricResult, _: MetricCollection, __: MetricContext
) -> str | None:
    if result.id != "probabilistic_sharpe_ratio" or result.value is None:
        return None
    if result.value >= 0.95:
        return (
            f"PSR = {result.value:.2f}: the Sharpe ratio is statistically above zero at the 95% "
            "level under i.i.d. assumptions (not a guarantee of future performance)."
        )
    return (
        f"PSR = {result.value:.2f}: the Sharpe ratio is not statistically distinguishable from "
        "zero at the 95% level; the track record cannot separate skill from luck."
    )


def _track_record_sufficiency(
    result: MetricResult, _: MetricCollection, __: MetricContext
) -> str | None:
    if result.id != "minimum_track_record_length" or result.value is None:
        return None
    needed = result.details.get("additional_periods_needed")
    if result.details.get("sufficient"):
        return "The actual history is at least as long as the minimum track record length."
    return (
        f"The history is {needed} period(s) shorter than the minimum track record length needed "
        "for the observed Sharpe ratio to be significant at 95%."
    )


RULES: tuple[ContextRule, ...] = (
    _smoothing,
    _hidden_tail,
    _alpha_significance,
    _short_path,
    _hit_rate_smoothing,
    _annualized_short,
    _sharpe_significance,
    _track_record_sufficiency,
)
