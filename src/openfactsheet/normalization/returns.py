"""Turn parsed input (:class:`RawReturns`) into a canonical :class:`ReturnSeries`.

Order of operations (all recorded in :class:`InputDiagnostics`):

1. reject infinite values, empty input and duplicate timestamps;
2. sort unsorted timestamps (recorded as a transformation);
3. trim leading/trailing missing values, drop interior missing values
   (never filled — counted and disclosed);
4. infer frequency from calendar spacing, or accept a declared frequency;
5. detect percent vs decimal scale and convert to decimal returns.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from openfactsheet.exceptions import FrequencyInferenceError
from openfactsheet.models.input import (
    FrequencySource,
    InputDiagnostics,
    ObservationFrequency,
    RawReturns,
    ReturnSeries,
)
from openfactsheet.normalization.frequency import (
    FrequencyInference,
    infer_frequency,
    parse_declared_frequency,
)
from openfactsheet.normalization.scaling import DeclaredScale, detect_return_scale
from openfactsheet.normalization.validation import validate_dates, validate_values
from openfactsheet.policy.annualization import periods_per_year


def normalize_returns(
    raw: RawReturns,
    *,
    return_scale: DeclaredScale | None = None,
    frequency: str | ObservationFrequency | None = None,
) -> tuple[ReturnSeries, InputDiagnostics]:
    """Normalize parsed input into simple decimal returns plus input diagnostics."""
    name = raw.name
    values = np.array(raw.values, dtype=np.float64)
    dates = raw.dates
    transformations = list(raw.transformations)
    warnings: list[str] = []

    validate_values(values, name)

    was_sorted = True
    if dates is not None:
        validate_dates(dates, name)
        if not dates.is_monotonic_increasing:
            order = np.argsort(dates.values, kind="stable")
            dates = dates[order]
            values = values[order]
            was_sorted = False
            transformations.append("observations sorted chronologically")
            warnings.append("Input timestamps were not in chronological order and were sorted.")

    # Missing values: trim the ends, drop (never fill) interior gaps.
    missing = np.isnan(values)
    valid_positions = np.flatnonzero(~missing)
    first, last = int(valid_positions[0]), int(valid_positions[-1])
    leading, trailing = first, len(values) - 1 - last
    values = values[first : last + 1]
    if dates is not None:
        dates = dates[first : last + 1]
    # Frequency evidence comes from the full date grid, including dates whose
    # value is missing: a NaN row is a missing observation, not irregular spacing.
    grid_dates = dates
    interior_missing = np.isnan(values)
    n_interior = int(interior_missing.sum())
    if n_interior:
        values = values[~interior_missing]
        if dates is not None:
            dates = dates[~interior_missing]
        warnings.append(
            f"{n_interior} interior missing value(s) were excluded (not filled). Metrics use the "
            "remaining observations; compounding skips the missing periods."
        )
    if leading or trailing:
        transformations.append(
            f"trimmed {leading} leading and {trailing} trailing missing value(s)"
        )

    # Frequency.
    declared = parse_declared_frequency(frequency) if frequency is not None else None
    freq_source: FrequencySource
    if dates is not None and grid_dates is not None:
        inference = infer_frequency(grid_dates)
        if inference.missing_expected_periods is not None and n_interior:
            inference = replace(
                inference,
                missing_expected_periods=inference.missing_expected_periods + n_interior,
            )
        if (
            declared is not None
            and inference.frequency.is_regular
            and inference.frequency != declared
        ):
            raise FrequencyInferenceError(
                f"{name}: declared frequency {declared.value!r} contradicts the dates, which "
                f"indicate {inference.frequency.value!r} ({inference.evidence})"
            )
        if declared is not None and not inference.frequency.is_regular:
            raise FrequencyInferenceError(
                f"{name}: declared frequency {declared.value!r} contradicts irregular dates "
                f"({inference.evidence})"
            )
        freq_source = "inferred" if inference.frequency.is_regular else "none"
    elif declared is not None:
        inference = FrequencyInference(
            declared,
            periods_per_year(declared),
            False,
            None,
            0,
            f"Undated values; frequency {declared.value!r} declared by the caller.",
        )
        freq_source = "declared"
        if declared is ObservationFrequency.DAILY:
            warnings.append(
                "Declared daily frequency without dates: assuming a business-day calendar "
                "(252 periods per year)."
            )
    else:
        inference = FrequencyInference(
            ObservationFrequency.UNKNOWN,
            None,
            False,
            None,
            0,
            "Undated values: observation frequency cannot be inferred, so no metric is "
            "annualized. Supply dates (e.g. a pandas Series with a DatetimeIndex) or declare "
            "the frequency.",
        )
        freq_source = "none"
    if not inference.frequency.is_regular:
        warnings.append(inference.evidence)

    # Scale.
    decision = detect_return_scale(
        values,
        inference.frequency,
        percent_hint=raw.percent_hint,
        declared=return_scale,
    )
    if decision.factor != 1.0:
        values = values * decision.factor
        transformations.append("percent values divided by 100 to obtain decimal returns")

    n_impossible = int(np.sum(values < -1.0))
    if n_impossible:
        warnings.append(
            f"{n_impossible} return(s) below -100% are impossible for ordinary simple returns; "
            "they were kept (not clipped) and wealth-path metrics are marked not applicable."
        )

    diagnostics = InputDiagnostics(
        name=name,
        source_type=raw.source_type,
        observations=len(values),
        start=dates[0].strftime("%Y-%m-%d") if dates is not None else None,
        end=dates[-1].strftime("%Y-%m-%d") if dates is not None else None,
        frequency=inference.frequency,
        frequency_source=freq_source,
        frequency_evidence=inference.evidence,
        periods_per_year=inference.periods_per_year,
        return_scale=decision.scale,
        return_scale_evidence=decision.evidence,
        missing_values=n_interior,
        leading_missing_trimmed=leading,
        trailing_missing_trimmed=trailing,
        missing_expected_periods=inference.missing_expected_periods,
        duplicate_dates=inference.duplicate_periods,
        was_sorted=was_sorted,
        transformations=tuple(transformations),
        warnings=tuple(warnings),
    )
    series = ReturnSeries(
        name=name,
        values=values,
        dates=dates,
        frequency=inference.frequency,
        periods_per_year=inference.periods_per_year,
        frequency_source=freq_source,
        source_type=raw.source_type,
        return_scale=decision.scale,
        metadata=dict(raw.metadata),
        input_diagnostics=diagnostics,
    )
    return series, diagnostics
