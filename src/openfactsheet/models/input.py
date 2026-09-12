"""Canonical normalized input model.

A :class:`ReturnSeries` is what every downstream layer consumes. It always
holds *simple decimal returns* (``0.01`` = +1%) as a read-only ``float64``
array with no missing values; gaps in the history are described by
:class:`InputDiagnostics`, never filled.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Literal

import numpy as np
import numpy.typing as npt
import pandas as pd


class ObservationFrequency(str, Enum):
    """Observation frequency inferred from calendar spacing (or declared by the caller)."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    IRREGULAR = "irregular"
    UNKNOWN = "unknown"

    @property
    def is_regular(self) -> bool:
        return self not in (ObservationFrequency.IRREGULAR, ObservationFrequency.UNKNOWN)


FrequencySource = Literal["inferred", "declared", "none"]

ReturnScale = Literal[
    "detected_decimal",
    "detected_percent",
    "declared_decimal",
    "declared_percent",
]


def _frozen_array(values: npt.ArrayLike) -> npt.NDArray[np.float64]:
    arr = np.array(values, dtype=np.float64, copy=True)
    arr.setflags(write=False)
    return arr


@dataclass(frozen=True, eq=False)
class RawReturns:
    """Parsed but not yet normalized input (output of the ``input`` layer).

    ``values`` may contain NaN (missing observations) and may be in percent
    units; ``percent_hint`` is ``True`` when the source carried explicit ``%``
    labels. Normalization turns this into a :class:`ReturnSeries`.
    """

    values: npt.NDArray[np.float64]
    dates: pd.DatetimeIndex | None
    name: str
    source_type: str
    percent_hint: bool | None = None
    transformations: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    # Parser-level warnings (e.g. PDF extraction notes), carried into InputDiagnostics.
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", _frozen_array(self.values))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        if self.dates is not None and len(self.dates) != len(self.values):
            raise ValueError("dates and values must have the same length")


@dataclass(frozen=True, eq=False)
class ReturnSeries:
    """A normalized, immutable return history.

    Attributes:
        name: Display name of the series.
        values: Simple decimal returns, ``float64``, read-only, no NaN.
        dates: Period-end timestamps aligned with ``values`` (``None`` if undated).
        frequency: Observation frequency.
        periods_per_year: Canonical annualization factor, ``None`` when annualization
            is not defensible (irregular/unknown frequency).
        frequency_source: ``"inferred"`` from dates, ``"declared"`` by the caller, or ``"none"``.
        source_type: Where the data came from (``"list"``, ``"pandas.Series"``, ``"csv"``, ...).
        return_type: Always ``"simple"`` in methodology 0.1.
        return_scale: How percent/decimal scale was established.
        metadata: Free-form provenance metadata.
    """

    name: str
    values: npt.NDArray[np.float64]
    dates: pd.DatetimeIndex | None
    frequency: ObservationFrequency
    periods_per_year: float | None
    frequency_source: FrequencySource
    source_type: str
    return_scale: ReturnScale
    return_type: str = "simple"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    input_diagnostics: InputDiagnostics | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", _frozen_array(self.values))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        if self.dates is not None and len(self.dates) != len(self.values):
            raise ValueError("dates and values must have the same length")

    def __len__(self) -> int:
        return int(self.values.shape[0])

    @property
    def n(self) -> int:
        return len(self)

    @property
    def years(self) -> float | None:
        """Length of history in years, when a periods-per-year factor is defensible."""
        if self.periods_per_year is None:
            return None
        return self.n / self.periods_per_year

    def to_pandas(self) -> pd.Series:
        """The returns OpenFactsheet actually analyzed, as a pandas Series."""
        index = self.dates if self.dates is not None else pd.RangeIndex(1, self.n + 1)
        return pd.Series(np.array(self.values), index=index, name=self.name, dtype="float64")


@dataclass(frozen=True, eq=False)
class ReturnTable:
    """Several named return series (e.g. columns of a DataFrame, used by ``compare``)."""

    series: Mapping[str, ReturnSeries]

    def __post_init__(self) -> None:
        object.__setattr__(self, "series", MappingProxyType(dict(self.series)))


@dataclass(frozen=True)
class InputDiagnostics:
    """What OpenFactsheet believes it received (CLAUDE.md section 6)."""

    name: str
    source_type: str
    observations: int
    start: str | None
    end: str | None
    frequency: ObservationFrequency
    frequency_source: FrequencySource
    frequency_evidence: str
    periods_per_year: float | None
    return_scale: ReturnScale
    return_scale_evidence: str
    missing_values: int
    leading_missing_trimmed: int
    trailing_missing_trimmed: int
    missing_expected_periods: int | None
    duplicate_periods: int  # observations sharing a calendar period (identical timestamps fail)
    was_sorted: bool
    transformations: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def years(self) -> float | None:
        if self.periods_per_year is None:
            return None
        return self.observations / self.periods_per_year

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source_type": self.source_type,
            "observations": self.observations,
            "start": self.start,
            "end": self.end,
            "years": self.years,
            "frequency": self.frequency.value,
            "frequency_source": self.frequency_source,
            "frequency_evidence": self.frequency_evidence,
            "periods_per_year": self.periods_per_year,
            "return_scale": self.return_scale,
            "return_scale_evidence": self.return_scale_evidence,
            "missing_values": self.missing_values,
            "leading_missing_trimmed": self.leading_missing_trimmed,
            "trailing_missing_trimmed": self.trailing_missing_trimmed,
            "missing_expected_periods": self.missing_expected_periods,
            "duplicate_periods": self.duplicate_periods,
            "was_sorted": self.was_sorted,
            "transformations": list(self.transformations),
            "warnings": list(self.warnings),
        }

    def to_text(self) -> str:
        freq = self.frequency.value
        if self.frequency_source == "declared":
            freq += " (declared by caller)"
        years = f"{self.years:.1f} years" if self.years is not None else "not determinable"
        missing = (
            str(self.missing_expected_periods)
            if self.missing_expected_periods is not None
            else "not assessed"
        )
        lines = [
            f"Detected input:            {self.source_type}",
            f"Frequency:                 {freq}",
            f"Start:                     {self.start or 'undated'}",
            f"End:                       {self.end or 'undated'}",
            f"Observations:              {self.observations}",
            f"History:                   {years}",
            f"Return scale:              {self.return_scale.replace('_', ' ')}",
            f"Missing values (interior): {self.missing_values}",
            f"Missing expected periods:  {missing}",
            f"Duplicate periods:         {self.duplicate_periods}",
        ]
        if self.transformations:
            lines.append("Transformations applied:   " + "; ".join(self.transformations))
        if self.warnings:
            lines.append("Input warnings:")
            lines.extend(f"  - {w}" for w in self.warnings)
        return "\n".join(lines)
