"""Drawdown and underwater metrics (CLAUDE.md section 12.4).

All metrics consume the shared wealth/drawdown engine in
:mod:`openfactsheet.metrics.path` via the context cache.
"""

from __future__ import annotations

import numpy as np

from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import (
    BACON,
    EMP,
    MAGDON_ISMAIL_2004,
    MARTIN_MCCANN_1989,
    PA,
    QS,
    lib,
)
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import Computed, MetricDocs

_PATH_CAVEAT = (
    "Short histories: drawdown statistics grow with the length of the track record and "
    "cannot reveal risks that have not yet materialized."
)


@metric(
    id="max_drawdown",
    name="Maximum drawdown",
    category="drawdown",
    unit="decimal_return",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Largest peak-to-trough decline of compounded wealth.",
        formula="min_t( W_t / max_{s<=t} W_s - 1 ), W_0 = 1, W_t = prod_{i<=t}(1 + r_i)",
        inputs="Periodic simple returns.",
        retail="The worst loss an investor would have suffered buying at a high point and "
        "selling at the following low point.",
        institutional="Path-dependent realized loss; always shown. Expected maximum drawdown "
        "grows with history length and volatility (Magdon-Ismail & Atiya, 2004), so compare "
        "only across similar horizons.",
        assumptions=("Wealth index starts at 1 before the first return.",),
        misleading_when=(
            _PATH_CAVEAT,
            "Returns are smoothed, which reduces measured drawdowns.",
            "Data frequency is low: intra-period declines are invisible.",
        ),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(
            lib(PA, "maxDrawdown", note="PerformanceAnalytics reports a positive magnitude."),
            lib(EMP, "max_drawdown"),
            lib(QS, "stats.max_drawdown"),
        ),
        references=(MAGDON_ISMAIL_2004, BACON),
        convention="Signed (negative = loss); the inception value counts as a peak so a first-"
        "period loss is a drawdown (decision 0007).",
    ),
)
def max_drawdown(ctx: MetricContext) -> Computed:
    episodes = ctx.cache.episodes
    if not episodes:
        return Computed(0.0, details={"episodes": 0})
    worst = min(episodes, key=lambda e: e.depth)
    return Computed(
        worst.depth,
        details={
            "peak_date": worst.peak_date,
            "trough_date": worst.trough_date,
            "recovery_date": worst.recovery_date,
            "recovered": worst.recovered,
            "peak_to_trough_periods": worst.peak_to_trough_periods,
            "duration_periods": worst.duration_periods,
        },
    )


@metric(
    id="average_drawdown",
    name="Average drawdown (per episode)",
    category="drawdown",
    unit="decimal_return",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Mean depth of all distinct drawdown episodes.",
        formula="(1/K) * sum_k depth_k over K peak-to-recovery episodes",
        inputs="Periodic simple returns.",
        retail="How deep the typical decline from a high point has been.",
        institutional="Episode-based average (PerformanceAnalytics AverageDrawdown convention); "
        "less dominated by a single event than maximum drawdown. Compare with the Pain Index, "
        "which averages over time instead of over episodes.",
        assumptions=("Every decline below a prior peak, however small, is an episode.",),
        misleading_when=(_PATH_CAVEAT, "Many tiny episodes dilute the average."),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(
            lib(PA, "AverageDrawdown", note="PerformanceAnalytics reports a positive magnitude."),
        ),
        references=(BACON,),
        convention="Mean of episode depths, signed (negative = loss); 0 when no drawdown occurred.",
    ),
)
def average_drawdown(ctx: MetricContext) -> Computed:
    episodes = ctx.cache.episodes
    if not episodes:
        return Computed(0.0, details={"episodes": 0})
    return Computed(
        float(np.mean([e.depth for e in episodes])), details={"episodes": len(episodes)}
    )


@metric(
    id="current_drawdown",
    name="Current drawdown",
    category="drawdown",
    unit="decimal_return",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="observed_point",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Decline of wealth at the end of the history relative to its highest point.",
        formula="W_n / max_{s<=n} W_s - 1",
        inputs="Periodic simple returns.",
        retail="How far below its previous high the investment stands at the end of the data.",
        institutional="State variable at the reporting date; zero when the series ends at a "
        "high-water mark.",
        assumptions=("Wealth index starts at 1 before the first return.",),
        misleading_when=("The history ends at an arbitrary date.",),
        minimum_data="Any non-empty history.",
        reference_implementations=(lib(QS, "stats.to_drawdown_series (last value)"),),
        references=(BACON,),
        convention="Signed (negative = loss).",
    ),
)
def current_drawdown(ctx: MetricContext) -> float:
    return float(ctx.cache.drawdown[-1])


