"""Consistency metrics (CLAUDE.md section 12.8)."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import BACON, QS, lib
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import MetricDocs


def _longest_run(mask: npt.NDArray[np.bool_]) -> int:
    longest = current = 0
    for flag in mask:
        current = current + 1 if flag else 0
        longest = max(longest, current)
    return longest


@metric(
    id="positive_period_pct",
    name="Positive periods",
    category="consistency",
    unit="fraction",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="location",
    docs=MetricDocs(
        measures="Share of periods with a strictly positive return (hit rate).",
        formula="#{t : r_t > 0} / n",
        formula_latex=r"\mathrm{Pos} = \frac{1}{n} \#\{t : r_t > 0\}",
        inputs="Periodic simple returns.",
        retail="How often the investment made money in a period.",
        institutional="Win rate on the supplied frequency; says nothing about the size of wins "
        "and losses (see gain-to-pain, Omega). A very high hit rate with small gains can mask "
        "rare large losses.",
        assumptions=("Zero returns count as neither positive nor negative.",),
        misleading_when=(
            "Returns are smoothed or stale, which inflates the share of small positive periods.",
        ),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(
            lib(
                QS,
                "stats.win_rate",
                agrees=False,
                note="QuantStats excludes zero-return periods from the denominator.",
            ),
        ),
        references=(BACON,),
        convention="Denominator includes all observations (zeros count as not positive).",
    ),
)
def positive_period_pct(ctx: MetricContext) -> float:
    return float(np.mean(ctx.r > 0.0))


@metric(
    id="negative_period_pct",
    name="Negative periods",
    category="consistency",
    unit="fraction",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="location",
    docs=MetricDocs(
        measures="Share of periods with a strictly negative return.",
        formula="#{t : r_t < 0} / n",
        formula_latex=r"\mathrm{Neg} = \frac{1}{n} \#\{t : r_t < 0\}",
        inputs="Periodic simple returns.",
        retail="How often the investment lost money in a period.",
        institutional="Loss frequency on the supplied frequency; together with positive "
        "periods it also reveals the share of exactly-zero periods.",
        assumptions=("Zero returns count as neither positive nor negative.",),
        misleading_when=("Returns are smoothed or stale.",),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(),
        references=(BACON,),
        convention="Denominator includes all observations.",
    ),
)
def negative_period_pct(ctx: MetricContext) -> float:
    return float(np.mean(ctx.r < 0.0))


@metric(
    id="longest_winning_streak",
    name="Longest run of positive periods",
    category="consistency",
    unit="periods",
    direction="neutral",
    nature="observed",
    min_data_policy="path_risk",
    docs=MetricDocs(
        measures="Maximum number of consecutive periods with positive returns.",
        formula="max length of consecutive runs with r_t > 0",
        formula_latex=(
            r"\max \{ j - i + 1 : 1 \le i \le j \le n,\ r_u > 0 \ \forall u \in i..j \}"
            r" \ (0 \text{ if no } r_t > 0)"
        ),
        inputs="Periodic simple returns.",
        retail="The longest stretch of back-to-back gaining periods.",
        institutional="Descriptive path statistic; unusually long streaks relative to the hit "
        "rate can indicate smoothing.",
        assumptions=(),
        misleading_when=("Compared across frequencies or history lengths.",),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(lib(QS, "stats.consecutive_wins"),),
        references=(BACON,),
        convention="Strictly positive returns only.",
    ),
)
def longest_winning_streak(ctx: MetricContext) -> float:
    return float(_longest_run(ctx.r > 0.0))


@metric(
    id="longest_losing_streak",
    name="Longest run of negative periods",
    category="consistency",
    unit="periods",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="path_risk",
    docs=MetricDocs(
        measures="Maximum number of consecutive periods with negative returns.",
        formula="max length of consecutive runs with r_t < 0",
        formula_latex=(
            r"\max \{ j - i + 1 : 1 \le i \le j \le n,\ r_u < 0 \ \forall u \in i..j \}"
            r" \ (0 \text{ if no } r_t < 0)"
        ),
        inputs="Periodic simple returns.",
        retail="The longest stretch of back-to-back losing periods.",
        institutional="Descriptive path statistic complementing drawdown duration.",
        assumptions=(),
        misleading_when=("Compared across frequencies or history lengths.",),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(lib(QS, "stats.consecutive_losses"),),
        references=(BACON,),
        convention="Strictly negative returns only.",
    ),
)
def longest_losing_streak(ctx: MetricContext) -> float:
    return float(_longest_run(ctx.r < 0.0))
