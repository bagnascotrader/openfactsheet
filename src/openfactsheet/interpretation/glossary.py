"""Meaning of statuses and confidence labels shown in reports."""

from __future__ import annotations

STATUS_MEANING: dict[str, str] = {
    "applicable": "Computed; the data meet the metric's statistical requirements.",
    "low_confidence": "Computed and shown, but the estimate is unreliable for the reasons given.",
    "supplementary": "Diagnostic or model-dependent statistic shown for context.",
    "not_applicable": "Cannot be meaningfully computed for this input (reason given).",
    "insufficient_data": "Fewer observations than the metric's mathematical minimum.",
    "error": "Unexpected calculation failure; the value is withheld (please report).",
}

CONFIDENCE_MEANING: dict[str, str] = {
    "high": "Enough data of adequate quality for a stable estimate.",
    "moderate": "Usable estimate with material sampling or data-quality uncertainty.",
    "low": "Highly uncertain estimate; do not rely on it alone.",
    "not_assessable": "No value to assess.",
}

CONFIDENCE_DISCLAIMER = (
    "Confidence describes the reliability of an estimate, not the quality of the investment."
)
