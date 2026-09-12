"""Drawdown and underwater metrics (CLAUDE.md section 12.4).

All metrics consume the shared wealth/drawdown engine in
:mod:`openfactsheet.metrics.path` via the context cache.
"""

from __future__ import annotations

import numpy as np

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import (
    AHMADI_JAVID_2012,
    BACON,
    CAJAS_2021,
    CHEKHLOV_2005,
    EMP,
    MAGDON_ISMAIL_2004,
    MARTIN_MCCANN_1989,
    PA,
    QS,
    SKFOLIO,
    lib,
)
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import Computed, MetricDocs
from openfactsheet.utils.math import entropic_value_at_risk

_PATH_CAVEAT = (
    "Short histories: drawdown statistics grow with the length of the track record and "
    "cannot reveal risks that have not yet materialized."
)


@metric(
    id="max_drawdown",
    name="Maximum drawdown",
    category="drawdown",
    unit="decimal_return",
    direction="higher_is_better",
    signed_loss=True,
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Largest peak-to-trough decline of compounded wealth.",
        formula="min_t( W_t / max_{s<=t} W_s - 1 ), W_0 = 1, W_t = prod_{i<=t}(1 + r_i)",
        formula_latex=(
            r"\mathrm{MDD} = \min_{0 \le t \le n} D_t, \quad D_t = \frac{W_t}{M_t} - 1, \quad "
            r"M_t = \max_{0 \le u \le t} W_u, \quad W_0 = 1"
        ),
        inputs="Periodic simple returns.",
        retail="The worst loss an investor would have suffered buying at a high point and "
        "selling at the following low point.",
        institutional="Path-dependent realized loss; always shown. Expected maximum drawdown "
        "grows with history length and volatility (Magdon-Ismail & Atiya, 2004), so compare "
        "only across similar horizons.",
        assumptions=("Wealth index starts at 1 before the first return.",),
        misleading_when=(
            _PATH_CAVEAT,
            "Returns are smoothed, which reduces measured drawdowns.",
            "Data frequency is low: intra-period declines are invisible.",
        ),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(
            lib(PA, "maxDrawdown", note="PerformanceAnalytics reports a positive magnitude."),
            lib(EMP, "max_drawdown"),
            lib(QS, "stats.max_drawdown"),
        ),
        references=(MAGDON_ISMAIL_2004, BACON),
        convention="Signed (negative = loss); the inception value counts as a peak so a first-"
        "period loss is a drawdown (decision 0007).",
    ),
)
def max_drawdown(ctx: MetricContext) -> Computed:
    episodes = ctx.cache.episodes
    if not episodes:
        return Computed(0.0, details={"episodes": 0})
    worst = min(episodes, key=lambda e: e.depth)
    notes: tuple[str, ...] = ()
    if not worst.recovered:
        notes = (
            "The deepest drawdown has not recovered by the end of the data; the loss is "
            "still open.",
        )
    return Computed(
        worst.depth,
        details={
            "peak_date": worst.peak_date,
            "trough_date": worst.trough_date,
            "recovery_date": worst.recovery_date,
            "recovered": worst.recovered,
            "peak_to_trough_periods": worst.peak_to_trough_periods,
            "duration_periods": worst.duration_periods,
        },
        notes=notes,
    )


