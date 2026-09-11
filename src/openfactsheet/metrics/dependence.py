"""Serial dependence, smoothing and stale-return metrics (CLAUDE.md section 12.7).

OpenFactsheet never unsmooths returns in the canonical report; these metrics
diagnose, and the confidence policy warns on affected metrics.
"""

from __future__ import annotations

import math

from openfactsheet.diagnostics.autocorrelation import ljung_box, sample_autocorrelation
from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import GLM_2004, LJUNG_BOX_1978, STATSMODELS, lib
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import Computed, MetricDocs


def _acf_docs(lag: int) -> MetricDocs:
    return MetricDocs(
        measures=f"Correlation between each return and the return {lag} period(s) earlier.",
        formula=f"rho_{lag} = sum_(t>{lag}) (r_t - m)(r_(t-{lag}) - m) / sum_t (r_t - m)^2",
        inputs="Periodic simple returns.",
        retail="Whether good or bad periods tend to be followed by similar periods. Values "
        "near zero are typical for liquid, market-priced investments.",
        institutional="Sample autocorrelation (full-sample variance denominator). Significant "
        "positive low-lag autocorrelation is a hallmark of return smoothing or illiquidity "
        "(Getmansky, Lo & Makarov, 2004) and biases square-root-of-time annualization. "
        "Approximate 95% significance bound: +/- 1.96 / sqrt(n).",
        assumptions=("Stationary returns.",),
        misleading_when=(
            "Samples are short: standard error is roughly 1/sqrt(n).",
            "Volatility regimes change over the history.",
        ),
        minimum_data="At least 5 observations; low confidence below 36, moderate below 60.",
        reference_implementations=(lib(STATSMODELS, "tsa.stattools.acf(adjusted=False)"),),
        references=(GLM_2004,),
        convention="Standard biased-denominator estimator; not bias-corrected.",
    )


def _acf(ctx: MetricContext, lag: int) -> Computed:
    rho = sample_autocorrelation(ctx.r, lag)
    if rho is None:
        raise UndefinedMetric(
            f"Lag-{lag} autocorrelation is undefined (too few observations or constant returns)."
        )
    bound = 1.96 / math.sqrt(ctx.n)
    return Computed(rho, details={"approx_95pct_bound": bound, "significant": abs(rho) > bound})


@metric(
    id="autocorrelation_lag1",
    name="Autocorrelation (lag 1)",
    category="dependence",
    unit="correlation",
    direction="context_dependent",
    nature="estimated",
    min_data_policy="autocorrelation",
    docs=_acf_docs(1),
)
def autocorrelation_lag1(ctx: MetricContext) -> Computed:
    return _acf(ctx, 1)


@metric(
    id="autocorrelation_lag2",
    name="Autocorrelation (lag 2)",
    category="dependence",
    unit="correlation",
    direction="context_dependent",
    nature="estimated",
    min_data_policy="autocorrelation",
    docs=_acf_docs(2),
)
def autocorrelation_lag2(ctx: MetricContext) -> Computed:
    return _acf(ctx, 2)


@metric(
    id="autocorrelation_lag3",
    name="Autocorrelation (lag 3)",
    category="dependence",
    unit="correlation",
    direction="context_dependent",
    nature="estimated",
    min_data_policy="autocorrelation",
    docs=_acf_docs(3),
)
def autocorrelation_lag3(ctx: MetricContext) -> Computed:
    return _acf(ctx, 3)


@metric(
    id="ljung_box_pvalue",
    name="Ljung-Box p-value (3 lags)",
    category="dependence",
    unit="probability",
    direction="context_dependent",
    nature="model_dependent",
    min_data_policy="ljung_box",
    supplementary=True,
    docs=MetricDocs(
        measures="Joint test that the first three autocorrelations are all zero.",
        formula="Q = n(n+2) sum_{k=1..3} rho_k^2 / (n - k); p-value from chi-squared(3)",
        inputs="Periodic simple returns.",
        retail="A small value (below 0.05) suggests returns are not independent from one "
        "period to the next.",
        institutional="Ljung-Box portmanteau test with 3 lags (matching the reported "
        "autocorrelations). A diagnostic, not a performance measure; with very long samples "
        "trivial dependence becomes 'significant'.",
        assumptions=("Asymptotic chi-squared distribution of Q.",),
        misleading_when=(
            "Very short samples (low power) or very long samples (tiny effects significant).",
            "Heteroskedastic returns (the test assumes constant variance).",
        ),
        minimum_data="At least 10 observations; low confidence below 36, moderate below 60.",
        reference_implementations=(lib(STATSMODELS, "stats.diagnostic.acorr_ljungbox"),),
        references=(LJUNG_BOX_1978,),
        convention="3 lags, no degrees-of-freedom adjustment; supplementary status.",
    ),
)
def ljung_box_pvalue(ctx: MetricContext) -> Computed:
    lags = int(ctx.methodology.get("dependence.ljung_box_lags"))
    out = ljung_box(ctx.r, lags)
    if out is None:
        raise UndefinedMetric("Ljung-Box statistic is undefined (constant returns).")
    stat, pvalue = out
    return Computed(pvalue, details={"q_statistic": stat, "lags": lags})


@metric(
    id="zero_return_pct",
    name="Zero-return periods",
    category="dependence",
    unit="fraction",
    direction="context_dependent",
    nature="observed",
    min_data_policy="observed_point",
    docs=MetricDocs(
        measures="Share of periods with a return of exactly zero.",
        formula="#{t : r_t = 0} / n",
        inputs="Periodic simple returns.",
        retail="Many exactly-zero periods can mean prices were not updated (stale pricing).",
        institutional="Stale-price indicator; exact zeros are rare for marked-to-market "
        "portfolios and suppress measured volatility.",
        assumptions=(),
        misleading_when=(
            "Cash-like or closed strategies legitimately report zero returns.",
            "Returns were rounded to few decimals.",
        ),
        minimum_data="Any non-empty history.",
        reference_implementations=(),
        references=(GLM_2004,),
        convention="Exact equality with 0.0 after normalization.",
    ),
)
def zero_return_pct(ctx: MetricContext) -> float:
    return ctx.diagnostics.zero_return_pct