@metric(
    id="longest_drawdown_duration",
    name="Longest drawdown duration",
    category="drawdown",
    unit="periods",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Longest time from a peak until wealth regained that peak (or until the end of "
        "the history, if not yet recovered).",
        formula="max_k (recovery_k - peak_k) in periods; ongoing episodes use n - peak_k",
        inputs="Periodic simple returns.",
        retail="The longest stretch an investor would have waited to get back to a previous high.",
        institutional="Peak-to-recovery duration in observation periods; an ongoing episode is "
        "a lower bound and is flagged as such.",
        assumptions=("Recovery means regaining the prior peak of compounded wealth.",),
        misleading_when=(_PATH_CAVEAT, "The longest episode is still ongoing (a lower bound)."),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(
            lib(
                PA,
                "findDrawdowns (length)",
                agrees=False,
                note="PerformanceAnalytics counts from the first underwater period, giving "
                "one period less for recovered episodes.",
            ),
        ),
        references=(BACON,),
        convention="Measured in observation periods from the peak to the recovery period "
        "inclusive; details report the equivalent in years when the frequency is regular.",
    ),
)
def longest_drawdown_duration(ctx: MetricContext) -> Computed:
    episodes = ctx.cache.episodes
    if not episodes:
        return Computed(0.0, details={"episodes": 0})
    longest = max(episodes, key=lambda e: e.duration_periods)
    ppy = ctx.returns.periods_per_year
    notes: tuple[str, ...] = ()
    if not longest.recovered:
        notes = (
            "The longest drawdown has not recovered by the end of the data; the duration "
            "is a lower bound.",
        )
    return Computed(
        float(longest.duration_periods),
        details={
            "years": longest.duration_periods / ppy if ppy else None,
            "peak_date": longest.peak_date,
            "recovery_date": longest.recovery_date,
            "ongoing": not longest.recovered,
        },
        notes=notes,
    )


@metric(
    id="drawdown_count",
    name="Number of drawdown episodes",
    category="drawdown",
    unit="count",
    direction="neutral",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="How many distinct peak-to-recovery declines occurred.",
        formula="K = number of maximal runs with W_t below its running peak",
        inputs="Periodic simple returns.",
        retail="How often the investment fell below a previous high.",
        institutional="Context for average drawdown and durations; depends strongly on data "
        "frequency and history length.",
        assumptions=("Every decline below a prior peak counts, however small.",),
        misleading_when=("Compared across frequencies or history lengths.",),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(lib(PA, "findDrawdowns (negative episodes)"),),
        references=(BACON,),
        convention="An ongoing episode at the end of the data is counted.",
    ),
)
def drawdown_count(ctx: MetricContext) -> Computed:
    episodes = ctx.cache.episodes
    ongoing = sum(1 for e in episodes if not e.recovered)
    return Computed(float(len(episodes)), details={"ongoing": ongoing})


@metric(
    id="time_underwater_pct",
    name="Time under water",
    category="drawdown",
    unit="fraction",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Share of periods in which wealth was below its previous peak.",
        formula="(1/n) * #{t : D_t < 0}",
        inputs="Periodic simple returns.",
        retail="The share of the time the investment was below a previous high.",
        institutional="Complements depth measures with persistence; high values with shallow "
        "drawdowns indicate grinding rather than crash risk.",
        assumptions=("Wealth index starts at 1 before the first return.",),
        misleading_when=(_PATH_CAVEAT,),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(),
        references=(BACON,),
        convention="Counted over observations 1..n (the inception point is excluded).",
    ),
)
def time_underwater_pct(ctx: MetricContext) -> float:
    return float(np.mean(ctx.cache.drawdown < 0.0))


@metric(
    id="ulcer_index",
    name="Ulcer Index",
    category="drawdown",
    unit="decimal_return",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Root-mean-square drawdown: combines depth and duration of declines.",
        formula="sqrt( (1/n) * sum_t D_t^2 )",
        inputs="Periodic simple returns.",
        retail="A single number for how deep and how long-lasting the declines were; 0 means "
        "the investment never fell below a previous high.",
        institutional="Martin & McCann's Ulcer Index on the canonical drawdown path; the "
        "denominator of the Martin ratio (Ulcer Performance Index).",
        assumptions=("Drawdowns measured from running peaks of compounded wealth.",),
        misleading_when=(_PATH_CAVEAT, "Compared across data frequencies."),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(
            lib(
                PA,
                "UlcerIndex",
                agrees=False,
                note="PerformanceAnalytics 2.0.4 builds drawdowns with DrawdownPeak, which "
                "divides returns by 100 (assumes percent inputs); agreement is verified "
                "against sqrt(mean(Drawdowns(R)^2)) instead.",
            ),
        ),
        references=(MARTIN_MCCANN_1989, BACON),
        convention="Non-negative magnitude in decimal units, computed from the canonical "
        "drawdown path over observations 1..n.",
    ),
)
def ulcer_index(ctx: MetricContext) -> float:
    return ctx.cache.ulcer_index


@metric(
    id="pain_index",
    name="Pain Index",
    category="drawdown",
    unit="decimal_return",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Average drawdown over time (mean absolute drawdown across all periods).",
        formula="(1/n) * sum_t |D_t|",
        inputs="Periodic simple returns.",
        retail="How far below its previous high the investment was, on average, over the whole "
        "history.",
        institutional="Zephyr Pain Index (see Bacon); time-weighted, unlike the episode-based "
        "average drawdown.",
        assumptions=("Drawdowns measured from running peaks of compounded wealth.",),
        misleading_when=(_PATH_CAVEAT,),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(
            lib(
                PA,
                "PainIndex",
                agrees=False,
                note="Same DrawdownPeak percent-input issue as UlcerIndex; verified against "
                "mean(|Drawdowns(R)|).",
            ),
        ),
        references=(BACON,),
        convention="Non-negative magnitude in decimal units over observations 1..n.",
    ),
)
def pain_index(ctx: MetricContext) -> float:
    return float(np.mean(np.abs(ctx.cache.drawdown)))