@metric(
    id="average_drawdown",
    name="Average drawdown (per episode)",
    category="drawdown",
    unit="decimal_return",
    direction="higher_is_better",
    signed_loss=True,
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Mean depth of all distinct drawdown episodes.",
        formula="(1/K) * sum_k depth_k over K peak-to-recovery episodes",
        formula_latex=(
            r"\overline{\mathrm{DD}} = \begin{cases} \frac{1}{K} \sum_{k=1}^{K} \delta_k & K > 0"
            r" \\ 0 & K = 0 \end{cases}, \quad \delta_k = \min_{t \in E_k} D_t"
        ),
        inputs="Periodic simple returns.",
        retail="How deep the typical decline from a high point has been.",
        institutional="Episode-based average (PerformanceAnalytics AverageDrawdown convention); "
        "less dominated by a single event than maximum drawdown. Compare with the Pain Index, "
        "which averages over time instead of over episodes.",
        assumptions=("Every decline below a prior peak, however small, is an episode.",),
        misleading_when=(_PATH_CAVEAT, "Many tiny episodes dilute the average."),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(
            lib(PA, "AverageDrawdown", note="PerformanceAnalytics reports a positive magnitude."),
        ),
        references=(BACON,),
        convention="Mean of episode depths, signed (negative = loss); 0 when no drawdown occurred.",
    ),
)
def average_drawdown(ctx: MetricContext) -> Computed:
    episodes = ctx.cache.episodes
    if not episodes:
        return Computed(0.0, details={"episodes": 0})
    return Computed(
        float(np.mean([e.depth for e in episodes])), details={"episodes": len(episodes)}
    )


@metric(
    id="current_drawdown",
    name="Current drawdown",
    category="drawdown",
    unit="decimal_return",
    direction="higher_is_better",
    signed_loss=True,
    nature="observed",
    min_data_policy="observed_point",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Decline of wealth at the end of the history relative to its highest point.",
        formula="W_n / max_{s<=n} W_s - 1",
        formula_latex=r"D_n = \frac{W_n}{M_n} - 1",
        inputs="Periodic simple returns.",
        retail="How far below its previous high the investment stands at the end of the data.",
        institutional="State variable at the reporting date; zero when the series ends at a "
        "high-water mark.",
        assumptions=("Wealth index starts at 1 before the first return.",),
        misleading_when=("The history ends at an arbitrary date.",),
        minimum_data="Any non-empty history.",
        reference_implementations=(lib(QS, "stats.to_drawdown_series (last value)"),),
        references=(BACON,),
        convention="Signed (negative = loss).",
    ),
)
def current_drawdown(ctx: MetricContext) -> float:
    return float(ctx.cache.drawdown[-1])


@metric(
    id="longest_drawdown_duration",
    name="Longest drawdown duration",
    category="drawdown",
    unit="periods",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Longest time from a peak until wealth regained that peak (or until the end of "
        "the history, if not yet recovered).",
        formula="max_k (recovery_k - peak_k) in periods; ongoing episodes use n - peak_k",
        formula_latex=(
            r"L_{\max} = \max_{1 \le k \le K} \ell_k, \quad \ell_k = \begin{cases}"
            r" \rho_k - \pi_k & \text{episode } k \text{ recovered} \\"
            r" n - \pi_k & \text{episode } k \text{ ongoing} \end{cases}"
            r", \quad L_{\max} = 0 \text{ if } K = 0"
        ),
        inputs="Periodic simple returns.",
        retail="The longest stretch an investor would have waited to get back to a previous high.",
        institutional="Peak-to-recovery duration in observation periods; an ongoing episode is "
        "a lower bound and is flagged as such.",
        assumptions=("Recovery means regaining the prior peak of compounded wealth.",),
        misleading_when=(_PATH_CAVEAT, "The longest episode is still ongoing (a lower bound)."),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(
            lib(
                PA,
                "findDrawdowns (length)",
                note="Equal for recovered episodes; PerformanceAnalytics counts an episode "
                "still open at the end of the data one period longer.",
            ),
        ),
        references=(BACON,),
        convention="Measured in observation periods from the peak to the recovery period "
        "inclusive; details report the equivalent in years when the frequency is regular.",
    ),
)
def longest_drawdown_duration(ctx: MetricContext) -> Computed:
    episodes = ctx.cache.episodes
    if not episodes:
        return Computed(0.0, details={"episodes": 0})
    longest = max(episodes, key=lambda e: e.duration_periods)
    ppy = ctx.returns.periods_per_year
    notes: tuple[str, ...] = ()
    if not longest.recovered:
        notes = (
            "The longest drawdown has not recovered by the end of the data; the duration "
            "is a lower bound.",
        )
    return Computed(
        float(longest.duration_periods),
        details={
            "years": longest.duration_periods / ppy if ppy else None,
            "peak_date": longest.peak_date,
            "recovery_date": longest.recovery_date,
            "ongoing": not longest.recovered,
        },
        notes=notes,
    )


