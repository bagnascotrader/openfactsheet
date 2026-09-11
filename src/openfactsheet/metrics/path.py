"""Canonical wealth-index and drawdown-episode engine (CLAUDE.md section 25).

Every drawdown metric consumes the objects produced here; no ratio rebuilds
drawdowns on its own. Conventions (decision 0007):

* ``wealth_0 = 1`` sits before the first return and counts as the first peak,
  so a loss in the very first period is a drawdown;
* ``drawdown_t = wealth_t / max_{s<=t} wealth_s - 1`` (signed, <= 0);
* an episode runs from the last peak before wealth falls below it to the first
  period in which wealth regains that peak (the recovery), or to the end of the
  history if it has not recovered (ongoing).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd


@dataclass(frozen=True)
class DrawdownEpisode:
    """One peak-to-recovery drawdown episode.

    Indices refer to the wealth index: ``0`` is inception (before the first
    return) and ``k`` is the wealth after the k-th return.
    """

    peak_index: int
    trough_index: int
    recovery_index: int | None
    depth: float
    peak_to_trough_periods: int
    recovery_periods: int | None
    total_underwater_periods: int
    duration_periods: int
    area: float
    peak_date: str | None
    trough_date: str | None
    recovery_date: str | None

    @property
    def recovered(self) -> bool:
        return self.recovery_index is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "peak_index": self.peak_index,
            "trough_index": self.trough_index,
            "recovery_index": self.recovery_index,
            "depth": self.depth,
            "peak_to_trough_periods": self.peak_to_trough_periods,
            "recovery_periods": self.recovery_periods,
            "total_underwater_periods": self.total_underwater_periods,
            "duration_periods": self.duration_periods,
            "area": self.area,
            "peak_date": self.peak_date,
            "trough_date": self.trough_date,
            "recovery_date": self.recovery_date,
            "recovered": self.recovered,
        }


def wealth_index(r: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Wealth path of length ``n + 1`` starting at 1 before the first return."""
    return np.concatenate(([1.0], np.cumprod(1.0 + r)))


def drawdown_path(wealth: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Signed drawdown for each wealth point (length ``n + 1``; first element is 0)."""
    peak = np.maximum.accumulate(wealth)
    return wealth / peak - 1.0


def _label(dates: pd.DatetimeIndex | None, wealth_idx: int) -> str | None:
    if dates is None or wealth_idx == 0:
        return None
    return dates[wealth_idx - 1].strftime("%Y-%m-%d")


def drawdown_episodes(
    dd_full: npt.NDArray[np.float64], dates: pd.DatetimeIndex | None
) -> tuple[DrawdownEpisode, ...]:
    """Split the drawdown path (including the inception point) into episodes."""
    n = dd_full.shape[0] - 1
    episodes: list[DrawdownEpisode] = []
    k = 1
    while k <= n:
        if dd_full[k] >= 0.0:
            k += 1
            continue
        peak = k - 1
        end = k
        while end <= n and dd_full[end] < 0.0:
            end += 1
        underwater = dd_full[k:end]
        trough = k + int(np.argmin(underwater))
        recovered = end <= n
        recovery = end if recovered else None
        episodes.append(
            DrawdownEpisode(
                peak_index=peak,
                trough_index=trough,
                recovery_index=recovery,
                depth=float(dd_full[trough]),
                peak_to_trough_periods=trough - peak,
                recovery_periods=(end - trough) if recovered else None,
                total_underwater_periods=end - k,
                duration_periods=(end - peak) if recovered else (n - peak),
                area=float(-np.sum(underwater)),
                peak_date=_label(dates, peak),
                trough_date=_label(dates, trough),
                recovery_date=_label(dates, end) if recovered else None,
            )
        )
        k = end
    return tuple(episodes)
