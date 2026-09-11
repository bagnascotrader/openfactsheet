"""Risk-free rate policy (decision 0005).

Methodology 0.1.0 uses a zero risk-free rate. This is a conventional,
prominently disclosed simplification; a deterministic public risk-free series
keyed on explicitly supplied currency metadata is on the roadmap. The investor's
currency is never inferred from the computer locale.
"""

from __future__ import annotations

from openfactsheet.policy.defaults import canonical_methodology


def risk_free_rate() -> float:
    return float(canonical_methodology().get("risk_free.rate"))


RISK_FREE_ASSUMPTION = (
    "Risk-free rate assumed to be 0% (methodology 0.1.0); the ratio therefore uses total "
    "rather than excess returns and is higher than an excess-return version when cash yields "
    "are positive."
)