@metric(
    id="drawdown_count",
    name="Number of drawdown episodes",
    category="drawdown",
    unit="count",
    direction="neutral",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="How many distinct peak-to-recovery declines occurred.",
        formula="K = number of maximal runs with W_t below its running peak",
        formula_latex=(
            r"K = \#\{\text{maximal runs } t_1..t_2 \subseteq 1..n \text{ with } D_t < 0"
            r" \ \forall t \in t_1..t_2\}"
        ),
        inputs="Periodic simple returns.",
        retail="How often the investment fell below a previous high.",
        institutional="Context for average drawdown and durations; depends strongly on data "
        "frequency and history length.",
        assumptions=("Every decline below a prior peak counts, however small.",),
        misleading_when=("Compared across frequencies or history lengths.",),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(lib(PA, "findDrawdowns (negative episodes)"),),
        references=(BACON,),
        convention="An ongoing episode at the end of the data is counted.",
    ),
)
def drawdown_count(ctx: MetricContext) -> Computed:
    episodes = ctx.cache.episodes
    ongoing = sum(1 for e in episodes if not e.recovered)
    return Computed(float(len(episodes)), details={"ongoing": ongoing})


@metric(
    id="time_underwater_pct",
    name="Time under water",
    category="drawdown",
    unit="fraction",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Share of periods in which wealth was below its previous peak.",
        formula="(1/n) * #{t : D_t < 0}",
        formula_latex=r"\mathrm{TUW} = \frac{1}{n} \#\{t \in 1..n : D_t < 0\}",
        inputs="Periodic simple returns.",
        retail="The share of the time the investment was below a previous high.",
        institutional="Complements depth measures with persistence; high values with shallow "
        "drawdowns indicate grinding rather than crash risk.",
        assumptions=("Wealth index starts at 1 before the first return.",),
        misleading_when=(_PATH_CAVEAT,),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(),
        references=(BACON,),
        convention="Counted over observations 1..n (the inception point is excluded).",
    ),
)
def time_underwater_pct(ctx: MetricContext) -> float:
    return float(np.mean(ctx.cache.drawdown < 0.0))


@metric(
    id="ulcer_index",
    name="Ulcer Index",
    category="drawdown",
    unit="decimal_return",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Root-mean-square drawdown: combines depth and duration of declines.",
        formula="sqrt( (1/n) * sum_t D_t^2 )",
        formula_latex=r"\mathrm{UI} = \sqrt{\frac{1}{n} \sum_{t=1}^{n} D_t^2}",
        inputs="Periodic simple returns.",
        retail="A single number for how deep and how long-lasting the declines were; 0 means "
        "the investment never fell below a previous high.",
        institutional="Martin & McCann's Ulcer Index on the canonical drawdown path; the "
        "denominator of the Martin ratio (Ulcer Performance Index).",
        assumptions=("Drawdowns measured from running peaks of compounded wealth.",),
        misleading_when=(_PATH_CAVEAT, "Compared across data frequencies."),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(
            lib(
                PA,
                "UlcerIndex",
                agrees=False,
                note="PerformanceAnalytics 2.0.4 builds drawdowns with DrawdownPeak, which "
                "divides returns by 100 (assumes percent inputs); agreement is verified "
                "against sqrt(mean(Drawdowns(R)^2)) instead.",
            ),
        ),
        references=(MARTIN_MCCANN_1989, BACON),
        convention="Non-negative magnitude in decimal units, computed from the canonical "
        "drawdown path over observations 1..n.",
    ),
)
def ulcer_index(ctx: MetricContext) -> float:
    return ctx.cache.ulcer_index


