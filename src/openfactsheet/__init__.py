"""OpenFactsheet — standardized, transparent investment performance analytics
without metric cherry-picking.

>>> import openfactsheet as ofs
>>> report = ofs.analyze(returns)                      # doctest: +SKIP
>>> print(report.summary())                            # doctest: +SKIP
"""

from openfactsheet.api import analyze, compare, load, methodology, metric_catalog
from openfactsheet.exceptions import (
    AmbiguousReturnScaleError,
    BenchmarkAlignmentError,
    FrequencyInferenceError,
    InputError,
    MetricCalculationError,
    OCRExtractionError,
    OpenFactsheetError,
)
from openfactsheet.models.input import ObservationFrequency, ReturnSeries, ReturnTable
from openfactsheet.models.metric import MetricResult
from openfactsheet.models.report import FactsheetReport
from openfactsheet.policy.methodology_version import METHODOLOGY_VERSION
from openfactsheet.version import __version__

__all__ = [
    "METHODOLOGY_VERSION",
    "AmbiguousReturnScaleError",
    "BenchmarkAlignmentError",
    "FactsheetReport",
    "FrequencyInferenceError",
    "InputError",
    "MetricCalculationError",
    "MetricResult",
    "OCRExtractionError",
    "ObservationFrequency",
    "OpenFactsheetError",
    "ReturnSeries",
    "ReturnTable",
    "__version__",
    "analyze",
    "compare",
    "load",
    "methodology",
    "metric_catalog",
]
