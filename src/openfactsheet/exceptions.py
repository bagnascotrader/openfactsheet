"""Package exceptions.

Input corruption fails early with one of these exceptions. Metric-specific
problems never raise out of :func:`openfactsheet.analyze`; they are captured in
:class:`~openfactsheet.models.metric.MetricResult` objects instead.
"""

from __future__ import annotations


class OpenFactsheetError(Exception):
    """Base class for all OpenFactsheet errors."""


class InputError(OpenFactsheetError, ValueError):
    """The supplied data cannot be interpreted as a return history."""


class AmbiguousReturnScaleError(InputError):
    """Returns could plausibly be either decimals or percentages.

    Resolve by declaring the scale explicitly, e.g.
    ``ofs.analyze(returns, return_scale="percent")``.
    """


class FrequencyInferenceError(InputError):
    """Observation frequency could not be established or was declared inconsistently."""


class BenchmarkAlignmentError(OpenFactsheetError, ValueError):
    """Fund and benchmark returns cannot be aligned without inventing data."""


class FactorAlignmentError(OpenFactsheetError, ValueError):
    """Fund and factor returns cannot be aligned without inventing data."""


class MetricCalculationError(OpenFactsheetError):
    """Unexpected failure inside a metric calculation (captured as status ``error``)."""


class UndefinedMetric(OpenFactsheetError):
    """Raised by a metric function when its value is mathematically undefined.

    Example: a Sharpe ratio when volatility is exactly zero. The engine turns
    this into a ``not_applicable`` :class:`MetricResult` carrying ``reason``.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class OCRExtractionError(InputError):
    """Image/PDF extraction failed or produced inadequate confidence (roadmap phase 6)."""


__all__ = [
    "AmbiguousReturnScaleError",
    "BenchmarkAlignmentError",
    "FactorAlignmentError",
    "FrequencyInferenceError",
    "InputError",
    "MetricCalculationError",
    "OCRExtractionError",
    "OpenFactsheetError",
    "UndefinedMetric",
]