@metric(
    id="pain_index",
    name="Pain Index",
    category="drawdown",
    unit="decimal_return",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Average drawdown over time (mean absolute drawdown across all periods).",
        formula="(1/n) * sum_t |D_t|",
        formula_latex=r"\mathrm{PI} = \frac{1}{n} \sum_{t=1}^{n} \left| D_t \right|",
        inputs="Periodic simple returns.",
        retail="How far below its previous high the investment was, on average, over the whole "
        "history.",
        institutional="Zephyr Pain Index (see Bacon); time-weighted, unlike the episode-based "
        "average drawdown.",
        assumptions=("Drawdowns measured from running peaks of compounded wealth.",),
        misleading_when=(_PATH_CAVEAT,),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(
            lib(
                PA,
                "PainIndex",
                agrees=False,
                note="Same DrawdownPeak percent-input issue as UlcerIndex; verified against "
                "mean(|Drawdowns(R)|).",
            ),
        ),
        references=(BACON,),
        convention="Non-negative magnitude in decimal units over observations 1..n.",
    ),
)
def pain_index(ctx: MetricContext) -> float:
    return float(np.mean(np.abs(ctx.cache.drawdown)))


_EPISODE_REFS = (
    lib(
        PA,
        "findDrawdowns / table.Drawdowns",
        note="Agrees on the episode table; PerformanceAnalytics counts an episode still open "
        "at the end of the data one period longer.",
    ),
)


@metric(
    id="median_drawdown",
    name="Median drawdown (per episode)",
    category="drawdown",
    unit="decimal_return",
    direction="higher_is_better",
    signed_loss=True,
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Median depth of the distinct drawdown episodes.",
        formula="median_k depth_k over K episodes (0 if K = 0)",
        formula_latex=(
            r"\widetilde{\mathrm{DD}} = \operatorname{med}\left(\delta_1, \dots, \delta_K\right),"
            r" \quad 0 \text{ if } K = 0"
        ),
        inputs="Periodic simple returns.",
        retail="The depth of a typical decline from a previous high; unlike the average it is not "
        "pulled down by one extreme episode.",
        institutional="Robust counterpart of the episode-based average drawdown; many shallow "
        "episodes make it close to zero.",
        assumptions=("Every decline below a prior peak, however small, is an episode.",),
        misleading_when=(_PATH_CAVEAT, "Few episodes (the median of 1-3 values is fragile)."),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=_EPISODE_REFS,
        references=(BACON,),
        convention="Median of episode depths, signed (decision 0025).",
    ),
)
def median_drawdown(ctx: MetricContext) -> Computed:
    episodes = ctx.cache.episodes
    if not episodes:
        return Computed(0.0, details={"episodes": 0})
    return Computed(
        float(np.median([e.depth for e in episodes])), details={"episodes": len(episodes)}
    )


@metric(
    id="average_drawdown_duration",
    name="Average drawdown duration",
    category="drawdown",
    unit="periods",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Mean time from a peak to recovery (or to the end of the data for an open "
        "episode), across all drawdown episodes.",
        formula="(1/K) * sum_k duration_k, duration as in longest_drawdown_duration (0 if K = 0)",
        formula_latex=(
            r"\bar\ell = \frac{1}{K} \sum_{k=1}^{K} \ell_k, \quad \ell_k = \begin{cases}"
            r" \rho_k - \pi_k & \text{recovered} \\ n - \pi_k & \text{ongoing} \end{cases},"
            r" \quad 0 \text{ if } K = 0"
        ),
        inputs="Periodic simple returns.",
        retail="How long, on average, the investment took to get back to a previous high.",
        institutional="Episode-weighted average duration in observation periods; an open "
        "episode contributes a lower bound (flagged).",
        assumptions=("Recovery means regaining the prior peak of compounded wealth.",),
        misleading_when=(_PATH_CAVEAT, "The longest episodes are still open (lower bound)."),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=_EPISODE_REFS,
        references=(BACON,),
        convention="Peak to recovery inclusive; open episodes measured to the last observation "
        "(decision 0025).",
    ),
)
def average_drawdown_duration(ctx: MetricContext) -> Computed:
    episodes = ctx.cache.episodes
    if not episodes:
        return Computed(0.0, details={"episodes": 0})
    avg = float(np.mean([e.duration_periods for e in episodes]))
    ppy = ctx.returns.periods_per_year
    open_count = sum(1 for e in episodes if not e.recovered)
    notes: tuple[str, ...] = ()
    if open_count:
        notes = (
            "An open drawdown is included up to the last observation; the average is a "
            "lower bound.",
        )
    return Computed(
        avg,
        details={
            "years": avg / ppy if ppy else None,
            "episodes": len(episodes),
            "ongoing": open_count,
        },
        notes=notes,
    )


