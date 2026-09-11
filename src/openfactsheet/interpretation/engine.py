"""Two-layer interpretation engine (CLAUDE.md section 16).

Plain-language and professional text come from each metric's registry
documentation; context notes come from :mod:`templates`. OpenFactsheet
explains measurements; it does not say "buy" or "sell".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openfactsheet.interpretation.templates import RULES
from openfactsheet.metrics.registry import get_metric
from openfactsheet.models.metric import MetricCollection
from openfactsheet.models.report import Interpretation

if TYPE_CHECKING:
    from openfactsheet.metrics.context import MetricContext


def build_interpretations(
    metrics: MetricCollection, ctx: MetricContext
) -> dict[str, Interpretation]:
    out: dict[str, Interpretation] = {}
    for result in metrics:
        docs = get_metric(result.id).docs
        context: list[str] = []
        if result.value is None and result.reason:
            context.append(result.reason)
        for rule in RULES:
            note = rule(result, metrics, ctx)
            if note:
                context.append(note)
        out[result.id] = Interpretation(
            metric_id=result.id,
            plain=docs.retail,
            professional=docs.institutional,
            context=tuple(context),
        )
    return out
