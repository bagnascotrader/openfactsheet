"""Return-smoothing risk assessment (decision 0014).

Smoothed or stale valuations (illiquid holdings, appraisal pricing, managed
marks) induce positive serial correlation and understate measured volatility,
inflating Sharpe-type ratios (Getmansky, Lo & Makarov, 2004). OpenFactsheet
never "unsmooths" returns in the canonical report; it diagnoses and warns.

The thresholds are a transparent heuristic, versioned with the methodology.
"""

from __future__ import annotations

import math

from openfactsheet.models.diagnostics import SmoothingRisk
from openfactsheet.policy.defaults import canonical_methodology


def assess_smoothing(lag1: float | None, n: int) -> tuple[SmoothingRisk, str]:
    conv = canonical_methodology().get("smoothing")
    if n < int(conv["min_observations"]):
        return "not_assessable", (
            f"Smoothing risk is not assessed with fewer than {conv['min_observations']} observations."
        )
    if lag1 is None:
        return "not_assessable", "Lag-1 autocorrelation is undefined (e.g. constant returns)."
    z = lag1 * math.sqrt(n)
    high, moderate = conv["high"], conv["moderate"]
    if lag1 >= high["lag1_min"] and z >= high["z_min"]:
        level: SmoothingRisk = "high"
    elif lag1 >= moderate["lag1_min"] and z >= moderate["z_min"]:
        level = "moderate"
    else:
        level = "none"
    evidence = (
        f"Lag-1 autocorrelation {lag1:.2f} (approx. z = {z:.2f} with {n} observations). "
        f"Rule: high if >= {high['lag1_min']:.2f} and z >= {high['z_min']}; moderate if "
        f">= {moderate['lag1_min']:.2f} and z >= {moderate['z_min']}."
    )
    return level, evidence
