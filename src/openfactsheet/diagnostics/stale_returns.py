"""Stale-price indicators: exact zero returns and runs of identical returns."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


def zero_return_count(r: npt.NDArray[np.float64]) -> int:
    return int(np.sum(r == 0.0))


def longest_identical_run(r: npt.NDArray[np.float64]) -> int:
    """Length of the longest run of consecutive, exactly identical returns (1 if none repeat)."""
    if r.shape[0] == 0:
        return 0
    longest = current = 1
    for prev, cur in zip(r[:-1], r[1:], strict=True):
        current = current + 1 if cur == prev else 1
        longest = max(longest, current)
    return longest