@metric(
    id="max_peak_to_trough_duration",
    name="Longest decline (peak to trough)",
    category="drawdown",
    unit="periods",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Longest time from a peak to the lowest point of the same drawdown episode.",
        formula="max_k (trough_k - peak_k) in periods (0 if K = 0)",
        formula_latex=(
            r"\max_{1 \le k \le K} \left( \tau_k - \pi_k \right), \quad "
            r"\tau_k = \arg\min_{t \in E_k} D_t \ (\text{first occurrence}), \quad "
            r"0 \text{ if } K = 0"
        ),
        inputs="Periodic simple returns.",
        retail="The longest stretch during which losses kept deepening before the turnaround.",
        institutional="Maximum peak-to-trough length in observation periods; complements the "
        "total duration, which also includes the recovery.",
        assumptions=("The trough is the first period with the episode's minimum drawdown.",),
        misleading_when=(_PATH_CAVEAT, "The deepest point of an open episode may still lie ahead."),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(lib(PA, "findDrawdowns (peaktotrough)"),),
        references=(BACON,),
        convention="Periods from the peak to the trough (decision 0025).",
    ),
)
def max_peak_to_trough_duration(ctx: MetricContext) -> Computed:
    episodes = ctx.cache.episodes
    if not episodes:
        return Computed(0.0, details={"episodes": 0})
    worst = max(episodes, key=lambda e: e.peak_to_trough_periods)
    ppy = ctx.returns.periods_per_year
    return Computed(
        float(worst.peak_to_trough_periods),
        details={
            "years": worst.peak_to_trough_periods / ppy if ppy else None,
            "peak_date": worst.peak_date,
            "trough_date": worst.trough_date,
        },
    )


@metric(
    id="average_recovery_duration",
    name="Average recovery time (trough to recovery)",
    category="drawdown",
    unit="periods",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    assumptions=("drawdown",),
    docs=MetricDocs(
        measures="Mean time from the trough of a drawdown back to the previous peak, over "
        "recovered episodes.",
        formula="mean_k (recovery_k - trough_k) over recovered episodes",
        formula_latex=(
            r"\bar R = \frac{1}{|K_r|} \sum_{k \in K_r} (\rho_k - \tau_k), \quad "
            r"K_r = \{k : \text{episode } k \text{ recovered}\}"
        ),
        undefined_when=("No drawdown episode has recovered (none occurred, or all are open).",),
        inputs="Periodic simple returns.",
        retail="Once the bottom was reached, how long it typically took to climb back to the "
        "previous high.",
        institutional="Average recovery length of completed episodes only; open episodes are "
        "excluded because their recovery time is unknown (disclosed in details).",
        assumptions=("Recovery means regaining the prior peak of compounded wealth.",),
        misleading_when=(
            _PATH_CAVEAT,
            "The deepest episode is still open and therefore excluded.",
        ),
        minimum_data="One recovered episode; low confidence below 3 years.",
        reference_implementations=(lib(PA, "findDrawdowns (recovery)"),),
        references=(BACON,),
        convention="Recovered episodes only (decision 0025).",
    ),
)
def average_recovery_duration(ctx: MetricContext) -> Computed:
    recovered = [e for e in ctx.cache.episodes if e.recovered]
    if not recovered:
        raise UndefinedMetric("No drawdown episode has recovered; recovery time is unknown.")
    avg = float(np.mean([e.recovery_periods for e in recovered if e.recovery_periods is not None]))
    ppy = ctx.returns.periods_per_year
    open_count = len(ctx.cache.episodes) - len(recovered)
    notes: tuple[str, ...] = ()
    if open_count:
        notes = (f"{open_count} open episode(s) excluded: their recovery time is unknown.",)
    return Computed(
        avg,
        details={
            "years": avg / ppy if ppy else None,
            "recovered_episodes": len(recovered),
            "excluded_open_episodes": open_count,
        },
        notes=notes,
    )


