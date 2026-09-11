"""Metric context and shared-quantity cache (CLAUDE.md section 34)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import cached_property

import numpy as np
import numpy.typing as npt

from openfactsheet.compare.alignment import AlignedBenchmark
from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.path import (
    DrawdownEpisode,
    drawdown_episodes,
    drawdown_path,
    wealth_index,
)
from openfactsheet.models.assumptions import Methodology
from openfactsheet.models.diagnostics import DataQualityReport
from openfactsheet.models.input import ReturnSeries


class MetricCache:
    """Lazily computed quantities shared by many metrics."""

    def __init__(self, series: ReturnSeries) -> None:
        self._series = series
        self.r: npt.NDArray[np.float64] = series.values

    @cached_property
    def wealth(self) -> npt.NDArray[np.float64]:
        """Wealth index of length n + 1 (starts at 1 before the first return)."""
        return wealth_index(self.r)

    @cached_property
    def drawdown_full(self) -> npt.NDArray[np.float64]:
        """Drawdown path including the inception point (length n + 1)."""
        return drawdown_path(self.wealth)

    @cached_property
    def drawdown(self) -> npt.NDArray[np.float64]:
        """Drawdown after each observation (length n)."""
        return self.drawdown_full[1:]

    @cached_property
    def episodes(self) -> tuple[DrawdownEpisode, ...]:
        return drawdown_episodes(self.drawdown_full, self._series.dates)

    @cached_property
    def mean(self) -> float:
        return float(np.mean(self.r))

    @cached_property
    def std(self) -> float:
        """Sample standard deviation (ddof = 1)."""
        if self.r.shape[0] < 2:
            raise UndefinedMetric("Standard deviation requires at least 2 observations.")
        return float(np.std(self.r, ddof=1))

    @cached_property
    def downside_deviation(self) -> float:
        """Per-period downside deviation, MAR = 0, full-sample denominator."""
        shortfall = np.minimum(self.r, 0.0)
        return float(np.sqrt(np.mean(shortfall**2)))

    @cached_property
    def cumulative_return(self) -> float:
        return float(self.wealth[-1] - 1.0)

    @cached_property
    def max_drawdown(self) -> float:
        return float(np.min(self.drawdown_full))

    @cached_property
    def ulcer_index(self) -> float:
        return float(np.sqrt(np.mean(self.drawdown**2)))

    def central_moment(self, k: int) -> float:
        """Population central moment m_k = (1/n) sum (r_t - mean)^k."""
        return float(np.mean((self.r - self.mean) ** k))

    def _standardized_moment(self, k: int, what: str) -> float:
        """m_k / m_2^(k/2), undefined when the variance is zero or underflows.

        Returns that differ only at the level of floating-point underflow (e.g.
        ``[0, 0, 1e-198]``) have a variance that rounds to 0 or a ratio that
        overflows; such shape statistics are reported as undefined, never NaN.
        """
        m2 = self.central_moment(2)
        if m2 == 0.0:
            raise UndefinedMetric(f"Return variance is zero (numerically); {what} is undefined.")
        denominator = m2 ** (k / 2)
        value = self.central_moment(k) / denominator if denominator != 0.0 else math.inf
        if not math.isfinite(value):
            raise UndefinedMetric(
                f"Return variance is too small to compute {what} in floating point."
            )
        return float(value)

    @cached_property
    def population_skewness(self) -> float:
        """Moment skewness g1 = m3 / m2^(3/2) (population, not bias-corrected)."""
        return self._standardized_moment(3, "moment skewness")

    @cached_property
    def population_kurtosis(self) -> float:
        """Moment kurtosis m4 / m2^2 (population, non-excess: normal = 3)."""
        return self._standardized_moment(4, "moment kurtosis")

    @cached_property
    def lower_partial_moment_1(self) -> float:
        """LPM of order 1 at target 0: (1/n) sum max(-r_t, 0)."""
        return float(np.mean(np.maximum(-self.r, 0.0)))

    @cached_property
    def skewness(self) -> float:
        """Bias-corrected sample skewness G1."""
        if self.r.shape[0] < 3:
            raise UndefinedMetric("Skewness requires at least 3 observations.")
        self._standardized_moment(3, "skewness")  # raises if the variance underflows
        from scipy.stats import skew

        value = float(skew(self.r, bias=False))
        if not math.isfinite(value):
            raise UndefinedMetric(
                "Return variance is too small to compute skewness in floating point."
            )
        return value

    @cached_property
    def excess_kurtosis(self) -> float:
        """Bias-corrected sample excess kurtosis G2."""
        if self.r.shape[0] < 4:
            raise UndefinedMetric("Kurtosis requires at least 4 observations.")
        self._standardized_moment(4, "kurtosis")  # raises if the variance underflows
        from scipy.stats import kurtosis

        value = float(kurtosis(self.r, fisher=True, bias=False))
        if not math.isfinite(value):
            raise UndefinedMetric(
                "Return variance is too small to compute kurtosis in floating point."
            )
        return value


@dataclass(eq=False)
class MetricContext:
    """Everything a metric function may read. Metric functions must not mutate it."""

    returns: ReturnSeries
    diagnostics: DataQualityReport
    methodology: Methodology
    benchmark: AlignedBenchmark | None = None
    cache: MetricCache = field(init=False)

    def __post_init__(self) -> None:
        self.cache = MetricCache(self.returns)

    @property
    def r(self) -> npt.NDArray[np.float64]:
        return self.returns.values

    @property
    def n(self) -> int:
        return self.returns.n

    @property
    def ppy(self) -> float:
        """Periods per year; only called by metrics flagged ``annualized``."""
        ppy = self.returns.periods_per_year
        if ppy is None:  # pragma: no cover - guarded by the applicability engine
            raise UndefinedMetric("Annualization factor is not available.")
        return ppy

    @property
    def bench(self) -> AlignedBenchmark:
        if self.benchmark is None:  # pragma: no cover - guarded by the applicability engine
            raise UndefinedMetric("No benchmark supplied.")
        return self.benchmark

    @cached_property
    def cagr(self) -> float:
        """Geometric annualized return (requires a valid wealth path and a regular frequency)."""
        wealth_end = float(self.cache.wealth[-1])
        if wealth_end <= 0.0:
            return -1.0
        return float(wealth_end ** (self.ppy / self.n) - 1.0)
