"""The single metric registry (CLAUDE.md section 11).

Reports iterate over this registry, which enforces "compute all": a metric
cannot be dropped from a canonical report without being removed from the
registry (a methodology change).
"""

from __future__ import annotations

import importlib
from collections.abc import Callable

from openfactsheet.models.metric import (
    CATEGORY_ORDER,
    Category,
    Direction,
    MetricDefinition,
    MetricDocs,
    MetricFunction,
    Nature,
    Unit,
)
from openfactsheet.policy.thresholds import get_policy

_REGISTRY: dict[str, MetricDefinition] = {}
_ORDER: list[str] = []

_BUILTIN_MODULES = (
    "openfactsheet.metrics.returns",
    "openfactsheet.metrics.volatility",
    "openfactsheet.metrics.downside",
    "openfactsheet.metrics.drawdown",
    "openfactsheet.metrics.risk_adjusted",
    "openfactsheet.metrics.tail",
    "openfactsheet.metrics.distribution",
    "openfactsheet.metrics.consistency",
    "openfactsheet.metrics.dependence",
    "openfactsheet.metrics.benchmark",
    "openfactsheet.metrics.statistical",
)
_loaded = False

ASSUMPTION_KEYS = frozenset(
    {
        "annualization",
        "risk_free",
        "mar",
        "omega_threshold",
        "tail",
        "drawdown",
        "sample_std",
        "benchmark",
        "regression",
        "iid_asymptotics",
        "parametric",
        "sterling_excess",
        "entropic",
    }
)


def metric(
    *,
    id: str,
    name: str,
    category: Category,
    unit: Unit,
    direction: Direction,
    nature: Nature,
    min_data_policy: str,
    docs: MetricDocs,
    requires_benchmark: bool = False,
    annualized: bool = False,
    uses_wealth_path: bool = False,
    volatility_based: bool = False,
    supplementary: bool = False,
    assumptions: tuple[str, ...] = (),
    formula_version: int = 1,
) -> Callable[[MetricFunction], MetricFunction]:
    """Register a canonical metric function."""

    def decorator(func: MetricFunction) -> MetricFunction:
        if id in _REGISTRY:
            raise ValueError(f"Metric {id!r} is already registered")
        get_policy(min_data_policy)
        unknown = set(assumptions) - ASSUMPTION_KEYS
        if unknown:
            raise ValueError(f"Metric {id!r} declares unknown assumption keys {sorted(unknown)}")
        _REGISTRY[id] = MetricDefinition(
            id=id,
            name=name,
            category=category,
            unit=unit,
            direction=direction,
            nature=nature,
            min_data_policy=min_data_policy,
            docs=docs,
            func=func,
            requires_benchmark=requires_benchmark,
            annualized=annualized,
            uses_wealth_path=uses_wealth_path,
            volatility_based=volatility_based,
            supplementary=supplementary,
            assumption_keys=assumptions,
            formula_version=formula_version,
        )
        _ORDER.append(id)
        return func

    return decorator


def _load_builtin() -> None:
    global _loaded
    if _loaded:
        return
    for module in _BUILTIN_MODULES:
        importlib.import_module(module)
    _loaded = True


def all_metrics() -> tuple[MetricDefinition, ...]:
    """Every registered metric, in canonical report order."""
    _load_builtin()
    rank = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    order = {mid: i for i, mid in enumerate(_ORDER)}
    return tuple(sorted(_REGISTRY.values(), key=lambda d: (rank.get(d.category, 99), order[d.id])))


def get_metric(metric_id: str) -> MetricDefinition:
    _load_builtin()
    return _REGISTRY[metric_id]
