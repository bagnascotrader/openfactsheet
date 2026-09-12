"""Factor-model metrics (decision 0028).

Computed only when the caller supplies factor returns; otherwise every metric
here is ``not_applicable`` with the reason. The regression itself lives in
:mod:`openfactsheet.factors.regressions`; loadings of every factor are reported
in section 11 of the canonical report and in ``report.factor_analysis``.
"""

from __future__ import annotations

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import (
    ASNESS_KRAIL_LIEW_2001,
    CARHART_1997,
    FAMA_FRENCH_1993,
    FAMA_FRENCH_2015,
    FUNG_HSIEH_2004,
    JENSEN_1968,
    NEWEY_WEST_1987,
    NEWEY_WEST_1994,
    R_SANDWICH,
    STATSMODELS,
    lib,
)
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import Computed, MetricDocs

_FACTOR_CAVEATS = (
    "The factors do not span the fund's true risk exposures (omitted factors appear as alpha).",
    "Exposures change over time; one full-history regression averages them.",
    "Returns are smoothed or stale, which biases loadings toward zero and alpha upward.",
    "The factor returns are not investable at zero cost (alpha is measured against paper "
    "portfolios before trading costs).",
)
_FACTOR_ASSUMPTIONS = (
    "Linear factor model with constant loadings over the aligned periods.",
    "Factor returns supplied by the caller, aligned by period, never filled.",
    "Dependent variable: fund return minus the supplied RF column, or the fund return when no "
    "RF column is supplied (risk-free rate 0%).",
    "Newey-West (HAC) covariance with the canonical lag rule; Student t inference.",
)
_REG_LATEX = (
    r"y_t = \alpha + \sum_{j=1}^{k} \beta_j f_{j,t} + \varepsilon_t, \quad "
    r"y_t = r_t - r^{\mathrm{RF}}_t, \quad t = 1..m"
)
_REFS = (FAMA_FRENCH_1993, CARHART_1997, FAMA_FRENCH_2015, NEWEY_WEST_1987, NEWEY_WEST_1994)
_MIN_DATA = (
    "At least k + 2 aligned observations for k factors; low confidence below 3 years of overlap, "
    "moderate below 5 years."
)


def _fit_details(ctx: MetricContext) -> dict[str, object]:
    fit = ctx.fac.fit
    return {
        "model": fit.model,
        "factors": list(fit.factor_names),
        "dependent": fit.dependent,
        "hac_lags": fit.hac_lags,
        "df_resid": fit.df_resid,
    }


@metric(
    id="factor_alpha",
    name="Factor-model alpha (annualized)",
    category="factors",
    unit="decimal_return",
    direction="higher_is_better",
    nature="model_dependent",
    min_data_policy="factor_regression",
    requires_factors=True,
    annualized=True,
    assumptions=("factor_model", "annualization"),
    docs=MetricDocs(
        measures="Average return not explained by the supplied factors, annualized.",
        formula="P * a, with a the intercept of OLS: y_t = a + sum_j b_j f_j,t + e_t",
        formula_latex=r"\alpha_{\text{ann}} = P \, \hat\alpha, \quad " + _REG_LATEX,
        undefined_when=(
            "A factor is constant over the aligned periods.",
            "The factor returns are perfectly collinear over the aligned periods.",
        ),
        inputs="Fund returns and caller-supplied factor returns (optionally with an RF column) "
        "on aligned periods with a regular frequency.",
        retail="The part of the fund's yearly return that the supplied factors (for example the "
        "market, size and value) do not explain. It depends entirely on which factors are used.",
        institutional="Multi-factor (Jensen-style) alpha, annualized arithmetically. Details "
        "report the per-period intercept with its Newey-West standard error, t-statistic, "
        "p-value and 95% confidence interval (annualized). Judge alpha by its uncertainty, not "
        "its point estimate; with smoothed returns it is biased upward.",
        assumptions=(*_FACTOR_ASSUMPTIONS, "Arithmetic annualization of the intercept."),
        misleading_when=(*_FACTOR_CAVEATS, "The history is short."),
        minimum_data=_MIN_DATA,
        reference_implementations=(
            lib(R_SANDWICH, "coef(lm)[1] * P", note="Validated on the factor fixture."),
            lib(STATSMODELS, "OLS(...).fit(cov_type='HAC')"),
        ),
        references=(JENSEN_1968, *_REFS, ASNESS_KRAIL_LIEW_2001),
        convention="Per-period OLS intercept x periods per year (decision 0028).",
    ),
)
def factor_alpha(ctx: MetricContext) -> Computed:
    fit = ctx.fac.fit
    ppy = ctx.ppy
    a = fit.alpha

    def ann(x: float | None) -> float | None:
        return x * ppy if x is not None else None

    return Computed(
        a.estimate * ppy,
        details={
            **_fit_details(ctx),
            "per_period": a.estimate,
            "standard_error_per_period": a.standard_error,
            "t_statistic": a.t_statistic,
            "p_value": a.p_value,
            "ci_level": fit.ci_level,
            "ci_lower": ann(a.ci_lower),
            "ci_upper": ann(a.ci_upper),
        },
    )


