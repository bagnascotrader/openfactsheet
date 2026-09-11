"""Statistical confidence in performance (CLAUDE.md section 12.11).

Raw performance is separated from confidence in performance. The Sharpe-ratio
inference uses the non-normal i.i.d. asymptotic variance of the per-period
Sharpe ratio (Mertens 2002; Opdyke 2007), as used by Bailey & Lopez de Prado
(2012) for the Probabilistic Sharpe Ratio and the Minimum Track Record Length:

    Var(SR_hat) ~ (1 - g3 * SR + (g4 - 1) / 4 * SR^2) / (n - 1)

with g3 the moment skewness and g4 the (non-excess) moment kurtosis. Serial
correlation is not modelled; smoothed series are flagged by the confidence
policy (these metrics are volatility-based).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import (
    BAILEY_LDP_2012,
    LO_2002,
    MERTENS_2002,
    OPDYKE_2007,
    PA,
    SCIPY,
    STUDENT_1908,
    lib,
)
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import Computed, MetricDocs

_IID_CAVEATS = (
    "Returns are serially correlated or smoothed: the i.i.d. variance understates the true "
    "uncertainty (Lo, 2002).",
    "Samples are short: the asymptotic normal approximation is poor.",
    "Many strategies were tried before this one was shown (selection bias; see the Deflated "
    "Sharpe Ratio, which needs the number of trials and is not computable from one series).",
)


@dataclass(frozen=True)
class _SharpeMoments:
    sr: float  # per-period Sharpe ratio, mean / sample std, rf = 0
    g3: float  # moment skewness
    g4: float  # moment (non-excess) kurtosis
    variance_factor: float  # 1 - g3*SR + (g4 - 1)/4 * SR^2
    n: int


def _sharpe_moments(ctx: MetricContext) -> _SharpeMoments:
    std = ctx.cache.std
    if std == 0.0:
        raise UndefinedMetric("Volatility is zero; Sharpe-ratio inference is undefined.")
    sr = ctx.cache.mean / std
    g3 = ctx.cache.population_skewness
    g4 = ctx.cache.population_kurtosis
    factor = 1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr**2
    if factor <= 0.0:
        raise UndefinedMetric(
            "The asymptotic variance factor of the Sharpe ratio is not positive (degenerate "
            "return distribution)."
        )
    return _SharpeMoments(sr=sr, g3=g3, g4=g4, variance_factor=factor, n=ctx.n)


def _norm_cdf(x: float) -> float:
    from scipy.stats import norm

    return float(norm.cdf(x))


def _norm_ppf(p: float) -> float:
    from scipy.stats import norm

    return float(norm.ppf(p))


@metric(
    id="probabilistic_sharpe_ratio",
    name="Probabilistic Sharpe Ratio (vs 0)",
    category="statistical",
    unit="probability",
    direction="higher_is_better",
    nature="estimated",
    min_data_policy="asymptotic_inference",
    volatility_based=True,
    assumptions=("iid_asymptotics", "risk_free"),
    docs=MetricDocs(
        measures="Estimated probability that the true Sharpe ratio is above zero, given the "
        "track-record length, skewness and kurtosis.",
        formula="Phi( (SR - SR*) * sqrt(n - 1) / sqrt(1 - g3*SR + (g4 - 1)/4 * SR^2) ), SR* = 0",
        formula_latex=(
            r"\mathrm{PSR} = \Phi\!\left( \frac{(\widehat{SR} - SR^*)\sqrt{n-1}}"
            r"{\sqrt{1 - g_3 \widehat{SR} + \frac{g_4 - 1}{4} \widehat{SR}^2}} \right), \quad "
            r"\widehat{SR} = \frac{\bar r}{s}, \ g_3 = \frac{m_3}{m_2^{3/2}}, \ "
            r"g_4 = \frac{m_4}{m_2^2}, \ SR^* = 0"
        ),
        undefined_when=(
            "Sample standard deviation is exactly zero.",
            "Return variance underflows in floating point (moments not computable).",
            "The variance factor is not positive (degenerate distribution).",
        ),
        inputs="Periodic simple returns.",
        retail="How confident one can be, statistically, that the investment's risk-adjusted "
        "return is genuinely positive rather than luck. Values near 1 mean strong evidence; "
        "0.5 means no evidence either way.",
        institutional="Bailey & Lopez de Prado (2012) PSR with benchmark SR* = 0 on the per-period "
        "(non-annualized) Sharpe ratio, using moment skewness and non-excess kurtosis. Unlike "
        "PerformanceAnalytics' default, kurtosis is not ignored: fat tails reduce confidence.",
        assumptions=("Independent, identically distributed returns.", "Risk-free rate 0%."),
        misleading_when=_IID_CAVEATS,
        minimum_data="At least 4 observations; low confidence below 36, moderate below 60.",
        reference_implementations=(
            lib(
                PA,
                "ProbSharpeRatio(refSR=0, ignore_kurtosis=FALSE)",
                note="Agrees with ignore_kurtosis=FALSE; the PerformanceAnalytics default sets "
                "kurtosis to 3.",
            ),
        ),
        references=(BAILEY_LDP_2012, MERTENS_2002),
        convention="Reference Sharpe ratio 0, per-period Sharpe, population moments "
        "(decision 0019).",
    ),
)
def probabilistic_sharpe_ratio(ctx: MetricContext) -> Computed:
    m = _sharpe_moments(ctx)
    ref = float(ctx.methodology.get("sharpe_inference.reference_sharpe"))
    z = (m.sr - ref) * math.sqrt(m.n - 1) / math.sqrt(m.variance_factor)
    return Computed(
        _norm_cdf(z),
        details={
            "sharpe_per_period": m.sr,
            "z_statistic": z,
            "moment_skewness": m.g3,
            "moment_kurtosis": m.g4,
        },
    )


@metric(
    id="sharpe_ratio_standard_error",
    name="Sharpe ratio standard error (annualized)",
    category="statistical",
    unit="ratio",
    direction="neutral",
    nature="estimated",
    min_data_policy="asymptotic_inference",
    annualized=True,
    volatility_based=True,
    assumptions=("iid_asymptotics", "annualization", "risk_free"),
    docs=MetricDocs(
        measures="Sampling uncertainty of the annualized Sharpe ratio; details give the 95% "
        "confidence interval.",
        formula="sqrt(P) * sqrt( (1 - g3*SR + (g4 - 1)/4 * SR^2) / (n - 1) ); "
        "CI = SR_ann +/- z_0.975 * SE",
        formula_latex=(
            r"\mathrm{SE}(\widehat{SR}_{\text{ann}}) = \sqrt{P} \sqrt{\frac{1 - g_3 \widehat{SR}"
            r" + \frac{g_4 - 1}{4} \widehat{SR}^2}{n - 1}}, \quad "
            r"\mathrm{CI}_{95} = \widehat{SR}\sqrt{P} \pm z_{0.975} \, \mathrm{SE}"
        ),
        undefined_when=(
            "Sample standard deviation is exactly zero.",
            "Return variance underflows in floating point (moments not computable).",
            "The variance factor is not positive (degenerate distribution).",
        ),
        inputs="Periodic simple returns with a regular frequency.",
        retail="How precisely the Sharpe ratio is known. A Sharpe ratio of 1.0 with a standard "
        "error of 0.5 could plausibly be anywhere from about 0 to 2.",
        institutional="Non-normal i.i.d. asymptotic standard error (Mertens 2002; Opdyke 2007), "
        "scaled by sqrt(P) like the annualized Sharpe ratio. The details report the two-sided "
        "95% interval (z = 1.96); PerformanceAnalytics' interval uses the one-sided quantile "
        "and is therefore a 90% interval.",
        assumptions=(
            "Independent, identically distributed returns.",
            "Square-root-of-time scaling of the per-period standard error.",
        ),
        misleading_when=_IID_CAVEATS,
        minimum_data="At least 4 observations; low confidence below 36, moderate below 60.",
        reference_implementations=(
            lib(
                PA,
                "ProbSharpeRatio(...)$sr_confidence_interval",
                agrees=False,
                note="Same variance formula; PerformanceAnalytics uses qnorm(0.95) (a 90% "
                "two-sided interval), a per-period Sharpe ratio and ignores kurtosis by default.",
            ),
        ),
        references=(MERTENS_2002, OPDYKE_2007, LO_2002),
        convention="Two-sided 95% interval, annualized by sqrt(P), population moments "
        "(decision 0019).",
    ),
)
def sharpe_ratio_standard_error(ctx: MetricContext) -> Computed:
    m = _sharpe_moments(ctx)
    level = float(ctx.methodology.get("sharpe_inference.ci_level"))
    se_pp = math.sqrt(m.variance_factor / (m.n - 1))
    se = se_pp * math.sqrt(ctx.ppy)
    sr_ann = m.sr * math.sqrt(ctx.ppy)
    half = _norm_ppf(0.5 + level / 2.0) * se
    return Computed(
        se,
        details={
            "sharpe_ratio": sr_ann,
            "ci_level": level,
            "ci_lower": sr_ann - half,
            "ci_upper": sr_ann + half,
            "standard_error_per_period": se_pp,
        },
    )


@metric(
    id="minimum_track_record_length",
    name="Minimum track record length",
    category="statistical",
    unit="periods",
    direction="neutral",
    nature="estimated",
    min_data_policy="asymptotic_inference",
    volatility_based=True,
    assumptions=("iid_asymptotics", "risk_free"),
    docs=MetricDocs(
        measures="Number of observations needed for the observed Sharpe ratio to be "
        "statistically above zero at 95% confidence.",
        formula="1 + (1 - g3*SR + (g4 - 1)/4 * SR^2) * ( z_0.95 / (SR - SR*) )^2, SR* = 0",
        formula_latex=(
            r"\mathrm{MinTRL} = 1 + \left(1 - g_3 \widehat{SR} + \frac{g_4 - 1}{4}"
            r" \widehat{SR}^2\right) \left( \frac{z_{0.95}}{\widehat{SR} - SR^*} \right)^2,"
            r" \quad SR^* = 0"
        ),
        undefined_when=(
            "The observed Sharpe ratio is not above the reference 0 (no track-record length can "
            "make it significant).",
            "Sample standard deviation is exactly zero.",
            "Return variance underflows in floating point (moments not computable).",
        ),
        inputs="Periodic simple returns.",
        retail="How long a track record this investment would need before its risk-adjusted "
        "return could be told apart from luck. If it exceeds the actual history, the record is "
        "too short to be conclusive.",
        institutional="Bailey & Lopez de Prado (2012) MinTRL at 95% one-sided confidence with "
        "SR* = 0, in observation periods (details give years and whether the actual history "
        "suffices). Depends on the observed Sharpe ratio, skewness and kurtosis.",
        assumptions=("Independent, identically distributed returns.",),
        misleading_when=_IID_CAVEATS,
        minimum_data="At least 4 observations; low confidence below 36, moderate below 60.",
        reference_implementations=(
            lib(
                PA,
                "MinTrackRecord(refSR=0, p=0.95, ignore_kurtosis=FALSE)",
                note="Agrees with ignore_kurtosis=FALSE.",
            ),
        ),
        references=(BAILEY_LDP_2012,),
        convention="95% one-sided, SR* = 0, per-period Sharpe, population moments (decision 0019).",
    ),
)
def minimum_track_record_length(ctx: MetricContext) -> Computed:
    m = _sharpe_moments(ctx)
    ref = float(ctx.methodology.get("sharpe_inference.reference_sharpe"))
    if m.sr <= ref:
        raise UndefinedMetric(
            "The observed Sharpe ratio is not above 0; no track-record length would make it "
            "statistically positive."
        )
    conf = float(ctx.methodology.get("sharpe_inference.min_track_record_confidence"))
    min_trl = 1.0 + m.variance_factor * (_norm_ppf(conf) / (m.sr - ref)) ** 2
    ppy = ctx.returns.periods_per_year
    return Computed(
        min_trl,
        details={
            "years": min_trl / ppy if ppy else None,
            "observed_periods": m.n,
            "sufficient": m.n >= min_trl,
            "additional_periods_needed": max(0, math.ceil(min_trl - m.n)),
        },
    )


@metric(
    id="mean_return_standard_error",
    name="Mean return standard error (per period)",
    category="statistical",
    unit="decimal_return",
    direction="neutral",
    nature="estimated",
    min_data_policy="dispersion",
    volatility_based=True,
    docs=MetricDocs(
        measures="Sampling uncertainty of the average per-period return; details give the 95% "
        "confidence interval and a test of the mean against zero.",
        formula="s / sqrt(n); CI = mean +/- t_(0.975, n-1) * s / sqrt(n)",
        formula_latex=(
            r"\mathrm{SE}(\bar r) = \frac{s}{\sqrt{n}}, \quad \mathrm{CI}_{95} = \bar r \pm "
            r"t_{0.975,\,n-1} \, \frac{s}{\sqrt{n}}, \quad t = \frac{\bar r}{\mathrm{SE}(\bar r)}"
        ),
        undefined_when=("Sample standard deviation is exactly zero (no sampling variability).",),
        inputs="Periodic simple returns.",
        retail="How precisely the average return is known. If the confidence interval includes "
        "zero, the history cannot distinguish the average return from zero.",
        institutional="Student-t interval and two-sided t-test for the mean with n - 1 degrees "
        "of freedom (exact under normal i.i.d. returns, asymptotically valid otherwise). Serial "
        "correlation widens the true interval.",
        assumptions=("Independent, identically distributed returns.",),
        misleading_when=(
            "Returns are serially correlated or smoothed (the interval is too narrow).",
            "Returns are strongly skewed and the sample is short.",
        ),
        minimum_data="At least 2 observations; low confidence below 3 years.",
        reference_implementations=(lib(SCIPY, "stats.t / stats.ttest_1samp"),),
        references=(STUDENT_1908,),
        convention="Student-t, two-sided 95%, per period (decision 0020).",
    ),
)
def mean_return_standard_error(ctx: MetricContext) -> Computed:
    from scipy.stats import t as student_t

    std = ctx.cache.std
    if std == 0.0:
        raise UndefinedMetric(
            "Returns are constant; the standard error of the mean is zero and "
            "inference is undefined."
        )
    n = ctx.n
    level = float(ctx.methodology.get("mean_inference.ci_level"))
    se = std / math.sqrt(n)
    tq = float(student_t.ppf(0.5 + level / 2.0, n - 1))
    t_stat = ctx.cache.mean / se
    p_value = float(2.0 * student_t.sf(abs(t_stat), n - 1))
    return Computed(
        se,
        details={
            "ci_level": level,
            "ci_lower": ctx.cache.mean - tq * se,
            "ci_upper": ctx.cache.mean + tq * se,
            "t_statistic": t_stat,
            "p_value": p_value,
        },
    )
