"""Factor regression vs R lm + sandwich::NeweyWest + lmtest::coeftest (decision 0028).

Reference values: tests/fixtures/reference/factor_models.json, produced by
validation/r/factor_reference.R (R is not needed to run this test).
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pytest

import openfactsheet as ofs
from tests.conftest import FIXTURES, REFERENCE, fixture_series

pytestmark = pytest.mark.cross_library


@pytest.fixture(scope="module")
def reference() -> dict[str, Any]:
    return json.loads((REFERENCE / "factor_models.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _factors(columns: list[str]) -> pd.DataFrame:
    frame = pd.read_csv(FIXTURES / "factor_case_factors.csv")
    return frame[["date", *columns]]


@pytest.mark.parametrize(
    ("case", "columns"),
    [("ff3", ["Mkt-RF", "SMB", "HML", "RF"]), ("capm", ["Mkt-RF", "RF"])],
)
def test_factor_regression_matches_r(
    reference: dict[str, Any], case: str, columns: list[str]
) -> None:
    ref = reference[case]
    report = ofs.analyze(fixture_series("factor_case_fund"), factors=_factors(columns))
    fa = report.factor_analysis
    assert fa is not None
    fit = fa.fit
    assert fit is not None
    assert fit.n == ref["observations"]
    assert fit.hac_lags == ref["hac_lags"]
    coefs = [fit.alpha, *fit.loadings]
    for i, c in enumerate(coefs):
        assert c.estimate == pytest.approx(ref["estimate"][i], rel=1e-9, abs=1e-12)
        assert c.standard_error == pytest.approx(ref["std_error"][i], rel=1e-8)
        assert c.t_statistic == pytest.approx(ref["t"][i], rel=1e-8)
        assert c.p_value == pytest.approx(ref["p"][i], rel=1e-6, abs=1e-12)
        assert c.ci_lower == pytest.approx(ref["ci_lower"][i], rel=1e-8, abs=1e-12)
        assert c.ci_upper == pytest.approx(ref["ci_upper"][i], rel=1e-8, abs=1e-12)
    assert fit.r_squared == pytest.approx(ref["r_squared"], rel=1e-10)
    assert fit.adj_r_squared == pytest.approx(ref["adj_r_squared"], rel=1e-10)
    assert fit.residual_std == pytest.approx(ref["sigma"], rel=1e-10)

    m = report.metrics
    assert m["factor_alpha"].value == pytest.approx(12 * ref["estimate"][0], rel=1e-9)
    assert m["factor_alpha_t_statistic"].value == pytest.approx(ref["t"][0], rel=1e-8)
    assert m["factor_r_squared"].value == pytest.approx(ref["r_squared"], rel=1e-10)
    assert m["factor_residual_volatility"].value == pytest.approx(ref["sigma"] * 12**0.5, rel=1e-10)
