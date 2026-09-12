"""Factor-model data structures (decision 0028).

Factor returns are always supplied by the caller; OpenFactsheet never downloads
them. A :class:`FactorSet` holds the normalized factor columns, a
:class:`FactorModelFit` the regression of the fund on them.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from openfactsheet.models.input import InputDiagnostics, ReturnSeries


@dataclass(frozen=True, eq=False)
class FactorSet:
    """Normalized factor returns (simple decimal) plus an optional risk-free column.

    Every column is a :class:`ReturnSeries` with its own dates; periods where any
    column is missing are dropped at alignment, never filled.
    """

    factors: Mapping[str, ReturnSeries]
    risk_free: ReturnSeries | None
    source_type: str
    return_scale: str
    return_scale_evidence: str
    input_diagnostics: Mapping[str, InputDiagnostics] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "factors", MappingProxyType(dict(self.factors)))
        object.__setattr__(
            self, "input_diagnostics", MappingProxyType(dict(self.input_diagnostics))
        )

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self.factors)

    @property
    def k(self) -> int:
        return len(self.factors)


# Canonical labels for well-known factor sets, recognized from column names only.
# The label is descriptive: it never changes how the regression is estimated.
_ALIASES: Mapping[str, str] = MappingProxyType(
    {
        "MKTRF": "MKT",
        "MKT": "MKT",
        "MARKET": "MKT",
        "MKTEXCESS": "MKT",
        "RMRF": "MKT",
        "SMB": "SMB",
        "HML": "HML",
        "RMW": "RMW",
        "CMA": "CMA",
        "MOM": "MOM",
        "UMD": "MOM",
        "WML": "MOM",
    }
)
_KNOWN_MODELS: tuple[tuple[frozenset[str], str], ...] = (
    (frozenset({"MKT"}), "CAPM (single market factor)"),
    (frozenset({"MKT", "SMB", "HML"}), "Fama-French three-factor model"),
    (frozenset({"MKT", "SMB", "HML", "MOM"}), "Carhart four-factor model"),
    (frozenset({"MKT", "SMB", "HML", "RMW", "CMA"}), "Fama-French five-factor model"),
    (
        frozenset({"MKT", "SMB", "HML", "RMW", "CMA", "MOM"}),
        "Fama-French five-factor model with momentum",
    ),
)


def _canonical_name(column: str) -> str:
    return re.sub(r"[^A-Z]", "", column.upper())


def recognize_model(names: tuple[str, ...]) -> str:
    """Descriptive label for a factor set, e.g. ``"Fama-French three-factor model"``."""
    canon = [_ALIASES.get(_canonical_name(n)) for n in names]
    if all(c is not None for c in canon) and len(set(canon)) == len(canon):
        key = frozenset(c for c in canon if c is not None)
        for members, label in _KNOWN_MODELS:
            if key == members:
                return label
    return f"Custom factor model ({len(names)} factor{'s' if len(names) != 1 else ''})"


def is_risk_free_column(name: str) -> bool:
    """A column named ``RF`` (any case, surrounding spaces ignored) is the risk-free rate."""
    return name.strip().upper() == "RF"


@dataclass(frozen=True)
class FactorAlignment:
    """How fund and factor returns were aligned (overlap is always disclosed)."""

    fund_observations: int
    factor_observations: int  # periods where every factor (and RF, if any) has a value
    aligned_observations: int
    fund_only_periods: int
    overlap_start: str | None
    overlap_end: str | None
    alignment_method: str
    warnings: tuple[str, ...] = ()

    @property
    def fund_coverage(self) -> float:
        if self.fund_observations == 0:
            return 0.0
        return self.aligned_observations / self.fund_observations

    def to_dict(self) -> dict[str, Any]:
        return {
            "fund_observations": self.fund_observations,
            "factor_observations": self.factor_observations,
            "aligned_observations": self.aligned_observations,
            "fund_only_periods": self.fund_only_periods,
            "fund_coverage": self.fund_coverage,
            "overlap_start": self.overlap_start,
            "overlap_end": self.overlap_end,
            "alignment_method": self.alignment_method,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class Coefficient:
    """One regression coefficient with HAC inference (decision 0028)."""

    name: str
    estimate: float
    standard_error: float | None
    t_statistic: float | None
    p_value: float | None
    ci_lower: float | None
    ci_upper: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "estimate": self.estimate,
            "standard_error": self.standard_error,
            "t_statistic": self.t_statistic,
            "p_value": self.p_value,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
        }


@dataclass(frozen=True)
class FactorModelFit:
    """OLS regression of fund (excess) returns on supplied factor returns.

    ``alpha`` is per period; ``loadings`` are in factor order. Inference uses the
    heteroskedasticity- and autocorrelation-consistent (Newey-West) covariance with
    ``hac_lags`` lags and Student-t reference distribution with ``df_resid``
    degrees of freedom. ``None`` marks a statistic that is undefined for the data
    (e.g. a t-statistic when residuals are exactly zero).
    """

    model: str
    factor_names: tuple[str, ...]
    dependent: str
    n: int
    k: int
    df_resid: int
    hac_lags: int
    ci_level: float
    alpha: Coefficient
    loadings: tuple[Coefficient, ...]
    r_squared: float | None
    adj_r_squared: float | None
    residual_std: float  # per period, df_resid denominator
    residual_autocorrelation_lag1: float | None
    residual_ljung_box_pvalue: float | None
    max_vif: float | None
    periods_per_year: float | None
    alignment: FactorAlignment
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "factor_names": list(self.factor_names),
            "dependent": self.dependent,
            "observations": self.n,
            "factors": self.k,
            "df_resid": self.df_resid,
            "hac_lags": self.hac_lags,
            "ci_level": self.ci_level,
            "alpha_per_period": self.alpha.to_dict(),
            "loadings": [c.to_dict() for c in self.loadings],
            "r_squared": self.r_squared,
            "adj_r_squared": self.adj_r_squared,
            "residual_std_per_period": self.residual_std,
            "residual_autocorrelation_lag1": self.residual_autocorrelation_lag1,
            "residual_ljung_box_pvalue": self.residual_ljung_box_pvalue,
            "max_vif": self.max_vif,
            "periods_per_year": self.periods_per_year,
            "alignment": self.alignment.to_dict(),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class FactorAnalysis:
    """Section 11 of the canonical report: the fit, or the reason there is none."""

    model: str
    factor_names: tuple[str, ...]
    dependent: str
    return_scale: str
    return_scale_evidence: str
    alignment: FactorAlignment
    fit: FactorModelFit | None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "factor_names": list(self.factor_names),
            "dependent": self.dependent,
            "return_scale": self.return_scale,
            "return_scale_evidence": self.return_scale_evidence,
            "alignment": self.alignment.to_dict(),
            "fit": self.fit.to_dict() if self.fit is not None else None,
            "reason": self.reason,
        }

    def to_text(self) -> str:
        a = self.alignment
        lines = [
            f"Model:                     {self.model}",
            f"Factors:                   {', '.join(self.factor_names)}",
            f"Dependent variable:        {self.dependent}",
            f"Factor return scale:       {self.return_scale.replace('_', ' ')}",
            f"Alignment:                 {a.alignment_method}",
            f"Aligned observations:      {a.aligned_observations} "
            f"({a.fund_coverage:.0%} of fund history)",
            f"Fund-only periods dropped: {a.fund_only_periods}",
            f"Overlap:                   {a.overlap_start or 'n/a'} to {a.overlap_end or 'n/a'}",
        ]
        if self.fit is not None:
            f = self.fit
            lines.append(
                f"Estimation:                OLS; Newey-West (HAC) standard errors with "
                f"{f.hac_lags} lag(s); t with {f.df_resid} df"
            )
        lines.extend(f"  - {w}" for w in a.warnings)
        if self.fit is not None:
            lines.extend(f"  - {w}" for w in self.fit.warnings)
        if self.reason:
            lines.append(f"Not estimated:             {self.reason}")
        return "\n".join(lines)
