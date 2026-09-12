"""Suspiciously large returns (flagged, never removed)."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


def robust_outlier_count(r: npt.NDArray[np.float64], threshold: float) -> int:
    """Count observations whose robust z-score exceeds ``threshold``.

    Robust z-score: ``|r - median| / (1.4826 * MAD)``.
    """
    if r.shape[0] < 5:
        return 0
    median = float(np.median(r))
    mad = float(np.median(np.abs(r - median)))
    if mad == 0.0:
        return 0
    # A subnormal MAD can overflow the ratio to +inf, which is correctly an outlier.
    with np.errstate(over="ignore"):
        z = np.abs(r - median) / (1.4826 * mad)
    return int(np.sum(z > threshold))
