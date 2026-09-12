# 0026 — Canonical charts and the drawdown-episode table

**Status:** Accepted — methodology 0.1.0

## Problem

Charts are where selective presentation is easiest: a start date that skips a
crash, a truncated value axis that turns a 2% difference into a cliff, a
log scale that flattens a drawdown, a heatmap whose red is paler than its
blue, or a "top drawdowns" table that quietly shows the recent ones. The
canonical report needs charts, but every presentation choice that changes what a
reader sees must be fixed by the methodology, not by the report author.

## Known definitions

There is no academic standard for factsheet charts. Practitioner tear sheets
converge on the same set:

| Chart | pyfolio-reloaded | QuantStats | PerformanceAnalytics |
|---|---|---|---|
| Cumulative wealth | `plot_rolling_returns` (log option) | `snapshot`, `returns` (log option) | `chart.CumReturns` (`wealth.index`) |
| Underwater / drawdown | `plot_drawdown_underwater` | `drawdown` | `chart.Drawdown` |
| Top drawdown episodes | `show_worst_drawdown_periods` (top 5) | `drawdown_details` (all) | `table.Drawdowns` (top 5) |
| Calendar-year returns | `plot_annual_returns` | `yearly_returns` | `table.CalendarReturns` |
| Monthly heatmap | `plot_monthly_returns_heatmap` | `monthly_heatmap` | `table.CalendarReturns` |
| Return distribution | `plot_monthly_returns_dist` | `histogram`, `distribution` | `chart.Histogram` |
| Rolling statistics | rolling volatility, Sharpe, beta | rolling volatility, Sharpe, Sortino, beta | `charts.RollingPerformance` |

## PerformanceAnalytics behavior

`chart.CumReturns` plots `cumprod(1 + r)` from the first return (optionally
with `begin = "axis"` to align series); `chart.Drawdown` plots the same
compounded drawdown path OpenFactsheet uses ([0007](0007-drawdown-conventions.md));
`table.Drawdowns(top = 5)` sorts episodes by depth. Reported in library docs,
not verified numerically here (charts are presentation of values validated
elsewhere).

## QuantStats behavior

The monthly heatmap uses a diverging colormap centred on zero but scaled to the
data range, so the color for a loss and an equal gain can differ when the range
is asymmetric. Cumulative-return plots offer a log scale and "compounded" or
"summed" modes. Reported in library docs, not verified here.

## Empyrical behavior

Empyrical has no charts; pyfolio-reloaded (built on it) shows the five worst
drawdown periods and a log-scale option for cumulative returns.

## Academic sources

- Tufte, E. R. (2001). *The Visual Display of Quantitative Information* (2nd ed.) — the
  lie factor; data-ink.
- Cleveland, W. S., & McGill, R. (1984). Graphical Perception. *JASA* 79(387) — position
  on a common scale is read most accurately; length requires a zero baseline.
- Freedman, D., & Diaconis, P. (1981). On the histogram as a density estimator.
  *Z. Wahrscheinlichkeitstheorie* 57 — bin width $2\,\mathrm{IQR}\,n^{-1/3}$.
- CFA Institute, *Global Investment Performance Standards* (2020) — presentation of
  the full track record and of every required period.

## OpenFactsheet decision

Eight charts, always in this order, each either drawn or replaced by a sentence
stating why it cannot be drawn:

1. **Growth of 1** — the canonical wealth index $W_0 = 1, W_t = \prod_{s \le t}(1 + r_s)$
   over the full history, linear scale.
2. **Calendar-year returns** — complete years from the calendar-year engine
   ([0023](0023-calendar-year-statistics.md)); partial years are drawn outlined,
   marked `*` and captioned with their coverage; bars grow from 0%.
3. **Monthly returns** (dated monthly data only) — every month, empty cells for
   missing months, a diverging scale **symmetric** at $\pm\max_t |r_t|$ and a
   compounded Year column.
4. **Rolling one-year volatility** — annualized sample standard deviation over the
   one-year windows of [0024](0024-rolling-one-year-windows.md); the value axis
   includes 0.
5. **Underwater chart** — the canonical drawdown path $D_t$ (including inception),
   with the maximum drawdown marked.
6. **Distribution of returns** — every return counted (no trimming), Freedman–Diaconis
   bin width clipped to 10–40 bins, bin edges aligned at 0% so no bin mixes gains and
   losses, a normal curve with the sample mean and volatility, and the historical 95%
   VaR marked.
7. **Rolling one-year return** — exactly the window returns behind
   `best_rolling_year`, `worst_rolling_year` and `positive_rolling_year_pct`.
8. **Growth of 1 over the benchmark overlap** — only the aligned periods
   ([0012](0012-benchmark-alignment-and-relative-metrics.md)), both series rebased to 1
   immediately before the first common period, one linear axis; not drawn without a
   benchmark.

Rules common to all charts:

- the full analyzed history is shown; no start or end date is chosen;
- linear value scales; bars and magnitudes (volatility, counts) always include 0;
- one value axis per chart; straight segments between observations (no smoothing);
- identity colors (fund, benchmark) and polarity colors (gain, loss) are fixed theme
  tokens, validated for color-vision deficiency, in light and dark themes;
- every chart has a caption stating period, observation count and the conventions
  above, plus a data table with every plotted value; hover tooltips only repeat
  values that are also shown;
- when serial correlation suggests smoothing ([0014](0014-smoothing-risk.md)), the
  wealth and rolling-volatility captions say the path may look smoother than the
  underlying value changes;
- the HTML file is self-contained: no external scripts, fonts or images.

**Drawdown-episode table.** Every renderer (terminal, Markdown, HTML) lists the
**10 deepest** episodes of the canonical episode engine, deepest first, ties broken by
the earlier peak, with peak, trough and recovery dates, depth and the three durations
in periods; open episodes are labelled. The caption states how many episodes exist in
total; the JSON report lists all of them.

## Rationale

Every chart is a view of a quantity the metric engine already computes, so a chart can
never disagree with the table beside it and adds no new tunable. The conventions that
most often mislead — truncated axes, asymmetric color scales, log scales hiding
drawdowns, dropped outliers, omitted partial years, a benchmark drawn from a flattering
start — are fixed rather than left to the report author. Sorting episodes by depth
means a limited table can only omit shallower episodes, never a deeper one. A linear
scale is chosen over log because the audience includes retail investors and because
the underwater chart already shows proportional losses.

## Consequences

- Long, strongly compounding histories look back-loaded on the linear wealth chart;
  the underwater chart and calendar-year bars show the proportional picture.
- The heatmap of a series with one extreme month looks pale elsewhere; that is the
  honest consequence of a symmetric, data-wide scale.
- Charts are not drawn in Markdown or terminal output; those renderers point to the
  HTML report and `report.charts()` (SVG strings keyed by chart id).
- Adding, removing or restyling a canonical chart in a way that changes what is shown
  is a methodology change.
