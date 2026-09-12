"""Numerical helpers shared by metric implementations."""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt


def entropic_value_at_risk(losses: npt.NDArray[np.float64], alpha: float) -> float:
    """Entropic Value at Risk of a loss sample (Ahmadi-Javid, 2012).

    ``EVaR_alpha(X) = inf_{z > 0} z * ln( E[exp(X / z)] / alpha )`` for the
    empirical distribution of ``losses`` (larger = worse), with tail probability
    ``alpha`` (0.05 for 95% confidence).

    The objective is convex in ``z``; it is minimized over ``log z`` with a bounded
    Brent search after scaling the losses to unit maximum absolute value (EVaR is
    positively homogeneous, so ``EVaR(c X) = c EVaR(X)`` for ``c > 0``). The result
    lies between the Expected Shortfall and the maximum loss.
    """
    from scipy.optimize import minimize_scalar
    from scipy.special import logsumexp

    x = np.asarray(losses, dtype=np.float64)
    n = x.shape[0]
    if n == 0:
        raise ValueError("EVaR requires at least one observation")
    scale = float(np.max(np.abs(x)))
    if scale == 0.0:
        return 0.0
    if float(np.ptp(x)) == 0.0:
        return float(x[0])  # a constant loss has EVaR equal to that loss
    xs = x / scale
    log_n_alpha = math.log(n) + math.log(alpha)

    def objective(log_z: float) -> float:
        z = math.exp(log_z)
        return float(z * (logsumexp(xs / z) - log_n_alpha))

    result = minimize_scalar(
        objective, bounds=(-25.0, 12.0), method="bounded", options={"xatol": 1e-12}
    )
    # The infimum as z -> 0 is max(X); never report more than the worst loss.
    value = min(float(result.fun), float(np.max(xs)))
    return value * scale
