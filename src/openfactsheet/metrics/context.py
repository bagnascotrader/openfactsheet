"""Metric context and shared-quantity cache (CLAUDE.md section 34)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import cached_property

import numpy as np
import numpy.typing as npt

from openfactsheet.compare.alignment import AlignedBenchmark
from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.factors.regressions import AlignedFactors
from openfactsheet.metrics.path import (
    DrawdownEpisode,
    drawdown_episodes,
    drawdown_path,
    wealth_index,
)
from openfactsheet.models.assumptions import Methodology
from openfactsheet.models.diagnostics import DataQualityReport
from openfactsheet.models.input import ReturnSeries


@dataclass(frozen=True, eq=False)
class OneYearDependence:
    """Serial correlation up to the one-year horizon ``q = round(P)`` (decision 0029)."""

    q: int
    rho: npt.NDArray[np.float64]  # rho_1 .. rho_{q-1}
    variance_ratio: float
    standard_error: float  # asymptotic i.i.d. standard error of the variance ratio


@dataclass(frozen=True)
class CalendarYears:
    complete: dict[int, float]  # year -> compounded return of a complete calendar year
    partial: dict[int, str]  # year -> why it is incomplete (excluded)


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
    def gini_mean_difference(self) -> float:
        """Gini mean difference: mean of |r_i - r_j| over the n(n-1) ordered pairs i != j.

        Computed in O(n log n) from the sorted returns. Summing by parts,
        sum_k (2k - n - 1) r_(k) = sum_{k=1}^{n-1} k (n - k) (r_(k+1) - r_(k)), a sum of
        non-negative terms that is exactly zero for identical returns.
        """
        n = self.r.shape[0]
        if n < 2:
            raise UndefinedMetric("The mean difference requires at least 2 observations.")
        gaps = np.diff(np.sort(self.r))
        k = np.arange(1, n, dtype=np.float64)
        pair_sum = float(np.sum(k * (n - k) * gaps))  # = sum_{i<j} |r_i - r_j|
        return float(2.0 * pair_sum / (n * (n - 1)))

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
        # Identical returns, or a variance below floating-point resolution relative to the
        # size of the returns (e.g. [0.01] * 8, whose computed mean is inexact), carry no
        # shape information: the moment ratio would be pure rounding noise.
        resolution = (np.finfo(np.float64).eps * float(np.max(np.abs(self.r)))) ** 2 * 16.0
        if float(np.ptp(self.r)) == 0.0 or m2 <= resolution:
            raise UndefinedMetric(f"Returns are (numerically) constant; {what} is undefined.")
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
    factors: AlignedFactors | None = None
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

    @property
    def fac(self) -> AlignedFactors:
        if self.factors is None:  # pragma: no cover - guarded by the applicability engine
            raise UndefinedMetric("No factor returns supplied.")
        return self.factors

    @cached_property
    def calendar_years(self) -> CalendarYears:
        """Compounded returns of complete calendar years (decision 0023).

        A year is complete when the observations cover it: all 12 months (monthly),
        all 4 quarters (quarterly), its single observation (yearly), or, for daily and
        weekly data, a first observation within the tolerance of 1 January and a last
        observation within the tolerance of 31 December. Partial years are reported
        separately and never enter calendar-year statistics.
        """
        from openfactsheet.models.input import ObservationFrequency as F

        dates = self.returns.dates
        freq = self.returns.frequency
        if dates is None:
            raise UndefinedMetric("Calendar-year statistics require dated returns.")
        if not freq.is_regular:
            raise UndefinedMetric(
                f"Calendar-year statistics require a regular frequency; this series is "
                f"{freq.value}."
            )
        import pandas as pd

        tol = int(self.methodology.get("calendar_years.daily_weekly_edge_tolerance_days"))
        years = np.asarray(dates.year)
        complete: dict[int, float] = {}
        partial: dict[int, str] = {}
        for year in sorted(set(years.tolist())):
            mask = years == year
            dy = dates[mask]
            if freq is F.MONTHLY:
                ok = len(set(dy.month.tolist())) == 12
                why = f"{len(dy)} of 12 months"
            elif freq is F.QUARTERLY:
                ok = len(set(dy.quarter.tolist())) == 4
                why = f"{len(dy)} of 4 quarters"
            elif freq is F.YEARLY:
                ok, why = True, ""
            else:
                start_ok = dy.min() <= pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(
                    days=tol
                )
                end_ok = dy.max() >= pd.Timestamp(year=year, month=12, day=31) - pd.Timedelta(
                    days=tol
                )
                ok = bool(start_ok and end_ok)
                why = f"observations from {dy.min():%Y-%m-%d} to {dy.max():%Y-%m-%d}"
            if ok:
                complete[year] = float(np.prod(1.0 + self.r[mask]) - 1.0)
            else:
                partial[year] = why
        return CalendarYears(complete=complete, partial=partial)

    @cached_property
    def rolling_year_returns(self) -> tuple[npt.NDArray[np.float64], int]:
        """Compounded returns of every window of one year of consecutive observations."""
        window = round(self.ppy * float(self.methodology.get("rolling.window_years")))
        if self.n < window:
            raise UndefinedMetric(
                f"Fewer observations ({self.n}) than one year ({window}): no complete rolling "
                "one-year window."
            )
        windows = np.lib.stride_tricks.sliding_window_view(self.r, window)
        return np.prod(1.0 + windows, axis=1) - 1.0, window

    @cached_property
    def one_year_dependence(self) -> OneYearDependence:
        """Autocorrelations up to the one-year horizon and the variance ratio (decision 0029)."""
        from openfactsheet.diagnostics.autocorrelation import (
            autocorrelations,
            variance_ratio,
            variance_ratio_standard_error,
        )

        ppy = self.returns.periods_per_year
        if ppy is None:
            raise UndefinedMetric(
                "The one-year horizon requires a regular observation frequency; the frequency "
                f"of this series is {self.returns.frequency.value}."
            )
        conv = self.methodology.get("serial_correlation")
        q = round(ppy * float(conv["horizon_years"]))
        if q < 2:
            raise UndefinedMetric(
                "With one observation per year the one-year horizon is a single period; there is "
                "no within-year serial correlation to measure."
            )
        needed = int(conv["min_years"]) * q
        if self.n < needed:
            raise UndefinedMetric(
                f"At least {needed} observations ({conv['min_years']} years) are needed to "
                f"estimate the {q - 1} autocorrelations of a one-year horizon; {self.n} available."
            )
        rho = autocorrelations(self.r, q - 1)
        if rho is None:
            raise UndefinedMetric("Autocorrelations are undefined (constant returns).")
        return OneYearDependence(
            q=q,
            rho=rho,
            variance_ratio=variance_ratio(rho, q),
            standard_error=variance_ratio_standard_error(self.n, q),
        )

    @cached_property
    def cagr(self) -> float:
        """Geometric annualized return (requires a valid wealth path and a regular frequency)."""
        wealth_end = float(self.cache.wealth[-1])
        if wealth_end <= 0.0:
            return -1.0
        return float(wealth_end ** (self.ppy / self.n) - 1.0)
