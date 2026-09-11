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


def observations_for(definition: MetricDefinition, ctx: MetricContext) -> int:
    if definition.requires_benchmark:
        return ctx.benchmark.n if ctx.benchmark is not None else 0
    return ctx.n


def precheck(definition: MetricDefinition, ctx: MetricContext) -> Inapplicable | None:
    if definition.requires_benchmark and ctx.benchmark is None:
        return Inapplicable("not_applicable", NO_BENCHMARK_REASON)
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
    if n < policy.math_min_obs:
        basis = "aligned observations" if definition.requires_benchmark else "observations"
        return Inapplicable(
            "insufficient_data",
            f"Requires at least {policy.math_min_obs} {basis}; {n} available.",
        )
    return None
