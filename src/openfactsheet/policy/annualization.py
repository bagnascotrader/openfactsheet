"""Canonical annualization factors (decision 0002).

Calendar spacing is the primary evidence for frequency; the number of
observations is never used to guess an annualization factor.
"""

from __future__ import annotations

from openfactsheet.models.input import ObservationFrequency
from openfactsheet.policy.defaults import canonical_methodology


def periods_per_year(
    frequency: ObservationFrequency, *, calendar_days: bool = False
) -> float | None:
    """Canonical periods-per-year for a frequency, or ``None`` if annualization is not defensible.

    Args:
        frequency: Observation frequency.
        calendar_days: For daily data, whether weekend observations are present
            (calendar-day series such as crypto use 365; business-day series use 252).
    """
    table = canonical_methodology().get("annualization.periods_per_year")
    if frequency is ObservationFrequency.DAILY:
        return float(table["daily_calendar" if calendar_days else "daily_business"])
    if frequency in (
        ObservationFrequency.WEEKLY,
        ObservationFrequency.MONTHLY,
        ObservationFrequency.QUARTERLY,
        ObservationFrequency.YEARLY,
    ):
        return float(table[frequency.value])
    return None


def annualization_assumption(
    frequency: ObservationFrequency, ppy: float | None, source: str
) -> str:
    """Human-readable annualization statement attached to annualized metrics."""
    if ppy is None:
        return f"Not annualized: {frequency.value} observation frequency."
    origin = "declared by the caller" if source == "declared" else "inferred from dates"
    return f"Annualized with {ppy:g} periods per year ({frequency.value} frequency, {origin})."