def _drawdown_alpha(ctx: MetricContext) -> float:
    return 1.0 - float(ctx.methodology.get("drawdown_risk.confidence"))


_DD_TAIL_CAVEATS = (
    _PATH_CAVEAT,
    "Drawdown observations are strongly serially dependent: the 5% tail of the drawdown path "
    "often comes from a single episode.",
)


@metric(
    id="drawdown_at_risk_95",
    name="Drawdown-at-Risk (95%)",
    category="drawdown",
    unit="decimal_return",
    direction="higher_is_better",
    signed_loss=True,
    nature="estimated",
    min_data_policy="tail",
    uses_wealth_path=True,
    assumptions=("drawdown", "tail"),
    docs=MetricDocs(
        measures="Drawdown level that was exceeded in the worst 5% of periods.",
        formula="Q_0.05(D_1..D_n), linear interpolation (signed)",
        formula_latex=r"\mathrm{DaR}_{95} = Q_{0.05}\left(D_1, \dots, D_n\right)",
        inputs="Periodic simple returns.",
        retail="In about 1 period out of 20 the investment was at least this far below its "
        "previous high.",
        institutional="Drawdown-at-Risk (Chekhlov, Uryasev & Zabarankin 2005) on the compounded "
        "drawdown path, with the same linear quantile as historical VaR.",
        assumptions=("Drawdowns of all periods 1..n form the sample (inception excluded).",),
        misleading_when=_DD_TAIL_CAVEATS,
        minimum_data="At least 2 observations; low confidence below n = 100.",
        reference_implementations=(
            lib(
                SKFOLIO,
                "measures.drawdown_at_risk (compounded drawdowns)",
                agrees=False,
                note="skfolio uses the lower order statistic (inverted-CDF quantile) and, by "
                "default, uncompounded drawdowns.",
            ),
        ),
        references=(CHEKHLOV_2005,),
        convention="Compounded drawdowns, linear quantile, signed (decision 0021).",
    ),
)
def drawdown_at_risk_95(ctx: MetricContext) -> float:
    return float(np.quantile(ctx.cache.drawdown, _drawdown_alpha(ctx), method="linear"))


