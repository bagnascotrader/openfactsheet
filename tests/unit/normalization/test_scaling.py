from __future__ import annotations

import numpy as np
import pytest

from openfactsheet.exceptions import AmbiguousReturnScaleError, InputError
from openfactsheet.models.input import ObservationFrequency as F
from openfactsheet.normalization.scaling import detect_return_scale


def arr(*xs: float) -> np.ndarray:
    return np.asarray(xs, dtype=np.float64)


def test_decimal_monthly_detected() -> None:
    d = detect_return_scale(arr(0.01, -0.02, 0.015, 0.005, -0.01, 0.03), F.MONTHLY)
    assert d.scale == "detected_decimal"
    assert d.factor == 1.0


def test_percent_detected_from_magnitude() -> None:
    d = detect_return_scale(arr(1.5, -0.8, 2.1), F.UNKNOWN)
    assert d.scale == "detected_percent"
    assert d.factor == 0.01


def test_percent_label_is_strong_evidence() -> None:
    d = detect_return_scale(arr(0.01, 0.02), F.MONTHLY, percent_hint=True)
    assert d.scale == "detected_percent"


def test_declared_scale_wins() -> None:
    d = detect_return_scale(arr(1.5, 2.0), F.MONTHLY, declared="decimal")
    assert d.scale == "declared_decimal"
    assert detect_return_scale(arr(0.1), F.MONTHLY, declared="percent").factor == 0.01


def test_invalid_declared_scale() -> None:
    with pytest.raises(InputError):
        detect_return_scale(arr(0.1), F.MONTHLY, declared="basis_points")  # type: ignore[arg-type]


def test_ambiguous_zone_refuses_to_guess() -> None:
    # Median |r| of 0.1 per month: 10% (volatile) or 0.1% (cash-like) are both plausible.
    with pytest.raises(AmbiguousReturnScaleError, match="return_scale"):
        detect_return_scale(arr(0.1, -0.08, 0.12, 0.09, -0.11), F.MONTHLY)


def test_ambiguous_zone_with_impossible_decimal_is_percent() -> None:
    d = detect_return_scale(arr(0.1, -1.2, 0.12, 0.09, -0.11), F.MONTHLY)
    assert d.scale == "detected_percent"


def test_small_decimals_with_impossible_value_stay_decimal() -> None:
    d = detect_return_scale(arr(0.01, -0.02, 0.015, -1.5, 0.004), F.MONTHLY)
    assert d.scale == "detected_decimal"
    assert "impossible" in d.evidence


def test_price_levels_are_rejected() -> None:
    with pytest.raises(InputError, match="price or NAV"):
        detect_return_scale(arr(100.0, 101.2, 99.8, 102.5), F.MONTHLY)


def test_all_zero_is_decimal() -> None:
    assert detect_return_scale(arr(0.0, 0.0), F.MONTHLY).scale == "detected_decimal"


def test_daily_bounds_are_tighter() -> None:
    d = detect_return_scale(arr(0.6, -0.4, 1.1, -0.9), F.DAILY)
    assert d.scale == "detected_percent"
