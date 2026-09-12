"""Serial-dependence statistics shared by diagnostics and dependence metrics."""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt


def sample_autocorrelation(r: npt.NDArray[np.float64], lag: int) -> float | None:
    """Standard sample autocorrelation at ``lag`` (full-sample variance denominator).

    ``rho_k = sum_{t>k} (r_t - m)(r_{t-k} - m) / sum_t (r_t - m)^2``, the estimator
    used by statsmodels ``acf(adjusted=False)`` and R ``acf``. Returns ``None``
    when undefined (too few observations or zero variance).
    """
    n = r.shape[0]
    if n <= lag + 1:
        return None
    from statsmodels.tsa.stattools import acf

    if float(np.ptp(r)) == 0.0:
        return None
    values = acf(r, nlags=lag, fft=False, adjusted=False, missing="none")
    rho = float(values[lag])
    return rho if math.isfinite(rho) else None


def autocorrelations(r: npt.NDArray[np.float64], max_lag: int) -> npt.NDArray[np.float64] | None:
    """Sample autocorrelations ``rho_1 .. rho_max_lag`` (same estimator as above)."""
    n = r.shape[0]
    if max_lag < 1 or n <= max_lag + 1 or float(np.ptp(r)) == 0.0:
        return None
    from statsmodels.tsa.stattools import acf

    values = np.asarray(
        acf(r, nlags=max_lag, fft=False, adjusted=False, missing="none"), dtype=np.float64
    )[1:]
    return values if bool(np.all(np.isfinite(values))) else None


def variance_ratio(rho: npt.NDArray[np.float64], q: int) -> float:
    """Variance ratio at horizon ``q`` from autocorrelations ``rho_1 .. rho_{q-1}``.

    ``VR(q) = 1 + 2 sum_{k=1}^{q-1} (1 - k/q) rho_k`` (Lo & MacKinlay 1988): the variance
    of q-period sums relative to q times the one-period variance; 1 without serial
    correlation.
    """
    k = np.arange(1, q, dtype=np.float64)
    return float(1.0 + 2.0 * np.sum((1.0 - k / q) * rho[: q - 1]))


def variance_ratio_standard_error(n: int, q: int) -> float:
    """Asymptotic i.i.d. standard error ``sqrt(2 (2q - 1)(q - 1) / (3 q n))``."""
    return math.sqrt(2.0 * (2 * q - 1) * (q - 1) / (3.0 * q * n))


def ljung_box(r: npt.NDArray[np.float64], lags: int) -> tuple[float, float] | None:
    """Ljung-Box Q statistic and p-value for ``lags`` lags (statsmodels)."""
    if r.shape[0] <= lags + 1 or float(np.ptp(r)) == 0.0:
        return None
    from statsmodels.stats.diagnostic import acorr_ljungbox

    table = acorr_ljungbox(r, lags=[lags], return_df=True)
    stat = float(table["lb_stat"].iloc[0])
    pvalue = float(table["lb_pvalue"].iloc[0])
    if not (math.isfinite(stat) and math.isfinite(pvalue)):
        return None
    return stat, pvalue