@metric(
    id="factor_alpha_t_statistic",
    name="Factor-model alpha t-statistic (Newey-West)",
    category="factors",
    unit="ratio",
    direction="context_dependent",
    nature="model_dependent",
    min_data_policy="factor_regression",
    requires_factors=True,
    assumptions=("factor_model",),
    docs=MetricDocs(
        measures="How many (Newey-West) standard errors the factor-model alpha lies from zero.",
        formula="a / SE_HAC(a)",
        formula_latex=(
            r"t_\alpha = \frac{\hat\alpha}{\widehat{\mathrm{SE}}_{\mathrm{HAC}}(\hat\alpha)},"
            r" \quad "
            r"\widehat{V}_{\mathrm{HAC}} = \frac{m}{m-k-1} (X^\top X)^{-1} \hat S (X^\top X)^{-1},"
            r" \quad \hat S = \sum_{\ell=-q}^{q} \Big(1 - \frac{|\ell|}{q+1}\Big) \hat\Gamma_\ell,"
            r" \quad q = \big\lfloor 4 (m/100)^{2/9} \big\rfloor"
        ),
        undefined_when=(
            "A factor is constant or the factors are perfectly collinear.",
            "The factors reproduce the fund exactly (residuals zero or below floating-point "
            "resolution), so the standard error is zero.",
        ),
        inputs="Fund returns and caller-supplied factor returns on aligned periods.",
        retail="A rough gauge of whether the unexplained return could be luck: values beyond "
        "about +2 or -2 are unlikely to arise by chance alone if the model is right.",
        institutional="Student-t statistic of the intercept with m - k - 1 degrees of freedom "
        "and heteroskedasticity- and autocorrelation-consistent standard errors; the p-value "
        "and interval are in the alpha details. Multiple testing across funds or models "
        "inflates apparent significance.",
        assumptions=_FACTOR_ASSUMPTIONS,
        misleading_when=(
            *_FACTOR_CAVEATS,
            "Many funds or factor sets were tried and the best t-statistic is reported.",
        ),
        minimum_data=_MIN_DATA,
        reference_implementations=(
            lib(R_SANDWICH, "coeftest(lm, vcov = NeweyWest(lm, lag = L, prewhite = FALSE))"),
            lib(STATSMODELS, "OLS(...).fit(cov_type='HAC', use_t=True).tvalues[0]"),
        ),
        references=(NEWEY_WEST_1987, NEWEY_WEST_1994, *_REFS[:3]),
        convention="Newey-West lag floor(4 (m/100)^(2/9)), Bartlett kernel, small-sample factor "
        "m / (m - k - 1), no prewhitening (decision 0028).",
    ),
)
def factor_alpha_t_statistic(ctx: MetricContext) -> Computed:
    fit = ctx.fac.fit
    t = fit.alpha.t_statistic
    if t is None:
        raise UndefinedMetric(
            "The factors reproduce the fund exactly (residuals zero or below floating-point "
            "resolution), so the standard error of alpha is zero and its t-statistic is undefined."
        )
    return Computed(t, details={**_fit_details(ctx), "p_value": fit.alpha.p_value})


