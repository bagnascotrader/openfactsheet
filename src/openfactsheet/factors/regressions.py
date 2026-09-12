"""Fund/factor alignment and the canonical factor regression (decision 0028).

``y_t = alpha + sum_j b_j f_{j,t} + e_t`` by ordinary least squares (statsmodels),
where ``y_t`` is the fund return minus the supplied risk-free rate (or the fund
return when no ``RF`` column was supplied). Inference uses the Newey-West (HAC)
covariance with the lag ``floor(4 (m / 100)^(2/9))``, the small-sample factor
``m / (m - k - 1)`` and Student-t with ``m - k - 1`` degrees of freedom. The lag
rule is fixed by the methodology, never chosen per fund.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cached_property

import numpy as np
import numpy.typing as npt
import pandas as pd

from openfactsheet.compare.alignment import PERIOD_CODES, period_keys
from openfactsheet.exceptions import FactorAlignmentError, UndefinedMetric
from openfactsheet.factors.models import (
    Coefficient,
    FactorAlignment,
    FactorModelFit,
    FactorSet,
    recognize_model,
)
from openfactsheet.models.assumptions import Methodology
from openfactsheet.models.input import ReturnSeries


def _fmt(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%d")


def _finite_or_none(x: float) -> float | None:
    return float(x) if math.isfinite(float(x)) else None


def hac_lags(m: int) -> int:
    """Newey-West (1994) rule-of-thumb lag ``floor(4 (m / 100)^(2/9))``."""
    return math.floor(4.0 * (m / 100.0) ** (2.0 / 9.0)) if m > 0 else 0


@dataclass(frozen=True, eq=False)
class AlignedFactors:
    """Fund and factor returns on their common periods (never filled)."""

    fund: npt.NDArray[np.float64]
    risk_free: npt.NDArray[np.float64] | None
    x: npt.NDArray[np.float64]  # m x k factor returns
    names: tuple[str, ...]
    dates: pd.DatetimeIndex | None
    alignment: FactorAlignment
    periods_per_year: float | None
    methodology: Methodology

    @property
    def n(self) -> int:
        return int(self.fund.shape[0])

    @property
    def k(self) -> int:
        return len(self.names)

    @property
    def model(self) -> str:
        return recognize_model(self.names)

    @property
    def dependent(self) -> str:
        if self.risk_free is not None:
            return "fund return minus the supplied risk-free rate (RF)"
        return "fund return (no RF column supplied: risk-free rate 0%)"

    @cached_property
    def y(self) -> npt.NDArray[np.float64]:
        return self.fund - self.risk_free if self.risk_free is not None else self.fund

    @cached_property
    def fit(self) -> FactorModelFit:
        return fit_factor_model(self)


def align_factors(
    fund: ReturnSeries, factor_set: FactorSet, methodology: Methodology
) -> AlignedFactors:
    """Intersect the fund's periods with the periods where every factor has a value."""
    columns: dict[str, ReturnSeries] = dict(factor_set.factors)
    if factor_set.risk_free is not None:
        columns["RF"] = factor_set.risk_free
    warnings: list[str] = []
    dated = [s.dates is not None for s in columns.values()]
    if any(dated) and not all(dated):
        raise FactorAlignmentError("Some factor columns are dated and others are not.")
    factors_dated = all(dated)

    if fund.dates is not None and factors_dated:
        f_freq = fund.frequency
        c_freq = next(iter(columns.values())).frequency
        if f_freq.is_regular and c_freq.is_regular and f_freq != c_freq:
            raise FactorAlignmentError(
                f"Fund is {f_freq.value} but the factor returns are {c_freq.value}. OpenFactsheet "
                "does not resample returns; supply factor returns at the fund's frequency."
            )
        period_freq = f_freq if f_freq in PERIOD_CODES else c_freq
        code = PERIOD_CODES.get(period_freq)
        fund_keys = period_keys(fund, code)
        col_keys = {name: period_keys(s, code) for name, s in columns.items()}
        if fund_keys.has_duplicates or any(k.has_duplicates for k in col_keys.values()):
            raise FactorAlignmentError(
                "Several observations fall in the same calendar period; they cannot be aligned "
                "by period without choosing between them."
            )
        factor_common = None
        for keys in col_keys.values():
            factor_common = keys if factor_common is None else factor_common.intersection(keys)
        assert factor_common is not None
        factor_obs = len(factor_common)
        common = fund_keys.intersection(factor_common)
        f_pos = np.sort(fund_keys.get_indexer(common))
        common = fund_keys[f_pos]
        data = {name: s.values[col_keys[name].get_indexer(common)] for name, s in columns.items()}
        dates: pd.DatetimeIndex | None = pd.DatetimeIndex(fund.dates[f_pos])
        method = f"calendar {period_freq.value} period" if code is not None else "exact date"
        fund_vals = fund.values[f_pos]
    else:
        lengths = {s.n for s in columns.values()}
        if len(lengths) != 1 or next(iter(lengths)) != fund.n:
            raise FactorAlignmentError(
                "Fund and factor returns cannot be aligned by date (at least one side is "
                "undated) and their lengths differ; supply dates for both."
            )
        factor_obs = fund.n
        data = {name: s.values for name, s in columns.items()}
        fund_vals = fund.values
        if fund.dates is None and not factors_dated:
            dates = None
            method = "by position (fund and factors undated)"
            warnings.append(
                "Neither the fund nor the factors have dates; observations were paired by "
                "position. Verify that both cover exactly the same periods."
            )
        else:
            dates = fund.dates if fund.dates is not None else next(iter(columns.values())).dates
            undated = "factor returns" if fund.dates is not None else "fund"
            method = f"by position ({undated} undated; assumed to share the other side's dates)"
            warnings.append(
                f"The {undated} have no dates; they were assumed to cover the same periods."
            )

    m = int(fund_vals.shape[0])
    if m < fund.n:
        warnings.append(
            f"{fund.n - m} fund observation(s) have no matching return for every factor and are "
            "excluded from the factor regression (never filled)."
        )
    if m == 0:
        warnings.append("Fund and factor returns have no periods in common.")
    alignment = FactorAlignment(
        fund_observations=fund.n,
        factor_observations=factor_obs,
        aligned_observations=m,
        fund_only_periods=fund.n - m,
        overlap_start=_fmt(dates[0]) if dates is not None and m else None,
        overlap_end=_fmt(dates[-1]) if dates is not None and m else None,
        alignment_method=method,
        warnings=tuple(warnings),
    )
    names = tuple(factor_set.factors)
    x = (
        np.column_stack([np.asarray(data[n], dtype=np.float64) for n in names])
        if m
        else np.empty((0, len(names)))
    )
    rf = np.asarray(data["RF"], dtype=np.float64) if "RF" in data else None
    return AlignedFactors(
        fund=np.asarray(fund_vals, dtype=np.float64),
        risk_free=rf,
        x=x,
        names=names,
        dates=dates,
        alignment=alignment,
        periods_per_year=fund.periods_per_year,
        methodology=methodology,
    )


