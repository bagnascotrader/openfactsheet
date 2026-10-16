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

# The canonical short notice. DISCLAIMER.md at the repository root is the single source
# of the full disclosure and of this line; tests/unit/test_disclaimer.py fails if this
# constant, DISCLAIMER.md and README.md stop carrying the identical text. Reports show
# it next to a link to the full text and never inside the return data.
SHORT_DISCLAIMER = (
    "For information and education only — not investment advice. Investing involves risk; "
    "past performance does not predict future results. Verify results and consult a "
    "qualified financial adviser."
)
# Repository-relative path of the full disclosure, linked from every report at the
# documentation version that produced it (DocumentationLinks.source).
DISCLAIMER_PATH = "DISCLAIMER.md"
