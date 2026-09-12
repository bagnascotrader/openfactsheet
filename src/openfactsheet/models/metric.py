"""Metric definitions (registry metadata) and metric results (structured output)."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal

MetricStatus = Literal[
    "applicable",
    "low_confidence",
    "supplementary",
    "not_applicable",
    "insufficient_data",
    "error",
]

Direction = Literal[
    "higher_is_better",
    "lower_is_better",
    "context_dependent",
    "neutral",
]

Confidence = Literal["high", "moderate", "low", "not_assessable"]

# CLAUDE.md section 42: observed vs derived vs estimated vs model-dependent.
Nature = Literal["observed", "derived", "estimated", "model_dependent"]

Unit = Literal[
    "decimal_return",  # 0.01 == 1%
    "fraction",  # share of observations, 0..1
    "ratio",
    "periods",
    "count",
    "correlation",
    "probability",
    "beta",
]

Category = Literal[
    "returns",
    "volatility",
    "risk_adjusted",
    "drawdown",
    "tail",
    "distribution",
    "dependence",
    "consistency",
    "benchmark",
    "factors",
    "statistical",
]

CATEGORY_TITLES: Mapping[str, str] = MappingProxyType(
    {
        "returns": "Return summary",
        "volatility": "Risk summary",
        "drawdown": "Drawdowns",
        "risk_adjusted": "Risk-adjusted performance",
        "tail": "Tail behavior",
        "distribution": "Distribution",
        "consistency": "Consistency",
        "dependence": "Serial dependence & smoothing",
        "benchmark": "Benchmark-relative analysis",
        "factors": "Factor analysis",
        "statistical": "Statistical confidence",
    }
)

# Order in which categories appear in reports (CLAUDE.md section 30).
CATEGORY_ORDER: tuple[str, ...] = tuple(CATEGORY_TITLES)


@dataclass(frozen=True)
class AcademicReference:
    """A paper, book, or practitioner standard that defines a metric."""

    citation: str
    url: str | None = None


@dataclass(frozen=True)
class LibraryReference:
    """A reference implementation and whether it agrees with the OpenFactsheet convention."""

    library: str
    function: str
    agrees: bool
    note: str = ""


@dataclass(frozen=True)
class MetricDocs:
    """Answers to the twelve documentation questions of CLAUDE.md section 1.4.

    ``direction`` (question 4) and the minimum-data policy (question 9) live on
    :class:`MetricDefinition`; everything else is here.
    """

    measures: str  # 1. What does it measure?
    formula: str  # 2. Mathematical definition (plain text / LaTeX-lite)
    inputs: str  # 3. Required inputs
    retail: str  # 5. Plain-language interpretation
    institutional: str  # 6. Professional interpretation
    assumptions: tuple[str, ...]  # 7.
    misleading_when: tuple[str, ...]  # 8.
    minimum_data: str  # 9. (human explanation of the policy)
    reference_implementations: tuple[LibraryReference, ...]  # 10.
    references: tuple[AcademicReference, ...]  # 11.
    convention: str  # 12. OpenFactsheet convention where definitions vary
    # Exact definition in LaTeX, using the notation of docs/reference/notation.md.
    # It must describe precisely what the implementation computes.
    formula_latex: str = ""
    # Data conditions under which the function raises UndefinedMetric
    # (reported as status "not_applicable" with that reason).
    undefined_when: tuple[str, ...] = ()


@dataclass(frozen=True)
class Computed:
    """Rich return value for metric functions that need to attach details or notes.

    Metric functions may return a bare ``float`` or a ``Computed``.
    """

    value: float
    details: Mapping[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


MetricFunction = Callable[[Any], "float | Computed"]


@dataclass(frozen=True)
class MetricDefinition:
    """Registry entry for one canonical metric.

    Flags describe *requirements*; the policy layer turns them into status and
    confidence. Metric functions never decide applicability themselves.
    """

    id: str
    name: str
    category: Category
    unit: Unit
    direction: Direction
    nature: Nature
    min_data_policy: str
    docs: MetricDocs
    func: MetricFunction
    requires_benchmark: bool = False
    requires_factors: bool = False
    annualized: bool = False
    uses_wealth_path: bool = False
    volatility_based: bool = False
    supplementary: bool = False
    assumption_keys: tuple[str, ...] = ()
    formula_version: int = 1

    @property
    def formula_id(self) -> str:
        return f"{self.id}@v{self.formula_version}"

    def to_dict(self) -> dict[str, Any]:
        d = self.docs
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "unit": self.unit,
            "direction": self.direction,
            "nature": self.nature,
            "formula_id": self.formula_id,
            "min_data_policy": self.min_data_policy,
            "requires_benchmark": self.requires_benchmark,
            "requires_factors": self.requires_factors,
            "annualized": self.annualized,
            "uses_wealth_path": self.uses_wealth_path,
            "volatility_based": self.volatility_based,
            "supplementary": self.supplementary,
            "measures": d.measures,
            "formula": d.formula,
            "inputs": d.inputs,
            "convention": d.convention,
        }


@dataclass(frozen=True)
class MetricResult:
    """Structured outcome of one metric (CLAUDE.md section 10).

    ``value`` is ``None`` whenever the metric could not be validly computed, and
    ``reason`` then says why. A non-finite value can never be stored.
    """

    id: str
    name: str
    category: str
    value: float | None
    unit: str | None
    status: MetricStatus
    direction: Direction
    confidence: Confidence
    nature: Nature
    observations: int
    formula_id: str
    methodology_version: str
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    reason: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)
    reference_values: Mapping[str, float] | None = None

    def __post_init__(self) -> None:
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError(f"MetricResult {self.id!r} cannot hold non-finite value {self.value}")
        if self.value is None and self.reason is None:
            raise ValueError(f"MetricResult {self.id!r} has no value and no reason")
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    @property
    def has_value(self) -> bool:
        return self.value is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "confidence": self.confidence,
            "direction": self.direction,
            "nature": self.nature,
            "observations": self.observations,
            "formula_id": self.formula_id,
            "methodology_version": self.methodology_version,
            "assumptions": list(self.assumptions),
            "warnings": list(self.warnings),
            "reason": self.reason,
            "details": dict(self.details),
            "reference_values": (
                dict(self.reference_values) if self.reference_values is not None else None
            ),
        }


@dataclass(frozen=True)
class MetricCollection:
    """Ordered, id-addressable collection of metric results."""

    results: tuple[MetricResult, ...]

    def __iter__(self) -> Iterator[MetricResult]:
        return iter(self.results)

    def __len__(self) -> int:
        return len(self.results)

    def __getitem__(self, metric_id: str) -> MetricResult:
        for r in self.results:
            if r.id == metric_id:
                return r
        raise KeyError(metric_id)

    def __contains__(self, metric_id: object) -> bool:
        return any(r.id == metric_id for r in self.results)

    def get(self, metric_id: str) -> MetricResult | None:
        try:
            return self[metric_id]
        except KeyError:
            return None

    def by_category(self, category: str) -> tuple[MetricResult, ...]:
        return tuple(r for r in self.results if r.category == category)

    def values(self) -> dict[str, float | None]:
        return {r.id: r.value for r in self.results}

    def to_frame(self) -> Any:
        """Metrics as a pandas DataFrame indexed by metric id."""
        import pandas as pd

        rows = [
            {
                "id": r.id,
                "name": r.name,
                "category": r.category,
                "value": r.value,
                "unit": r.unit,
                "status": r.status,
                "confidence": r.confidence,
                "observations": r.observations,
                "reason": r.reason,
                "warnings": "; ".join(r.warnings),
            }
            for r in self.results
        ]
        return pd.DataFrame(rows).set_index("id")
