"""Deterministic percent-vs-decimal plausibility classifier (decision 0013).

Inputs such as ``1.5, -0.8, 2.1`` are probably percentages, while
``0.015, -0.008, 0.021`` are probably decimals. A single naive threshold is not
enough, so the classifier combines:

1. an explicit ``%`` label in the source (strong evidence of percent);
2. the median absolute return compared with a frequency-dependent upper bound
   for plausible decimal returns;
3. the impossibility of decimal returns below -100%.

In the zone where both readings are plausible it refuses to guess and raises
:class:`AmbiguousReturnScaleError`; the caller may then declare the scale.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt

from openfactsheet.exceptions import AmbiguousReturnScaleError, InputError
from openfactsheet.models.input import ObservationFrequency, ReturnScale
from openfactsheet.policy.defaults import canonical_methodology

DeclaredScale = Literal["decimal", "percent"]


@dataclass(frozen=True)
class ScaleDecision:
    scale: ReturnScale
    factor: float  # multiply raw values by this to obtain decimal returns
    evidence: str


def detect_return_scale(
    values: npt.NDArray[np.float64],
    frequency: ObservationFrequency,
    *,
    percent_hint: bool | None = None,
    declared: DeclaredScale | None = None,
) -> ScaleDecision:
    """Classify raw return values as decimal or percent.

    Args:
        values: Finite raw values (NaN already removed).
        frequency: Observation frequency (affects plausible magnitudes).
        percent_hint: ``True`` if the source labelled values with ``%``.
        declared: Scale explicitly declared by the caller; always wins.
    """
    if declared is not None:
        if declared not in ("decimal", "percent"):
            raise InputError(f"return_scale must be 'decimal' or 'percent', got {declared!r}.")
        if declared == "percent":
            return ScaleDecision("declared_percent", 0.01, "Scale declared by the caller: percent.")
        return ScaleDecision("declared_decimal", 1.0, "Scale declared by the caller: decimal.")

    if percent_hint:
        return ScaleDecision("detected_percent", 0.01, "Source values carry explicit '%' labels.")

    nonzero = np.abs(values[values != 0.0])
    if nonzero.size == 0:
        return ScaleDecision(
            "detected_decimal", 1.0, "All returns are exactly zero; scale is immaterial."
        )

    conv = canonical_methodology().get("return_scale")
    upper = float(conv["decimal_median_abs_upper"][frequency.value])
    confident = upper / float(conv["confident_divisor"])
    median_abs = float(np.median(nonzero))
    below_minus_one = int(np.sum(values < -1.0))

    if median_abs > upper:
        if median_abs / 100.0 > upper:
            hint = (
                " All values are positive, which suggests price or NAV levels rather than "
                "returns; convert them to returns explicitly (r_t = P_t / P_(t-1) - 1)."
                if bool(np.all(values > 0))
                else ""
            )
            raise InputError(
                f"Values are implausible as {frequency.value} returns in either decimal or "
                f"percent scale (median absolute value {median_abs:g}).{hint}"
            )
        return ScaleDecision(
            "detected_percent",
            0.01,
            f"Median absolute value {median_abs:g} exceeds the plausible decimal bound "
            f"{upper:g} for {frequency.value} returns; interpreted as percent.",
        )

    if median_abs <= confident:
        evidence = (
            f"Median absolute value {median_abs:g} is within the confident decimal bound "
            f"{confident:g} for {frequency.value} returns."
        )
        if below_minus_one:
            evidence += (
                f" {below_minus_one} value(s) below -1 are impossible as decimal returns and "
                "are flagged, not rescaled."
            )
        return ScaleDecision("detected_decimal", 1.0, evidence)

    # Ambiguous zone: both readings are plausible by magnitude.
    if below_minus_one:
        return ScaleDecision(
            "detected_percent",
            0.01,
            f"Median absolute value {median_abs:g} is plausible in both scales, but "
            f"{below_minus_one} value(s) below -1 are impossible as decimal returns; "
            "interpreted as percent.",
        )
    raise AmbiguousReturnScaleError(
        f"Cannot tell whether these {frequency.value} returns are decimals or percentages "
        f"(median absolute value {median_abs:g}: e.g. {median_abs:g} could mean "
        f"{median_abs:.2%} or {median_abs / 100:.2%} per period). Declare the scale, e.g. "
        "ofs.analyze(returns, return_scale='percent') or return_scale='decimal'."
    )
