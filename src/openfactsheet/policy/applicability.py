"""Applicability engine (CLAUDE.md section 14).

Decides, *before* calculation, whether a metric can be computed at all. It
never hides a metric for being unfavorable: the only grounds are missing
inputs (benchmark, annualization factor), a mathematically invalid wealth path,
or fewer observations than the metric's mathematical minimum.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from openfactsheet.models.metric import MetricDefinition, MetricStatus
from openfactsheet.policy.thresholds import get_policy

if TYPE_CHECKING:
    from openfactsheet.metrics.context import MetricContext

NO_BENCHMARK_REASON = (
    "No benchmark was supplied. Benchmark-relative metrics require explicitly supplied "
    "benchmark returns; OpenFactsheet never assumes a default benchmark."
)


@dataclass(frozen=True)
class Inapplicable:
    status: MetricStatus
    reason: str


NO_FACTORS_REASON = (
    "No factor returns were supplied. Factor-model metrics require explicitly supplied factor "
    "returns (ofs.analyze(returns, factors=...)); OpenFactsheet never downloads factor data."
)


def observations_for(definition: MetricDefinition, ctx: MetricContext) -> int:
    if definition.requires_benchmark:
        return ctx.benchmark.n if ctx.benchmark is not None else 0
    if definition.requires_factors:
        return ctx.factors.n if ctx.factors is not None else 0
    return ctx.n


def precheck(definition: MetricDefinition, ctx: MetricContext) -> Inapplicable | None:
    if definition.requires_benchmark and ctx.benchmark is None:
        return Inapplicable("not_applicable", NO_BENCHMARK_REASON)
    if definition.requires_factors and ctx.factors is None:
        return Inapplicable("not_applicable", NO_FACTORS_REASON)
    if definition.annualized and ctx.returns.periods_per_year is None:
        freq = ctx.returns.frequency.value
        return Inapplicable(
            "not_applicable",
            f"Annualization requires a regular observation frequency; the frequency of this "
            f"series is {freq}. Supply dated returns or declare the frequency.",
        )
    if definition.uses_wealth_path and ctx.diagnostics.impossible_return_count:
        return Inapplicable(
            "not_applicable",
            "The series contains returns below -100%, so the compounded wealth path (and every "
            "metric built on it) is not meaningful.",
        )
    n = observations_for(definition, ctx)
    policy = get_policy(definition.min_data_policy)
    minimum = policy.math_min_obs
    if definition.requires_factors and ctx.factors is not None:
        # k + 1 coefficients and at least one residual degree of freedom.
        minimum = max(minimum, ctx.factors.k + 2)
    if n < minimum:
        aligned = definition.requires_benchmark or definition.requires_factors
        basis = "aligned observations" if aligned else "observations"
        return Inapplicable(
            "insufficient_data",
            f"Requires at least {minimum} {basis}; {n} available.",
        )
    return None