@metric(
    id="factor_r_squared",
    name="Factor-model R-squared",
    category="factors",
    unit="fraction",
    direction="neutral",
    nature="estimated",
    min_data_policy="factor_regression",
    requires_factors=True,
    assumptions=("factor_model",),
    docs=MetricDocs(
        measures="Share of the variance of fund (excess) returns explained by the factors.",
        formula="1 - SSR / SST of the factor regression",
        formula_latex=(
            r"R^2 = 1 - \frac{\sum_{t=1}^{m} \hat\varepsilon_t^2}{\sum_{t=1}^{m} (y_t - \bar y)^2},"
            r" \quad \bar R^2 = 1 - (1 - R^2) \frac{m - 1}{m - k - 1}"
        ),
        undefined_when=(
            "A factor is constant or the factors are perfectly collinear.",
            "The dependent variable is constant (no variance to explain).",
        ),
        inputs="Fund returns and caller-supplied factor returns on aligned periods.",
        retail="How much of the fund's ups and downs the factors account for (1 = all of it).",
        institutional="A low R-squared means the factor loadings and alpha describe little of "
        "the fund's risk; the factor set may be inappropriate for the strategy. Adjusted "
        "R-squared is in the details.",
        assumptions=_FACTOR_ASSUMPTIONS[:3],
        misleading_when=(
            "Adding factors always raises R-squared; compare adjusted R-squared across models.",
            "Returns are smoothed (explained variance is understated).",
        ),
        minimum_data=_MIN_DATA,
        reference_implementations=(
            lib(R_SANDWICH, "summary(lm)$r.squared"),
            lib(STATSMODELS, "OLS(...).fit().rsquared"),
        ),
        references=(*_REFS[:3], FUNG_HSIEH_2004),
        convention="Centred R-squared of the OLS fit with an intercept (decision 0028).",
    ),
)
def factor_r_squared(ctx: MetricContext) -> Computed:
    fit = ctx.fac.fit
    if fit.r_squared is None:
        raise UndefinedMetric(
            "The dependent variable is constant over the aligned periods; there is no variance "
            "to explain."
        )
    return Computed(
        fit.r_squared, details={**_fit_details(ctx), "adjusted_r_squared": fit.adj_r_squared}
    )


@metric(
    id="factor_residual_volatility",
    name="Factor-model residual volatility (annualized)",
    category="factors",
    unit="decimal_return",
    direction="neutral",
    nature="estimated",
    min_data_policy="factor_regression",
    requires_factors=True,
    annualized=True,
    assumptions=("factor_model", "annualization"),
    docs=MetricDocs(
        measures="Volatility of the return not explained by the factors (specific risk).",
        formula="sqrt(SSR / (m - k - 1)) * sqrt(P)",
        formula_latex=(
            r"\sigma_\varepsilon = \sqrt{\frac{\sum_{t=1}^{m} \hat\varepsilon_t^2}{m-k-1}}"
            r" \, \sqrt{P}"
        ),
        undefined_when=("A factor is constant or the factors are perfectly collinear.",),
        inputs="Fund returns and caller-supplied factor returns on aligned periods with a "
        "regular frequency.",
        retail="How much the fund moves for reasons the factors do not capture; the size of "
        "the manager's independent bets, whether they pay off or not.",
        institutional="Regression standard error annualized by the square root of time; the "
        "denominator of a factor-model appraisal ratio. Understated when returns are smoothed.",
        assumptions=(*_FACTOR_ASSUMPTIONS[:3], "Square-root-of-time annualization."),
        misleading_when=(
            "Returns are smoothed or stale (volatility suppressed).",
            "Exposures change over time (time-varying betas appear as residual risk).",
        ),
        minimum_data=_MIN_DATA,
        reference_implementations=(lib(R_SANDWICH, "summary(lm)$sigma * sqrt(P)"),),
        references=(*_REFS[:3],),
        convention="Residual degrees of freedom m - k - 1, square-root-of-time annualization "
        "(decision 0028).",
    ),
)
def factor_residual_volatility(ctx: MetricContext) -> Computed:
    fit = ctx.fac.fit
    return Computed(
        fit.residual_std * ctx.ppy**0.5,
        details={**_fit_details(ctx), "per_period": fit.residual_std},
    )