def _residual_acf1(e: npt.NDArray[np.float64]) -> float | None:
    d = e - e.mean()
    denom = float(np.dot(d, d))
    if e.shape[0] < 3 or denom <= 0.0:
        return None
    return float(np.dot(d[1:], d[:-1]) / denom)


def _max_vif(x: npt.NDArray[np.float64]) -> float | None:
    """Largest variance inflation factor, ``diag(inv(corr(X)))`` (with an intercept)."""
    if x.shape[1] < 2:
        return None
    corr = np.corrcoef(x, rowvar=False)
    try:
        inv = np.linalg.inv(corr)
    except np.linalg.LinAlgError:
        return None
    vif = float(np.max(np.diag(inv)))
    return vif if math.isfinite(vif) else None


def fit_factor_model(af: AlignedFactors) -> FactorModelFit:
    """Estimate the factor regression; raise :class:`UndefinedMetric` when it is not identified."""
    m, k = af.n, af.k
    conv = af.methodology.get("factor_model")
    level = float(conv["ci_level"])
    if m < k + 2:
        raise UndefinedMetric(
            f"At least {k + 2} aligned observations are required to estimate {k + 1} "
            f"coefficients with one residual degree of freedom; {m} available."
        )
    for j, name in enumerate(af.names):
        if float(np.ptp(af.x[:, j])) == 0.0:
            raise UndefinedMetric(
                f"Factor {name!r} is constant over the aligned periods; its loading is not "
                "identified."
            )
    design = np.column_stack([np.ones(m), af.x])
    if int(np.linalg.matrix_rank(design)) < k + 1:
        raise UndefinedMetric(
            "The factor returns are perfectly collinear over the aligned periods; the loadings "
            "are not identified."
        )
    y = af.y
    lags = hac_lags(m)
    df_resid = m - k - 1
    names = ("alpha", *af.names)
    warnings: list[str] = []

    exact_note: str | None = None
    est: list[float] = []
    if float(np.ptp(y)) == 0.0:
        # Exact solution: a constant dependent variable has zero loadings, an intercept
        # equal to its value and zero residuals (t-statistics are 0/0).
        est = [float(y[0])] + [0.0] * k
        exact_note = "The dependent variable is constant: there is no variance to explain."
    else:
        beta, *_ = np.linalg.lstsq(design, y, rcond=None)
        resid0 = y - design @ beta
        tol = m * (16.0 * np.finfo(np.float64).eps * float(np.max(np.abs(y)))) ** 2
        if float(np.dot(resid0, resid0)) <= tol:
            # The factors reproduce the fund exactly (e.g. the fund *is* a factor):
            # residuals are rounding noise, so standard errors and t-statistics would be
            # meaningless (t ~ 1e15). Report the exact fit instead.
            est = [float(b) for b in beta]
            exact_note = (
                "The factors reproduce the dependent variable exactly (residuals below "
                "floating-point resolution); standard errors and t-statistics are undefined."
            )
    if exact_note is not None:
        coefs = [Coefficient(n, e, 0.0, None, None, e, e) for n, e in zip(names, est, strict=True)]
        constant = float(np.ptp(y)) == 0.0
        return FactorModelFit(
            model=af.model,
            factor_names=af.names,
            dependent=af.dependent,
            n=m,
            k=k,
            df_resid=df_resid,
            hac_lags=lags,
            ci_level=level,
            alpha=coefs[0],
            loadings=tuple(coefs[1:]),
            r_squared=None if constant else 1.0,
            adj_r_squared=None if constant else 1.0,
            residual_std=0.0,
            residual_autocorrelation_lag1=None,
            residual_ljung_box_pvalue=None,
            max_vif=_max_vif(af.x),
            periods_per_year=af.periods_per_year,
            alignment=af.alignment,
            warnings=(exact_note,),
        )

    import statsmodels.api as sm
    from statsmodels.stats.diagnostic import acorr_ljungbox

    result = sm.OLS(y, design).fit(
        cov_type="HAC",
        cov_kwds={"maxlags": lags, "use_correction": True},
        use_t=True,
    )
    params = np.asarray(result.params, dtype=np.float64)
    bse = np.asarray(result.bse, dtype=np.float64)
    tvals = np.asarray(result.tvalues, dtype=np.float64)
    pvals = np.asarray(result.pvalues, dtype=np.float64)
    ci = np.asarray(result.conf_int(alpha=1.0 - level), dtype=np.float64)
    coefs = [
        Coefficient(
            name=names[i],
            estimate=float(params[i]),
            standard_error=_finite_or_none(bse[i]),
            t_statistic=_finite_or_none(tvals[i]),
            p_value=_finite_or_none(pvals[i]),
            ci_lower=_finite_or_none(ci[i, 0]),
            ci_upper=_finite_or_none(ci[i, 1]),
        )
        for i in range(k + 1)
    ]
    resid = np.asarray(result.resid, dtype=np.float64)
    ssr = float(np.dot(resid, resid))
    residual_std = math.sqrt(ssr / df_resid)
    acf1 = _residual_acf1(resid)
    lb_lags = int(af.methodology.get("dependence.ljung_box_lags"))
    lb_p: float | None = None
    if m >= int(conv["ljung_box_min_observations"]) and ssr > 0.0:
        lb = acorr_ljungbox(resid, lags=[lb_lags], return_df=True)
        lb_p = _finite_or_none(float(lb["lb_pvalue"].iloc[0]))
    vif = _max_vif(af.x)
    if vif is not None and vif >= float(conv["vif_warning"]):
        warnings.append(
            f"The factors are strongly collinear (maximum variance inflation factor {vif:.1f}): "
            "individual loadings are imprecise; alpha and R-squared are not affected."
        )
    if lb_p is not None and lb_p < 0.05:
        warnings.append(
            f"Regression residuals are serially correlated (Ljung-Box p = {lb_p:.3f}); "
            "Newey-West standard errors allow for this, but smoothed returns also bias "
            "loadings toward zero and alpha upward."
        )
    r2 = _finite_or_none(float(result.rsquared))
    adj = _finite_or_none(float(result.rsquared_adj))
    return FactorModelFit(
        model=af.model,
        factor_names=af.names,
        dependent=af.dependent,
        n=m,
        k=k,
        df_resid=df_resid,
        hac_lags=lags,
        ci_level=level,
        alpha=coefs[0],
        loadings=tuple(coefs[1:]),
        r_squared=r2,
        adj_r_squared=adj,
        residual_std=residual_std,
        residual_autocorrelation_lag1=acf1,
        residual_ljung_box_pvalue=lb_p,
        max_vif=vif,
        periods_per_year=af.periods_per_year,
        alignment=af.alignment,
        warnings=tuple(warnings),
    )