@metric(
    id="cdar_95",
    name="Conditional Drawdown-at-Risk (95%)",
    category="drawdown",
    unit="decimal_return",
    direction="higher_is_better",
    signed_loss=True,
    nature="estimated",
    min_data_policy="tail",
    uses_wealth_path=True,
    assumptions=("drawdown", "tail"),
    docs=MetricDocs(
        measures="Average drawdown in the worst 5% of periods.",
        formula="mean(D_t | D_t <= Q_0.05(D))",
        formula_latex=(
            r"\mathrm{CDaR}_{95} = \frac{1}{|T|} \sum_{t \in T} D_t, \quad "
            r"T = \{t \in 1..n : D_t \le Q_{0.05}(D)\}"
        ),
        inputs="Periodic simple returns.",
        retail="How deep the drawdowns were, on average, during the worst 5% of periods.",
        institutional="CDaR (Chekhlov, Uryasev & Zabarankin 2005): Expected Shortfall of the "
        "drawdown path, a coherent path-dependent risk measure between DaR and the maximum "
        "drawdown. Estimated exactly like historical ES (decision 0010).",
        assumptions=("Drawdowns of all periods 1..n form the sample (inception excluded).",),
        misleading_when=_DD_TAIL_CAVEATS,
        minimum_data="At least 2 observations; low confidence below n = 100.",
        reference_implementations=(
            lib(
                SKFOLIO,
                "measures.cdar (compounded drawdowns)",
                note="Agrees when (1 - 0.95) x n is an integer; otherwise skfolio's fractional "
                "Rockafellar-Uryasev weighting differs slightly.",
            ),
            lib(
                PA,
                "CDD",
                agrees=False,
                note="PerformanceAnalytics' 'Conditional Drawdown' is the 5% quantile over all "
                "findDrawdowns runs (episodes and zero runs), not a conditional expectation of "
                "the drawdown path.",
            ),
        ),
        references=(CHEKHLOV_2005,),
        convention="Compounded drawdowns; mean of observations at or below the linear 5% "
        "quantile; signed (decision 0021).",
    ),
)
def cdar_95(ctx: MetricContext) -> Computed:
    d = ctx.cache.drawdown
    q = float(np.quantile(d, _drawdown_alpha(ctx), method="linear"))
    tail = d[d <= q]
    return Computed(float(np.mean(tail)), details={"tail_observations": int(tail.size)})


@metric(
    id="edar_95",
    name="Entropic Drawdown-at-Risk (95%)",
    category="drawdown",
    unit="decimal_return",
    direction="higher_is_better",
    signed_loss=True,
    nature="estimated",
    min_data_policy="tail",
    uses_wealth_path=True,
    assumptions=("drawdown", "entropic"),
    docs=MetricDocs(
        measures="Entropic (exponential-moment) upper bound on the drawdown tail at 95%.",
        formula="-EVaR_0.05(-D), EVaR_a(X) = inf_{z>0} z * ln( mean(exp(X/z)) / a )",
        formula_latex=(
            r"\mathrm{EDaR}_{95} = -\mathrm{EVaR}_{0.05}(-D), \quad "
            r"\mathrm{EVaR}_{a}(X) = \inf_{z > 0} \, z \ln\!\left( \frac{1}{a\,n} "
            r"\sum_{t=1}^{n} e^{X_t / z} \right)"
        ),
        inputs="Periodic simple returns.",
        retail="A conservative measure of how deep drawdowns get, sitting between the "
        "Conditional Drawdown-at-Risk and the maximum drawdown.",
        institutional="EDaR (Cajas 2021): Entropic VaR (Ahmadi-Javid 2012) of the drawdown "
        "magnitudes; the tightest Chernoff-type bound on DaR, coherent and more tail-sensitive "
        "than CDaR. Computed by one-dimensional convex minimization.",
        assumptions=("Drawdowns of all periods 1..n form the sample (inception excluded).",),
        misleading_when=(
            *_DD_TAIL_CAVEATS,
            "With 20 or fewer observations (n <= 1/0.05) the empirical EDaR equals the maximum "
            "drawdown exactly.",
        ),
        minimum_data="At least 2 observations; low confidence below n = 100.",
        reference_implementations=(
            lib(
                SKFOLIO,
                "measures.edar (compounded drawdowns)",
                note="Agrees to solver tolerance (about 1e-8).",
            ),
        ),
        references=(CAJAS_2021, AHMADI_JAVID_2012),
        convention="Compounded drawdowns, 95%, signed (decision 0021).",
    ),
)
def edar_95(ctx: MetricContext) -> float:
    alpha = 1.0 - float(ctx.methodology.get("entropic.confidence"))
    return -entropic_value_at_risk(-ctx.cache.drawdown, alpha)
