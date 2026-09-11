"""Tail-risk metrics (CLAUDE.md section 12.5).

Confidence levels are canonical (95%) and not user-selectable in the canonical
report.
"""

from __future__ import annotations

import numpy as np

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import (
    ACERBI_TASCHE_2002,
    BACON,
    EMP,
    HYNDMAN_FAN_1996,
    JORION_2006,
    NUMPY,
    PA,
    QS,
    lib,
)
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import Computed, MetricDocs

_TAIL_CAVEATS = (
    "Few observations fall in the 5% tail: with monthly data a 95% estimate rests on "
    "roughly n/20 points.",
    "The history does not contain a stress period.",
    "Returns are smoothed, which compresses the tail.",
)


def _alpha(ctx: MetricContext) -> float:
    return 1.0 - float(ctx.methodology.get("tail.var_confidence"))


@metric(
    id="var_historical_95",
    name="Value at Risk (historical, 95%)",
    category="tail",
    unit="decimal_return",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="tail",
    assumptions=("tail",),
    docs=MetricDocs(
        measures="Return threshold that was breached in the worst 5% of periods.",
        formula="Q_0.05(r), empirical quantile with linear interpolation (Hyndman-Fan type 7)",
        inputs="Periodic simple returns.",
        retail="In about 1 period out of 20, the return was this bad or worse.",
        institutional="Historical-simulation VaR at 95% for one observation period; says "
        "nothing about losses beyond the threshold (see Expected Shortfall).",
        assumptions=("The supplied history is representative of the tail.",),
        misleading_when=_TAIL_CAVEATS,
        minimum_data="At least 2 observations; low confidence when fewer than 5 observations "
        "are expected in the tail (n < 100).",
        reference_implementations=(
            lib(
                PA,
                "VaR(p=0.95, method='historical')",
                note="Reports the negated quantile (loss as a positive number in 2.0.4 "
                "internals, negative in the public wrapper).",
            ),
            lib(NUMPY, "quantile(method='linear')"),
            lib(
                QS,
                "stats.value_at_risk",
                agrees=False,
                note="QuantStats defaults to a parametric (normal) VaR.",
            ),
        ),
        references=(JORION_2006, HYNDMAN_FAN_1996),
        convention="95% confidence, per observation period, signed return (negative = loss), "
        "linear interpolation (decision 0010).",
    ),
)
def var_historical_95(ctx: MetricContext) -> float:
    return float(np.quantile(ctx.r, _alpha(ctx), method="linear"))


@metric(
    id="expected_shortfall_historical_95",
    name="Expected Shortfall / CVaR (historical, 95%)",
    category="tail",
    unit="decimal_return",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="tail",
    assumptions=("tail",),
    docs=MetricDocs(
        measures="Average return in the periods at or below the 95% VaR threshold.",
        formula="mean(r_t | r_t <= Q_0.05(r))",
        inputs="Periodic simple returns.",
        retail="When things went badly (the worst 5% of periods), this was the average return.",
        institutional="Historical Expected Shortfall (CVaR); a coherent risk measure (Acerbi & "
        "Tasche, 2002) that accounts for the severity of tail losses.",
        assumptions=("The supplied history is representative of the tail.",),
        misleading_when=_TAIL_CAVEATS,
        minimum_data="At least 2 observations; low confidence when fewer than 5 observations "
        "are expected in the tail (n < 100).",
        reference_implementations=(
            lib(
                PA,
                "ES(p=0.95, method='historical')",
                note="Uses returns strictly below the quantile; identical unless an "
                "observation equals the quantile exactly.",
            ),
            lib(
                QS,
                "stats.cvar",
                agrees=False,
                note="QuantStats conditions on a parametric VaR threshold.",
            ),
            lib(
                EMP,
                "conditional_value_at_risk",
                note="Uses returns at or below the 5th percentile.",
            ),
        ),
        references=(ACERBI_TASCHE_2002, JORION_2006, BACON),
        convention="Mean of returns at or below the linear-interpolated 5% quantile; signed.",
    ),
)
def expected_shortfall_historical_95(ctx: MetricContext) -> Computed:
    q = float(np.quantile(ctx.r, _alpha(ctx), method="linear"))
    tail = ctx.r[ctx.r <= q]
    return Computed(float(np.mean(tail)), details={"tail_observations": int(tail.size)})


@metric(
    id="tail_ratio",
    name="Tail ratio (95th / 5th percentile)",
    category="tail",
    unit="ratio",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="tail",
    docs=MetricDocs(
        measures="Size of the right tail relative to the left tail.",
        formula="|Q_0.95(r)| / |Q_0.05(r)|",
        inputs="Periodic simple returns.",
        retail="Above 1: the best periods were larger than the worst periods were bad.",
        institutional="Quantile-based asymmetry measure, robust to single extremes but noisy "
        "in short samples.",
        assumptions=("Linear-interpolated empirical quantiles.",),
        misleading_when=_TAIL_CAVEATS[:2],
        minimum_data="At least 2 observations; low confidence below n = 100.",
        reference_implementations=(lib(EMP, "tail_ratio"), lib(QS, "stats.tail_ratio")),
        references=(BACON,),
        convention="Absolute values of the 95th and 5th percentiles (decision 0010).",
    ),
)
def tail_ratio(ctx: MetricContext) -> float:
    lo = float(np.quantile(ctx.r, 0.05, method="linear"))
    hi = float(np.quantile(ctx.r, 0.95, method="linear"))
    if lo == 0.0:
        raise UndefinedMetric("The 5th percentile return is zero; the tail ratio is undefined.")
    return abs(hi) / abs(lo)
