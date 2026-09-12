"""Canonical assumptions registry (CLAUDE.md section 22).

This module is the single machine-readable source of every canonical
convention. Rationale for each entry lives in ``docs/methodology/decisions``.
Nothing here may be tuned per fund; changes require a methodology version bump.
"""

from __future__ import annotations

from functools import cache
from typing import Any

from openfactsheet.models.assumptions import Methodology
from openfactsheet.policy.methodology_version import METHODOLOGY_VERSION

CANONICAL_ASSUMPTIONS: dict[str, Any] = {
    "return_type": "simple",
    "annualization": {
        # Decision 0002. Daily factor depends on the observed calendar:
        # business-day series (no weekend observations) use 252, calendar-day
        # series (weekend observations present, e.g. crypto) use 365.
        "periods_per_year": {
            "daily_business": 252.0,
            "daily_calendar": 365.0,
            "weekly": 52.0,
            "monthly": 12.0,
            "quarterly": 4.0,
            "yearly": 1.0,
        },
        "irregular": "not annualized",
        "unknown": "not annualized unless the caller declares the observation frequency",
        "scaling": "square-root-of-time for volatility; linear for arithmetic means",
    },
    "risk_free": {
        "rate": 0.0,
        "description": (
            "0% per period in methodology 0.1.0 for all excess-return metrics "
            "(Sharpe, Sortino, Calmar, Martin, alpha, Treynor). Ratios are therefore "
            "total-return ratios; this is disclosed on every affected metric."
        ),
    },
    "dispersion": {
        "ddof": 1,
        "description": "sample standard deviation (n - 1 denominator)",
    },
    "annual_return": {
        "method": "geometric",
        "description": (
            "geometric (CAGR): (prod(1 + r))^(periods_per_year / n) - 1; the "
            "arithmetic mean x periods_per_year is reported separately"
        ),
    },
    "downside": {
        "mar": 0.0,
        "denominator": "full_sample",
        "description": (
            "target (MAR) = 0% per period; downside deviation = "
            "sqrt(sum(min(r - MAR, 0)^2) / n) using all n observations"
        ),
    },
    "omega": {
        "threshold": 0.0,
        "description": "threshold = 0% per period, simple (empirical) estimator",
    },
    "lower_partial_moments": {
        # Decision 0016. Kappa-3 and the upside potential ratio share the Sortino
        # target and the full-sample denominator; all are per-period ratios.
        "target": 0.0,
        "kappa_order": 3,
        "denominator": "full_sample",
    },
    "sterling": {
        # Decision 0017. Historical 10% adjustment added to |max drawdown|.
        "excess": 0.10,
    },
    "parametric_var": {
        # Decision 0018. Population moments (Boudt, Peterson & Croux 2008), so the
        # Cornish-Fisher quantile reduces exactly to the Gaussian one when S = K = 0.
        "confidence": 0.95,
        "moments": "population",
    },
    "drawdown_risk": {
        # Decision 0021. Tail measures of the compounded drawdown path D_1..D_n
        # (the inception point is excluded), using the historical-ES estimator of
        # decision 0010 so DaR / CDaR are consistent with VaR / ES.
        "confidence": 0.95,
        "quantile_method": "linear",
    },
    "entropic": {
        # Decision 0021. Entropic VaR (Ahmadi-Javid 2012) of losses at 95%.
        "confidence": 0.95,
    },
    "modified_es": {
        # Decision 0022. Cornish-Fisher ES (Boudt, Peterson & Croux 2008),
        # population moments, full second-order expansion.
        "confidence": 0.95,
        "moments": "population",
    },
    "calendar_years": {
        # Decision 0023. Only complete calendar years are used.
        "monthly": "all 12 calendar months observed",
        "quarterly": "all 4 calendar quarters observed",
        "yearly": "the year's observation",
        "daily_weekly_edge_tolerance_days": 7,
    },
    "rolling": {
        # Decision 0024. One-year windows of round(periods_per_year) consecutive
        # observations, advanced one observation at a time.
        "window_years": 1,
        "step_periods": 1,
    },
    "sharpe_inference": {
        # Decision 0019. Non-normal i.i.d. asymptotics (Mertens 2002; Bailey &
        # Lopez de Prado 2012) on the per-period Sharpe ratio.
        "reference_sharpe": 0.0,
        "ci_level": 0.95,
        "min_track_record_confidence": 0.95,
        "moments": "population skewness g1 and non-excess kurtosis m4 / m2^2",
    },
    "mean_inference": {
        # Decision 0020. Student-t interval with n - 1 degrees of freedom.
        "ci_level": 0.95,
    },
    "tail": {
        "var_confidence": 0.95,
        "es_confidence": 0.95,
        "quantile_method": "linear",
        "sign": "signed return (negative = loss)",
        "description": (
            "historical 95% VaR = 5% empirical quantile (linear interpolation, R type 7); "
            "95% ES = mean of returns at or below that quantile; both reported as "
            "signed returns (negative = loss)"
        ),
    },
    "drawdown": {
        "initial_wealth_is_peak": True,
        "description": (
            "wealth index starts at 1 before the first return, so a first-period loss "
            "is a drawdown; drawdowns reported as signed returns (negative = loss)"
        ),
    },
    "distribution": {
        "skewness": "adjusted Fisher-Pearson G1 (bias-corrected sample skewness)",
        "kurtosis": "bias-corrected sample excess kurtosis G2",
        "description": "bias-corrected sample estimators G1 and G2 (as pandas / Excel)",
    },
    "dependence": {
        "acf_lags": [1, 2, 3],
        "ljung_box_lags": 3,
        "description": "sample autocorrelation (full-sample variance denominator)",
    },
    "benchmark": {
        "alignment": "intersection of periods; never filled",
        "regression": "OLS of fund on benchmark returns (risk-free = 0)",
        "alpha_annualization": "arithmetic: per-period intercept x periods_per_year",
        "information_ratio": "annualized arithmetic mean active return / tracking error",
        "capture": "geometric, annualized over up (benchmark > 0) or down (benchmark < 0) periods",
        "description": (
            "periods aligned on their intersection (monthly/quarterly/yearly by calendar "
            "period, daily/weekly by exact date); missing benchmark returns are never filled"
        ),
    },
    "missing_data": {
        "description": (
            "missing returns are never replaced by zero or forward-filled; leading and "
            "trailing gaps are trimmed, interior gaps are disclosed and the remaining "
            "observations are analyzed"
        ),
    },
    "return_scale": {
        # Decision 0013. Upper bound for the median absolute return of a
        # plausible *decimal* series, by frequency.
        "decimal_median_abs_upper": {
            "daily": 0.05,
            "weekly": 0.10,
            "monthly": 0.20,
            "quarterly": 0.30,
            "yearly": 0.60,
            "irregular": 0.30,
            "unknown": 0.30,
        },
        # Below (upper / confident_divisor) a series is confidently decimal.
        "confident_divisor": 4.0,
    },
    "smoothing": {
        # Decision 0014. Heuristic, documented, versioned.
        "min_observations": 12,
        "high": {"lag1_min": 0.30, "z_min": 1.96},
        "moderate": {"lag1_min": 0.15, "z_min": 1.645},
        "reference": "Getmansky, Lo & Makarov (2004), Journal of Financial Economics 74(3)",
    },
    "outliers": {
        "robust_z_threshold": 5.0,
        "description": (
            "robust z-score |r - median| / (1.4826 * MAD) above 5 is flagged (never removed)"
        ),
    },
    "stale_returns": {
        "zero_share_warning": 0.10,
        "identical_run_warning": 3,
    },
    "confidence": {
        # Benchmark-relative metrics are capped at "moderate" when the aligned
        # overlap covers less than this share of the fund's observations.
        "benchmark_min_coverage": 0.9,
        # Annualized metrics are "low" confidence when fewer years than this exist.
        "annualization_min_years": 1.0,
    },
    "distribution_warning": {
        "skewness_at_or_below": -1.0,
        "excess_kurtosis_at_or_above": 3.0,
        "min_observations": 24,
    },
}


@cache
def canonical_methodology() -> Methodology:
    """The canonical methodology object embedded in every report."""
    return Methodology(version=METHODOLOGY_VERSION, conventions=CANONICAL_ASSUMPTIONS)
