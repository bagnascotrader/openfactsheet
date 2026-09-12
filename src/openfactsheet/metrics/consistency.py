"""Consistency metrics (CLAUDE.md section 12.8)."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.metrics.references import BACON, GIPS, PA, QS, lib
from openfactsheet.metrics.registry import metric
from openfactsheet.models.metric import Computed, MetricDocs


def _longest_run(mask: npt.NDArray[np.bool_]) -> int:
    longest = current = 0
    for flag in mask:
        current = current + 1 if flag else 0
        longest = max(longest, current)
    return longest


@metric(
    id="positive_period_pct",
    name="Positive periods",
    category="consistency",
    unit="fraction",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="location",
    docs=MetricDocs(
        measures="Share of periods with a strictly positive return (hit rate).",
        formula="#{t : r_t > 0} / n",
        formula_latex=r"\mathrm{Pos} = \frac{1}{n} \#\{t : r_t > 0\}",
        inputs="Periodic simple returns.",
        retail="How often the investment made money in a period.",
        institutional="Win rate on the supplied frequency; says nothing about the size of wins "
        "and losses (see gain-to-pain, Omega). A very high hit rate with small gains can mask "
        "rare large losses.",
        assumptions=("Zero returns count as neither positive nor negative.",),
        misleading_when=(
            "Returns are smoothed or stale, which inflates the share of small positive periods.",
        ),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(
            lib(
                QS,
                "stats.win_rate",
                agrees=False,
                note="QuantStats excludes zero-return periods from the denominator.",
            ),
        ),
        references=(BACON,),
        convention="Denominator includes all observations (zeros count as not positive).",
    ),
)
def positive_period_pct(ctx: MetricContext) -> float:
    return float(np.mean(ctx.r > 0.0))


@metric(
    id="negative_period_pct",
    name="Negative periods",
    category="consistency",
    unit="fraction",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="location",
    docs=MetricDocs(
        measures="Share of periods with a strictly negative return.",
        formula="#{t : r_t < 0} / n",
        formula_latex=r"\mathrm{Neg} = \frac{1}{n} \#\{t : r_t < 0\}",
        inputs="Periodic simple returns.",
        retail="How often the investment lost money in a period.",
        institutional="Loss frequency on the supplied frequency; together with positive "
        "periods it also reveals the share of exactly-zero periods.",
        assumptions=("Zero returns count as neither positive nor negative.",),
        misleading_when=("Returns are smoothed or stale.",),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(),
        references=(BACON,),
        convention="Denominator includes all observations.",
    ),
)
def negative_period_pct(ctx: MetricContext) -> float:
    return float(np.mean(ctx.r < 0.0))


@metric(
    id="longest_winning_streak",
    name="Longest run of positive periods",
    category="consistency",
    unit="periods",
    direction="neutral",
    nature="observed",
    min_data_policy="path_risk",
    docs=MetricDocs(
        measures="Maximum number of consecutive periods with positive returns.",
        formula="max length of consecutive runs with r_t > 0",
        formula_latex=(
            r"\max \{ j - i + 1 : 1 \le i \le j \le n,\ r_u > 0 \ \forall u \in i..j \}"
            r" \ (0 \text{ if no } r_t > 0)"
        ),
        inputs="Periodic simple returns.",
        retail="The longest stretch of back-to-back gaining periods.",
        institutional="Descriptive path statistic; unusually long streaks relative to the hit "
        "rate can indicate smoothing.",
        assumptions=(),
        misleading_when=("Compared across frequencies or history lengths.",),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(lib(QS, "stats.consecutive_wins"),),
        references=(BACON,),
        convention="Strictly positive returns only.",
    ),
)
def longest_winning_streak(ctx: MetricContext) -> float:
    return float(_longest_run(ctx.r > 0.0))


@metric(
    id="longest_losing_streak",
    name="Longest run of negative periods",
    category="consistency",
    unit="periods",
    direction="lower_is_better",
    nature="observed",
    min_data_policy="path_risk",
    docs=MetricDocs(
        measures="Maximum number of consecutive periods with negative returns.",
        formula="max length of consecutive runs with r_t < 0",
        formula_latex=(
            r"\max \{ j - i + 1 : 1 \le i \le j \le n,\ r_u < 0 \ \forall u \in i..j \}"
            r" \ (0 \text{ if no } r_t < 0)"
        ),
        inputs="Periodic simple returns.",
        retail="The longest stretch of back-to-back losing periods.",
        institutional="Descriptive path statistic complementing drawdown duration.",
        assumptions=(),
        misleading_when=("Compared across frequencies or history lengths.",),
        minimum_data="One observation; low confidence below 3 years.",
        reference_implementations=(lib(QS, "stats.consecutive_losses"),),
        references=(BACON,),
        convention="Strictly negative returns only.",
    ),
)
def longest_losing_streak(ctx: MetricContext) -> float:
    return float(_longest_run(ctx.r < 0.0))


# --- Calendar years (decision 0023) -----------------------------------------

_CALENDAR_CAVEATS = (
    "Few complete calendar years: one or two years say little about consistency.",
    "Calendar boundaries are arbitrary: a loss straddling two years is split between them.",
)
_CALENDAR_REFS = (
    lib(
        PA,
        "apply.yearly(R, Return.cumulative) on complete years",
        note="Agrees on complete years; OpenFactsheet excludes partial first and last years.",
    ),
)
_CALENDAR_LATEX_YEARS = (
    r"R_y = \prod_{t \in y} (1 + r_t) - 1 \ \text{ for each complete calendar year } y \in Y"
)


def _years_details(ctx: MetricContext) -> dict[str, object]:
    cy = ctx.calendar_years
    return {
        "calendar_year_returns": {str(y): v for y, v in cy.complete.items()},
        "excluded_partial_years": {str(y): why for y, why in cy.partial.items()},
    }


def _complete_years(ctx: MetricContext) -> dict[int, float]:
    cy = ctx.calendar_years
    if not cy.complete:
        partial = ", ".join(f"{y} ({why})" for y, why in cy.partial.items())
        raise UndefinedMetric(f"No complete calendar year in the history; partial: {partial}.")
    return cy.complete


def _partial_note(ctx: MetricContext) -> tuple[str, ...]:
    partial = ctx.calendar_years.partial
    if not partial:
        return ()
    listed = ", ".join(f"{y} ({why})" for y, why in partial.items())
    return (f"Partial calendar years excluded: {listed}.",)


@metric(
    id="best_calendar_year",
    name="Best calendar year",
    category="consistency",
    unit="decimal_return",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    docs=MetricDocs(
        measures="Highest compounded return of any complete calendar year.",
        formula="max over complete years y of prod_{t in y} (1 + r_t) - 1",
        formula_latex=r"\max_{y \in Y} R_y, \quad " + _CALENDAR_LATEX_YEARS,
        undefined_when=(
            "No complete calendar year is covered by the history.",
            "The returns are undated or the frequency is irregular.",
        ),
        inputs="Dated periodic simple returns with a regular frequency.",
        retail="The best full January-to-December year.",
        institutional="Maximum complete-calendar-year return; partial first and last years are "
        "excluded and listed in the details, together with every complete year's return.",
        assumptions=("Only complete calendar years are used.",),
        misleading_when=_CALENDAR_CAVEATS,
        minimum_data="One complete calendar year; low confidence below 3 years of history.",
        reference_implementations=_CALENDAR_REFS,
        references=(GIPS, BACON),
        convention="Complete years only; compounded monthly/quarterly/daily returns "
        "(decision 0023).",
    ),
)
def best_calendar_year(ctx: MetricContext) -> Computed:
    years = _complete_years(ctx)
    year = max(years, key=lambda y: years[y])
    return Computed(
        years[year], details={"year": year, **_years_details(ctx)}, notes=_partial_note(ctx)
    )


@metric(
    id="worst_calendar_year",
    name="Worst calendar year",
    category="consistency",
    unit="decimal_return",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    docs=MetricDocs(
        measures="Lowest compounded return of any complete calendar year.",
        formula="min over complete years y of prod_{t in y} (1 + r_t) - 1",
        formula_latex=r"\min_{y \in Y} R_y, \quad " + _CALENDAR_LATEX_YEARS,
        undefined_when=(
            "No complete calendar year is covered by the history.",
            "The returns are undated or the frequency is irregular.",
        ),
        inputs="Dated periodic simple returns with a regular frequency.",
        retail="The worst full January-to-December year.",
        institutional="Minimum complete-calendar-year return; always shown, including when it "
        "is unfavorable.",
        assumptions=("Only complete calendar years are used.",),
        misleading_when=_CALENDAR_CAVEATS,
        minimum_data="One complete calendar year; low confidence below 3 years of history.",
        reference_implementations=_CALENDAR_REFS,
        references=(GIPS, BACON),
        convention="Complete years only (decision 0023).",
    ),
)
def worst_calendar_year(ctx: MetricContext) -> Computed:
    years = _complete_years(ctx)
    year = min(years, key=lambda y: years[y])
    return Computed(years[year], details={"year": year}, notes=_partial_note(ctx))


@metric(
    id="positive_calendar_years_pct",
    name="Positive calendar years",
    category="consistency",
    unit="fraction",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="path_risk",
    uses_wealth_path=True,
    docs=MetricDocs(
        measures="Share of complete calendar years with a positive compounded return.",
        formula="#{y : R_y > 0} / #Y over complete calendar years",
        formula_latex=r"\frac{\#\{y \in Y : R_y > 0\}}{|Y|}, \quad " + _CALENDAR_LATEX_YEARS,
        undefined_when=(
            "No complete calendar year is covered by the history.",
            "The returns are undated or the frequency is irregular.",
        ),
        inputs="Dated periodic simple returns with a regular frequency.",
        retail="How many full years ended with a gain.",
        institutional="Calendar-year hit rate; the details list every complete year's return "
        "and every excluded partial year.",
        assumptions=("Only complete calendar years are used.",),
        misleading_when=_CALENDAR_CAVEATS,
        minimum_data="One complete calendar year; low confidence below 3 years of history.",
        reference_implementations=_CALENDAR_REFS,
        references=(GIPS, BACON),
        convention="Complete years only; a zero year counts as not positive (decision 0023).",
    ),
)
def positive_calendar_years_pct(ctx: MetricContext) -> Computed:
    years = _complete_years(ctx)
    positive = sum(1 for v in years.values() if v > 0.0)
    return Computed(
        positive / len(years),
        details={"complete_years": len(years), "positive_years": positive, **_years_details(ctx)},
        notes=_partial_note(ctx),
    )


# --- Rolling one-year windows (decision 0024) ------------------------------

_ROLLING_CAVEATS = (
    "Overlapping windows share observations, so rolling statistics are strongly "
    "autocorrelated and overstate the amount of independent evidence.",
    "Gaps in the history make a window span more than one calendar year.",
)
_ROLLING_LATEX = (
    r"R^{(w)}_t = \prod_{i=t-w+1}^{t} (1 + r_i) - 1, \quad t = w, \dots, n, \quad "
    r"w = \operatorname{round}(P)"
)


def _window_end(ctx: MetricContext, pos: int, window: int) -> str | None:
    dates = ctx.returns.dates
    return dates[pos + window - 1].strftime("%Y-%m-%d") if dates is not None else None


@metric(
    id="best_rolling_year",
    name="Best rolling one-year return",
    category="consistency",
    unit="decimal_return",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="path_risk",
    annualized=True,
    uses_wealth_path=True,
    assumptions=("annualization",),
    docs=MetricDocs(
        measures="Highest compounded return over any window of one year of consecutive "
        "observations.",
        formula="max_t prod_{i=t-w+1..t} (1 + r_i) - 1, w = round(P)",
        formula_latex=r"\max_{w \le t \le n} R^{(w)}_t, \quad " + _ROLLING_LATEX,
        undefined_when=("Fewer observations than one year (n < w).",),
        inputs="Periodic simple returns with a regular frequency.",
        retail="The best twelve months (or one year of periods) an investor could have "
        "experienced, whatever the start date.",
        institutional="Maximum of all overlapping one-year compounded returns; every start "
        "date is considered, so no favorable start date can be chosen.",
        assumptions=("Window = one year of observations, step = one observation.",),
        misleading_when=_ROLLING_CAVEATS,
        minimum_data="One full window (n >= P); low confidence below 3 years.",
        reference_implementations=(lib(PA, "rollapply(R, P, Return.cumulative)"),),
        references=(BACON,),
        convention="Window round(P) observations, step 1 (decision 0024).",
    ),
)
def best_rolling_year(ctx: MetricContext) -> Computed:
    rolled, window = ctx.rolling_year_returns
    pos = int(np.argmax(rolled))
    return Computed(
        float(rolled[pos]),
        details={
            "window_end": _window_end(ctx, pos, window),
            "windows": int(rolled.size),
            "window_periods": window,
        },
    )


@metric(
    id="worst_rolling_year",
    name="Worst rolling one-year return",
    category="consistency",
    unit="decimal_return",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="path_risk",
    annualized=True,
    uses_wealth_path=True,
    assumptions=("annualization",),
    docs=MetricDocs(
        measures="Lowest compounded return over any window of one year of consecutive "
        "observations.",
        formula="min_t prod_{i=t-w+1..t} (1 + r_i) - 1, w = round(P)",
        formula_latex=r"\min_{w \le t \le n} R^{(w)}_t, \quad " + _ROLLING_LATEX,
        undefined_when=("Fewer observations than one year (n < w).",),
        inputs="Periodic simple returns with a regular frequency.",
        retail="The worst twelve months (or one year of periods) an investor could have "
        "experienced, whatever the start date.",
        institutional="Minimum of all overlapping one-year compounded returns; a start-date-"
        "free worst case that is often much worse than the worst calendar year.",
        assumptions=("Window = one year of observations, step = one observation.",),
        misleading_when=_ROLLING_CAVEATS,
        minimum_data="One full window (n >= P); low confidence below 3 years.",
        reference_implementations=(lib(PA, "rollapply(R, P, Return.cumulative)"),),
        references=(BACON,),
        convention="Window round(P) observations, step 1 (decision 0024).",
    ),
)
def worst_rolling_year(ctx: MetricContext) -> Computed:
    rolled, window = ctx.rolling_year_returns
    pos = int(np.argmin(rolled))
    return Computed(
        float(rolled[pos]),
        details={
            "window_end": _window_end(ctx, pos, window),
            "windows": int(rolled.size),
            "window_periods": window,
        },
    )


@metric(
    id="positive_rolling_year_pct",
    name="Positive rolling one-year windows",
    category="consistency",
    unit="fraction",
    direction="higher_is_better",
    nature="observed",
    min_data_policy="path_risk",
    annualized=True,
    uses_wealth_path=True,
    assumptions=("annualization",),
    docs=MetricDocs(
        measures="Share of all one-year windows (every start date) with a positive compounded "
        "return.",
        formula="#{t : R_t^(w) > 0} / (n - w + 1), w = round(P)",
        formula_latex=(r"\frac{\#\{t : R^{(w)}_t > 0\}}{n - w + 1}, \quad " + _ROLLING_LATEX),
        undefined_when=("Fewer observations than one year (n < w).",),
        inputs="Periodic simple returns with a regular frequency.",
        retail="If you had invested at any point and held for one year, how often you would "
        "have ended with a gain.",
        institutional="Rolling one-year hit rate over all start dates. Windows overlap, so it is "
        "a descriptive statistic, not a probability estimate.",
        assumptions=("Window = one year of observations, step = one observation.",),
        misleading_when=_ROLLING_CAVEATS,
        minimum_data="One full window (n >= P); low confidence below 3 years.",
        reference_implementations=(lib(PA, "rollapply(R, P, Return.cumulative)"),),
        references=(BACON,),
        convention="Window round(P) observations, step 1; zero counts as not positive "
        "(decision 0024).",
    ),
)
def positive_rolling_year_pct(ctx: MetricContext) -> Computed:
    rolled, window = ctx.rolling_year_returns
    return Computed(
        float(np.mean(rolled > 0.0)),
        details={"windows": int(rolled.size), "window_periods": window},
    )
