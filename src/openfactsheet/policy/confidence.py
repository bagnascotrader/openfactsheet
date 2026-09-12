"""Confidence engine (CLAUDE.md section 15).

Confidence describes the reliability of an *estimate*, never the quality of
the investment. It is derived transparently from:

* the metric's minimum-data policy (observations, years, expected tail count);
* data-quality diagnostics (smoothing/serial correlation, missing periods,
  stale returns, distribution shape, declared frequency);
* the benchmark overlap for benchmark-relative metrics.

A low-confidence metric is still shown with its value and warnings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.models.metric import Confidence, MetricDefinition, MetricStatus
from openfactsheet.policy.annualization import annualization_assumption
from openfactsheet.policy.risk_free import RISK_FREE_ASSUMPTION
from openfactsheet.policy.thresholds import get_policy

if TYPE_CHECKING:
    from openfactsheet.metrics.context import MetricContext

_RANK: dict[str, int] = {"high": 3, "moderate": 2, "low": 1}

IID_ASYMPTOTICS_ASSUMPTION = (
    "Asymptotic normal approximation for independent, identically distributed returns, "
    "allowing for skewness and kurtosis (Mertens 2002; Bailey & Lopez de Prado 2012); serial "
    "correlation is not modelled."
)
PARAMETRIC_ASSUMPTION = (
    "Model-dependent: return distribution approximated from population moments (normal, or "
    "Cornish-Fisher expansion with skewness and excess kurtosis); not a historical estimate."
)


def _cap(current: Confidence, ceiling: Confidence) -> Confidence:
    return ceiling if _RANK[ceiling] < _RANK[current] else current


@dataclass(frozen=True)
class Assessment:
    status: MetricStatus
    confidence: Confidence
    warnings: tuple[str, ...]
    assumptions: tuple[str, ...]


def assumption_texts(definition: MetricDefinition, ctx: MetricContext) -> tuple[str, ...]:
    m = ctx.methodology
    texts: list[str] = []
    for key in definition.assumption_keys:
        if key == "annualization":
            r = ctx.returns
            texts.append(
                annualization_assumption(r.frequency, r.periods_per_year, r.frequency_source)
            )
        elif key == "risk_free":
            texts.append(RISK_FREE_ASSUMPTION)
        elif key == "mar":
            texts.append(
                f"Minimum acceptable return (target) = {m.get('downside.mar'):.0%} per period; "
                "downside deviation uses all observations in the denominator."
            )
        elif key == "omega_threshold":
            texts.append(f"Omega threshold = {m.get('omega.threshold'):.0%} per period.")
        elif key == "tail":
            texts.append(
                f"{m.get('tail.var_confidence'):.0%} confidence; historical (empirical) quantile "
                "with linear interpolation; no distributional assumption; reported as a signed "
                "return (negative = loss)."
            )
        elif key == "drawdown":
            texts.append(
                "Wealth index starts at 1 before the first return; drawdowns are measured from "
                "running peaks of compounded wealth."
            )
        elif key == "sample_std":
            texts.append("Sample standard deviation (n - 1 denominator).")
        elif key == "benchmark" and ctx.benchmark is not None:
            b = ctx.benchmark.diagnostics
            texts.append(
                f"Benchmark {b.name!r}: {b.aligned_observations} aligned observations "
                f"({b.alignment_method})."
            )
        elif key == "regression":
            texts.append(
                "Ordinary least squares of fund on benchmark returns (risk-free rate 0%); "
                "conventional i.i.d. standard errors."
            )
        elif key == "iid_asymptotics":
            texts.append(IID_ASYMPTOTICS_ASSUMPTION)
        elif key == "parametric":
            texts.append(PARAMETRIC_ASSUMPTION)
        elif key == "entropic":
            texts.append(
                f"{m.get('entropic.confidence'):.0%} confidence; entropic VaR of the empirical "
                "distribution (exponential-moment bound), computed by one-dimensional convex "
                "minimization; signed return (negative = loss)."
            )
        elif key == "sterling_excess":
            texts.append(
                f"Sterling adjustment: {m.get('sterling.excess'):.0%} added to the absolute "
                "maximum drawdown (a historical convention, not an estimate)."
            )
    return tuple(texts)


def assess(definition: MetricDefinition, ctx: MetricContext, notes: tuple[str, ...]) -> Assessment:
    warnings: list[str] = list(notes)
    diag = ctx.diagnostics
    policy = get_policy(definition.min_data_policy)

    if definition.requires_benchmark and ctx.benchmark is not None:
        n = ctx.benchmark.n
        ppy = ctx.benchmark.periods_per_year
    else:
        n = ctx.n
        ppy = ctx.returns.periods_per_year
    years = n / ppy if ppy is not None else None
    tail_p = 1.0 - float(ctx.methodology.get("tail.var_confidence"))
    confidence, reason = policy.confidence(n, years, tail_p)
    if reason:
        warnings.append(reason)

    # Smoothing / serial correlation.
    if definition.volatility_based:
        if diag.smoothing_risk == "high":
            confidence = "low"
            warnings.append(
                "High serial correlation suggests smoothed or stale returns; measured volatility "
                "is likely understated and this metric overstated."
            )
        elif diag.smoothing_risk == "moderate":
            confidence = _cap(confidence, "moderate")
            warnings.append(
                "Moderate serial correlation: volatility may be understated by smoothed returns."
            )
        if diag.zero_return_pct >= float(ctx.methodology.get("stale_returns.zero_share_warning")):
            confidence = _cap(confidence, "moderate")
            warnings.append(
                f"{diag.zero_return_pct:.0%} of returns are exactly zero (possible stale pricing)."
            )
        shape = ctx.methodology.get("distribution_warning")
        if ctx.n >= int(shape["min_observations"]):
            skew: float | None
            kurt: float | None
            try:
                skew = ctx.cache.skewness
                kurt = ctx.cache.excess_kurtosis
            except UndefinedMetric:
                skew = kurt = None
            if (
                skew is not None
                and kurt is not None
                and (
                    skew <= float(shape["skewness_at_or_below"])
                    or kurt >= float(shape["excess_kurtosis_at_or_above"])
                )
            ):
                warnings.append(
                    f"Returns are far from normal (skewness {skew:.2f}, excess kurtosis "
                    f"{kurt:.2f}); volatility does not capture tail risk. See the drawdown and "
                    "tail sections."
                )

    # Gaps in the history.
    if definition.uses_wealth_path or definition.annualized:
        gaps = diag.missing_expected_periods or 0
        if gaps or diag.missing_values:
            confidence = _cap(confidence, "moderate")
            warnings.append(
                "The history has missing periods; compounding and annualization skip them."
            )
    if definition.uses_wealth_path and diag.total_loss:
        warnings.append("A -100% return occurs: wealth is zero from that period onward.")

    thresholds = ctx.methodology.get("confidence")

    # Annualizing less than a year of data.
    min_years = float(thresholds["annualization_min_years"])
    if definition.annualized and years is not None and years < min_years:
        confidence = "low"
        warnings.append(
            f"Annualized from only {years:.1f} years of data; the figure extrapolates a partial "
            "year."
        )

    # Declared frequency.
    if definition.annualized and ctx.returns.frequency_source == "declared":
        warnings.append("Annualization relies on a frequency declared by the caller, not on dates.")

    # Benchmark overlap.
    if definition.requires_benchmark and ctx.benchmark is not None:
        b = ctx.benchmark.diagnostics
        if b.fund_coverage < float(thresholds["benchmark_min_coverage"]):
            confidence = _cap(confidence, "moderate")
            warnings.append(f"Benchmark overlaps only {b.fund_coverage:.0%} of the fund history.")
        if b.alignment_method.startswith("by position"):
            warnings.append("Fund and benchmark were paired by position, not by date.")

    if definition.supplementary:
        status: MetricStatus = "supplementary"
    elif confidence == "low":
        status = "low_confidence"
    else:
        status = "applicable"
    return Assessment(
        status=status,
        confidence=confidence,
        warnings=tuple(dict.fromkeys(warnings)),
        assumptions=assumption_texts(definition, ctx),
    )
