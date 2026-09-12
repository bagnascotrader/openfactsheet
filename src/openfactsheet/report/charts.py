"""Canonical charts, rendered as static, self-contained SVG (decision 0026).

Charts are presentation only: every value is computed by the same engine as the
metrics (wealth and drawdown path, calendar years, rolling windows), so a chart
can never disagree with the numbers beside it.

Honesty rules enforced here (and tested):

* every chart spans the full analyzed history; no start date is chosen;
* bars grow from zero and every value axis for bars or magnitudes includes zero;
* one value axis per chart (never a dual axis);
* straight line segments between observations (no smoothing);
* the monthly heatmap scale is symmetric, so a loss is as saturated as an equal gain;
* partial calendar years are shown, outlined and labelled, never styled as full years;
* the histogram contains every return (no outlier trimming) with a normal overlay;
* a benchmark is compared only over the aligned overlap, both rebased at its start;
* every chart has a text caption and a data table (tooltips never gate a value).

Colors are CSS custom properties resolved by the HTML report (light and dark),
validated for color-vision deficiency: identity uses categorical slots 1 and 2
(fund blue, benchmark orange); polarity uses the blue/red diverging pair around a
neutral gray midpoint.
"""

from __future__ import annotations

import json
import math
import zlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from html import escape
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt
import pandas as pd

from openfactsheet.exceptions import UndefinedMetric
from openfactsheet.metrics.context import MetricContext
from openfactsheet.models.input import ObservationFrequency

if TYPE_CHECKING:
    from openfactsheet.models.report import FactsheetReport

# Geometry (SVG user units; the SVG scales to its container through the viewBox).
WIDTH = 760.0
PLOT_HEIGHT = 250.0
MARGIN_LEFT = 58.0
MARGIN_RIGHT = 96.0  # room for direct end labels
MARGIN_TOP = 18.0
MARGIN_BOTTOM = 34.0
BAR_MAX_WIDTH = 24.0
BAR_RADIUS = 4.0
MINUS = "−"


@dataclass(frozen=True)
class Chart:
    """One canonical chart: SVG plus the text needed to read it without the picture."""

    id: str
    section: str  # report section (category) the chart belongs to
    title: str
    caption: str
    svg: str = ""
    table_header: tuple[str, ...] = ()
    table_rows: tuple[tuple[str, ...], ...] = ()
    unavailable_reason: str | None = None
    legend: tuple[tuple[str, str], ...] = field(default_factory=tuple)  # (css var, label)


# --- formatting --------------------------------------------------------------


def _pct(x: float, decimals: int = 1, signed: bool = True) -> str:
    text = f"{abs(x) * 100:.{decimals}f}%"
    if x < 0 and round(abs(x) * 100, decimals) != 0:
        return MINUS + text
    return ("+" + text) if signed and x > 0 else text


def _num(x: float, decimals: int = 2) -> str:
    text = f"{abs(x):.{decimals}f}"
    return (MINUS + text) if x < 0 and round(abs(x), decimals) != 0 else text


def _date(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%d")


# --- scales and ticks ----------------------------------------------------------


@dataclass(frozen=True)
class LinearScale:
    d0: float
    d1: float
    r0: float
    r1: float

    def __call__(self, v: float) -> float:
        if self.d1 == self.d0:
            return (self.r0 + self.r1) / 2
        return self.r0 + (v - self.d0) / (self.d1 - self.d0) * (self.r1 - self.r0)


def nice_ticks(lo: float, hi: float, target: int = 5) -> list[float]:
    """Round tick values (1-2-2.5-5 steps) covering [lo, hi]."""
    if hi <= lo:
        hi = lo + (abs(lo) if lo else 1.0)
    raw = (hi - lo) / target
    magnitude = 10 ** math.floor(math.log10(raw))
    step = magnitude
    for m in (1.0, 2.0, 2.5, 5.0, 10.0):
        if raw <= m * magnitude:
            step = m * magnitude
            break
    first = math.ceil(lo / step - 1e-9) * step
    ticks = []
    v = first
    while v <= hi + step * 1e-9:
        ticks.append(round(v, 12))
        v += step
    return ticks


def _padded(lo: float, hi: float, pad: float = 0.06) -> tuple[float, float]:
    span = hi - lo
    if span <= 0:
        span = abs(hi) if hi else 1.0
    return lo - span * pad, hi + span * pad


def _date_ticks(start: pd.Timestamp, end: pd.Timestamp) -> list[tuple[pd.Timestamp, str]]:
    years = (end - start).days / 365.25
    if years >= 2:
        step = next(s for s in (1, 2, 5, 10, 20, 50) if years / s <= 10)
        first = start.year + (1 if (start.month, start.day) != (1, 1) else 0)
        first += (-first) % step
        return [
            (pd.Timestamp(year=y, month=1, day=1), str(y))
            for y in range(first, end.year + 1, step)
            if start <= pd.Timestamp(year=y, month=1, day=1) <= end
        ]
    months = max(1, round(years * 12))
    step = next(s for s in (1, 2, 3, 6) if months / s <= 8)
    ticks = []
    t = pd.Timestamp(year=start.year, month=start.month, day=1)
    while t <= end:
        if t >= start and (t.month - 1) % step == 0:
            ticks.append((t, t.strftime("%b %Y")))
        t = t + pd.offsets.MonthBegin(1)
    return ticks


# --- SVG primitives ------------------------------------------------------------


def _svg_open(height: float, title: str, desc: str, points: list[object] | None = None) -> str:
    # Deterministic id (Python's hash() is salted per process, which would make the
    # HTML output differ between runs).
    uid = f"ofs-{zlib.crc32(title.encode('utf-8')):08x}"
    data = ""
    if points is not None:
        data = f' data-points="{escape(json.dumps(points, separators=(",", ":")), quote=True)}"'
    return (
        f'<svg class="ofs-chart" viewBox="0 0 {WIDTH:.0f} {height:.0f}" role="img" '
        f'aria-labelledby="{uid}-t {uid}-d" preserveAspectRatio="xMidYMid meet"{data}>'
        f'<title id="{uid}-t">{escape(title)}</title><desc id="{uid}-d">{escape(desc)}</desc>'
    )


def _text(x: float, y: float, s: str, cls: str = "tick", anchor: str = "middle") -> str:
    return f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}">{escape(s)}</text>'


def _hline(y: float, x0: float, x1: float, cls: str) -> str:
    return f'<line class="{cls}" x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}"/>'


def _vline(x: float, y0: float, y1: float, cls: str) -> str:
    return f'<line class="{cls}" x1="{x:.1f}" y1="{y0:.1f}" x2="{x:.1f}" y2="{y1:.1f}"/>'


def _path(xs: Sequence[float], ys: Sequence[float]) -> str:
    return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in zip(xs, ys, strict=True))


def _y_axis(scale: LinearScale, ticks: list[float], fmt: str, x0: float, x1: float) -> str:
    parts = []
    for t in ticks:
        y = scale(t)
        parts.append(_hline(y, x0, x1, "grid"))
        label = (
            _pct(
                t,
                0 if all(abs(v * 100 - round(v * 100)) < 1e-9 for v in ticks) else 1,
                signed=False,
            )
            if fmt.startswith("pct")
            else _num(t, 2)
        )
        parts.append(_text(x0 - 8, y + 4, label, "tick", "end"))
    return "".join(parts)


def _fmt(v: float, y_fmt: str) -> str:
    """Point label: ``pct`` (signed return), ``pct_level`` (unsigned level) or ``num``."""
    if y_fmt == "pct":
        return _pct(v)
    if y_fmt == "pct_level":
        return _pct(v, signed=False)
    return _num(v)


def _bar_path(x: float, w: float, y_base: float, y_end: float) -> str:
    """Column with a 4px rounded data-end and a square baseline."""
    h = abs(y_end - y_base)
    r = min(BAR_RADIUS, h, w / 2)
    if y_end <= y_base:  # grows upward
        return (
            f"M{x:.2f},{y_base:.2f} V{y_end + r:.2f} Q{x:.2f},{y_end:.2f} {x + r:.2f},{y_end:.2f}"
            f" H{x + w - r:.2f} Q{x + w:.2f},{y_end:.2f} {x + w:.2f},{y_end + r:.2f}"
            f" V{y_base:.2f} Z"
        )
    return (
        f"M{x:.2f},{y_base:.2f} V{y_end - r:.2f} Q{x:.2f},{y_end:.2f} {x + r:.2f},{y_end:.2f}"
        f" H{x + w - r:.2f} Q{x + w:.2f},{y_end:.2f} {x + w:.2f},{y_end - r:.2f}"
        f" V{y_base:.2f} Z"
    )


# --- shared data -------------------------------------------------------------------


def _context(report: FactsheetReport) -> MetricContext:
    return MetricContext(
        returns=report.returns, diagnostics=report.diagnostics, methodology=report.assumptions
    )


def _x_positions(report: FactsheetReport) -> tuple[npt.NDArray[np.float64], list[str], bool]:
    """X coordinate (days or index) of the inception point and each observation.

    Returns ``(xs, labels, dated)`` where ``xs`` has length n + 1: the inception point
    (one median spacing before the first observation) followed by each observation.
    """
    series = report.returns
    n = series.n
    if series.dates is None:
        xs = np.arange(n + 1, dtype=np.float64)
        return xs, ["start", *[f"period {i}" for i in range(1, n + 1)]], False
    days = (series.dates - series.dates[0]).days.to_numpy().astype(np.float64)
    gap = float(np.median(np.diff(days))) if n > 1 else 30.0
    xs = np.concatenate([[-gap], days])
    labels = ["inception", *[_date(d) for d in series.dates]]
    return xs, labels, True


def _x_axis_dated(
    report: FactsheetReport, xscale: LinearScale, y: float, x_origin_date: pd.Timestamp
) -> str:
    dates = report.returns.dates
    assert dates is not None
    parts = []
    for ts, label in _date_ticks(x_origin_date, dates[-1]):
        x = xscale(float((ts - dates[0]).days))
        parts.append(_vline(x, y, y + 4, "axis"))
        parts.append(_text(x, y + 18, label))
    return "".join(parts)


def _period_caption(report: FactsheetReport) -> str:
    s = report.input_summary
    span = f"{s.start} to {s.end}" if s.start else "undated observations"
    return f"{span}; {s.observations} {s.frequency.value} returns"


def _smoothing_note(report: FactsheetReport) -> str:
    if report.diagnostics.smoothing_risk in ("moderate", "high"):
        return (
            f" Returns show {report.diagnostics.smoothing_risk} serial correlation (possible "
            "smoothing): the path may look smoother than the underlying value changes."
        )
    return ""


# --- line chart (wealth, rolling statistics, benchmark comparison) -----------------


@dataclass(frozen=True)
class _Line:
    css: str  # CSS custom property holding the series color
    label: str
    ys: npt.NDArray[np.float64]


def _line_chart(
    *,
    title: str,
    desc: str,
    xs: npt.NDArray[np.float64],
    x_labels: Sequence[str],
    lines: Sequence[_Line],
    y_fmt: str,
    include_zero: bool,
    baseline: float | None,
    baseline_label: str | None,
    report: FactsheetReport,
    dated: bool,
    x_origin: pd.Timestamp | None,
) -> str:
    x0, x1 = MARGIN_LEFT, WIDTH - MARGIN_RIGHT
    y_top, y_bot = MARGIN_TOP, MARGIN_TOP + PLOT_HEIGHT
    all_y = np.concatenate([ln.ys for ln in lines])
    lo, hi = float(np.min(all_y)), float(np.max(all_y))
    if baseline is not None:
        lo, hi = min(lo, baseline), max(hi, baseline)
    if include_zero:
        lo, hi = min(lo, 0.0), max(hi, 0.0)
    lo, hi = _padded(lo, hi)
    if include_zero and float(np.min(all_y)) >= 0 and (baseline is None or baseline >= 0):
        lo = 0.0  # a magnitude axis starts exactly at zero
    ticks = [t for t in nice_ticks(lo, hi) if lo <= t <= hi]
    xscale = LinearScale(float(xs[0]), float(xs[-1]), x0, x1)
    yscale = LinearScale(lo, hi, y_bot, y_top)

    points: list[object] = []
    for i, x in enumerate(xs):
        values = [f"{_fmt(float(ln.ys[i]), y_fmt)}  {ln.label}" for ln in lines]
        points.append([round(xscale(float(x)), 2), [*values, x_labels[i]]])

    parts = [_svg_open(y_bot + MARGIN_BOTTOM, title, desc, points)]
    parts.append(_y_axis(yscale, ticks, y_fmt, x0, x1))
    if baseline is not None:
        parts.append(_hline(yscale(baseline), x0, x1, "baseline"))
        if baseline_label:
            parts.append(_text(x0 + 4, yscale(baseline) - 5, baseline_label, "note", "start"))
    parts.append(_hline(y_bot, x0, x1, "axis"))
    if dated and x_origin is not None:
        parts.append(_x_axis_dated(report, xscale, y_bot, x_origin))
    else:
        for t in nice_ticks(float(xs[0]), float(xs[-1]), 6):
            if xs[0] <= t <= xs[-1]:
                parts.append(_text(xscale(t), y_bot + 18, f"{t:.0f}"))
    for ln in lines:
        path = _path([xscale(float(x)) for x in xs], [yscale(float(y)) for y in ln.ys])
        parts.append(f'<path class="line" style="stroke:var({ln.css})" d="{path}"/>')
    # Direct end labels (the legend is also rendered in HTML for two or more series).
    ends = sorted(((yscale(float(ln.ys[-1])), ln) for ln in lines), key=lambda t: t[0])
    last_y = -1e9
    for y, ln in ends:
        y_label = max(y, last_y + 14)
        last_y = y_label
        value = _fmt(float(ln.ys[-1]), y_fmt)
        parts.append(
            f'<circle class="dot" cx="{x1:.1f}" cy="{y:.1f}" r="4" style="fill:var({ln.css})"/>'
        )
        parts.append(_text(x1 + 8, y_label + 4, value, "endlabel", "start"))
    parts.append(_vline(x0, y_top, y_bot, "xhair"))
    parts.append("</svg>")
    return "".join(parts)


# --- chart builders --------------------------------------------------------------------


def wealth_chart(report: FactsheetReport) -> Chart:
    ctx = _context(report)
    title = "Growth of 1 since inception"
    if ctx.diagnostics.impossible_return_count:
        return Chart(
            "wealth",
            "returns",
            title,
            "",
            unavailable_reason="Returns below -100% make the wealth path meaningless.",
        )
    wealth = ctx.cache.wealth
    xs, labels, dated = _x_positions(report)
    end = float(wealth[-1])
    caption = (
        f"{_period_caption(report)}. Linear scale; the line starts at 1.0 one period before "
        f"the first return and includes every period. Ending value {_num(end)} "
        f"({_pct(end - 1)} cumulative)." + _smoothing_note(report)
    )
    origin = None
    if dated and report.returns.dates is not None:
        origin = report.returns.dates[0] + pd.Timedelta(days=float(xs[0]))
    svg = _line_chart(
        title=title, desc=caption, xs=xs, x_labels=labels,
        lines=[_Line("--series-1", "growth of 1", wealth)], y_fmt="num",
        include_zero=False, baseline=1.0, baseline_label=None,
        report=report, dated=dated, x_origin=origin,
    )  # fmt: skip
    rows = tuple((labels[i], _num(float(w), 4)) for i, w in enumerate(wealth))
    return Chart("wealth", "returns", title, caption, svg, ("Date", "Growth of 1"), rows)


def underwater_chart(report: FactsheetReport) -> Chart:
    ctx = _context(report)
    title = "Drawdown from previous peak (underwater chart)"
    if ctx.diagnostics.impossible_return_count:
        return Chart(
            "underwater",
            "drawdown",
            title,
            "",
            unavailable_reason="Returns below -100% make the drawdown path meaningless.",
        )
    dd = ctx.cache.drawdown_full
    xs, labels, dated = _x_positions(report)
    x0, x1 = MARGIN_LEFT, WIDTH - MARGIN_RIGHT
    y_top, y_bot = MARGIN_TOP, MARGIN_TOP + PLOT_HEIGHT
    low = float(np.min(dd))
    lo = low * 1.08 if low < 0 else -0.01
    ticks = [t for t in nice_ticks(lo, 0.0) if lo <= t <= 0.0]
    xscale = LinearScale(float(xs[0]), float(xs[-1]), x0, x1)
    yscale = LinearScale(lo, 0.0, y_bot, y_top)
    px = [xscale(float(x)) for x in xs]
    py = [yscale(float(d)) for d in dd]
    points: list[object] = [
        [round(px[i], 2), [f"{_pct(float(dd[i]))}  drawdown", labels[i]]] for i in range(len(xs))
    ]
    worst = int(np.argmin(dd))
    episodes = ctx.cache.episodes
    open_note = ""
    if episodes and not min(episodes, key=lambda e: e.depth).recovered:
        open_note = " The deepest drawdown had not recovered by the end of the data."
    caption = (
        f"{_period_caption(report)}. Decline of compounded wealth below its running peak "
        f"(0% = at a new high). Maximum drawdown {_pct(low)}"
        + (f" on {labels[worst]}" if worst else "")
        + f"; time under water {_pct(float(np.mean(dd[1:] < 0)), 0, signed=False)} of periods."
        + open_note
    )
    parts = [_svg_open(y_bot + MARGIN_BOTTOM, title, caption, points)]
    parts.append(_y_axis(yscale, ticks, "pct", x0, x1))
    area = _path(px, py) + f" L{px[-1]:.2f},{yscale(0.0):.2f} L{px[0]:.2f},{yscale(0.0):.2f} Z"
    parts.append(f'<path class="area" style="fill:var(--loss)" d="{area}"/>')
    parts.append(f'<path class="line" style="stroke:var(--loss)" d="{_path(px, py)}"/>')
    parts.append(_hline(yscale(0.0), x0, x1, "baseline"))
    if dated and report.returns.dates is not None:
        origin = report.returns.dates[0] + pd.Timedelta(days=float(xs[0]))
        parts.append(_x_axis_dated(report, xscale, y_bot, origin))
    parts.append(_hline(y_bot, x0, x1, "axis"))
    if low < 0:
        parts.append(
            f'<circle class="dot" cx="{px[worst]:.1f}" cy="{py[worst]:.1f}" r="4" '
            'style="fill:var(--loss)"/>'
        )
        anchor = "start" if px[worst] < (x0 + x1) / 2 else "end"
        dx = 8 if anchor == "start" else -8
        parts.append(_text(px[worst] + dx, py[worst] + 4, f"max {_pct(low)}", "endlabel", anchor))
    parts.append(_vline(x0, y_top, y_bot, "xhair"))
    parts.append("</svg>")
    rows = tuple((labels[i], _pct(float(d), 2)) for i, d in enumerate(dd))
    return Chart(
        "underwater", "drawdown", title, caption, "".join(parts), ("Date", "Drawdown"), rows
    )


def calendar_year_chart(report: FactsheetReport) -> Chart:
    ctx = _context(report)
    title = "Calendar-year returns"
    try:
        cy = ctx.calendar_years
    except UndefinedMetric as exc:
        return Chart("calendar_years", "returns", title, "", unavailable_reason=exc.reason)
    dates = report.returns.dates
    assert dates is not None
    years_all = sorted({*cy.complete, *cy.partial})
    # Complete years come straight from the calendar-year engine; partial years are
    # compounded the same way over the months observed.
    values: dict[int, float] = dict(cy.complete)
    for y in cy.partial:
        mask = np.asarray(dates.year) == y
        values[y] = float(np.prod(1.0 + report.returns.values[mask]) - 1.0)
    x0, x1 = MARGIN_LEFT, WIDTH - 24.0
    y_top, y_bot = MARGIN_TOP + 10, MARGIN_TOP + PLOT_HEIGHT
    vs = list(values.values())
    lo, hi = _padded(min(0.0, *vs), max(0.0, *vs), 0.12)
    lo, hi = min(lo, 0.0), max(hi, 0.0)
    ticks = [t for t in nice_ticks(lo, hi) if lo <= t <= hi]
    yscale = LinearScale(lo, hi, y_bot, y_top)
    band = (x1 - x0) / len(years_all)
    w = min(BAR_MAX_WIDTH, band * 0.6)
    y0 = yscale(0.0)
    parts = [_svg_open(y_bot + MARGIN_BOTTOM + 14, title, "")]
    parts.append(_y_axis(yscale, ticks, "pct", x0, x1))
    for i, y in enumerate(years_all):
        v = values[y]
        partial = y in cy.partial
        cx = x0 + band * (i + 0.5)
        ye = yscale(v)
        css = "--gain" if v >= 0 else "--loss"
        cls = "bar partial" if partial else "bar"
        label = f"{y}{' (partial: ' + cy.partial[y] + ')' if partial else ''}"
        tip = f"{_pct(v)}\n{label}"
        parts.append(
            f'<path class="{cls}" style="--c:var({css})" d="{_bar_path(cx - w / 2, w, y0, ye)}" '
            f'tabindex="0" data-tip="{escape(tip, quote=True)}"/>'
        )
        ty = ye - 6 if v >= 0 else ye + 14
        parts.append(_text(cx, ty, _pct(v), "value"))
        parts.append(_text(cx, y_bot + 18, f"{y}*" if partial else str(y)))
    parts.append(_hline(y0, x0, x1, "baseline"))
    parts.append("</svg>")
    partial_note = ""
    if cy.partial:
        listed = "; ".join(f"{y}: {why}" for y, why in cy.partial.items())
        partial_note = (
            " * Partial years are outlined and are not used in calendar-year statistics "
            f"({listed})."
        )
    caption = (
        f"{_period_caption(report)}. Compounded return of each calendar year; bars start at "
        "0%." + partial_note
    )
    svg = _svg_set_desc("".join(parts), caption)
    rows = tuple(
        (f"{y}{' (partial)' if y in cy.partial else ''}", _pct(values[y], 2)) for y in years_all
    )
    return Chart("calendar_years", "returns", title, caption, svg, ("Year", "Return"), rows)


def _svg_set_desc(svg: str, desc: str) -> str:
    start = svg.index("<desc")
    open_end = svg.index(">", start) + 1
    close = svg.index("</desc>", open_end)
    return svg[:open_end] + escape(desc) + svg[close:]


def monthly_heatmap(report: FactsheetReport) -> Chart:
    title = "Monthly returns (%)"
    series = report.returns
    if series.dates is None or series.frequency is not ObservationFrequency.MONTHLY:
        return Chart(
            "monthly_heatmap", "returns", title, "",
            unavailable_reason="The monthly table is drawn for dated monthly returns only.",
        )  # fmt: skip
    ctx = _context(report)
    cy = ctx.calendar_years
    dates = series.dates
    table: dict[tuple[int, int], float] = {
        (d.year, d.month): float(v) for d, v in zip(dates, series.values, strict=True)
    }
    years = list(range(dates[0].year, dates[-1].year + 1))
    bound = float(np.max(np.abs(series.values))) or 1.0
    x0 = MARGIN_LEFT
    cell_w = (WIDTH - x0 - 12.0) / 13.0
    cell_h = 22.0
    top = 30.0
    height = top + cell_h * len(years) + 58.0
    parts = [_svg_open(height, title, "")]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for j, m in enumerate([*months, "Year"]):
        parts.append(_text(x0 + cell_w * (j + 0.5), top - 10, m, "tick"))
    for i, year in enumerate(years):
        y = top + cell_h * i
        parts.append(_text(x0 - 8, y + cell_h / 2 + 4, str(year), "tick", "end"))
        for j in range(12):
            x = x0 + cell_w * j
            v = table.get((year, j + 1))
            if v is None:
                parts.append(
                    f'<rect class="cell missing" x="{x + 1:.1f}" y="{y + 1:.1f}" '
                    f'width="{cell_w - 2:.1f}" height="{cell_h - 2:.1f}" rx="2"/>'
                )
                continue
            parts.append(
                _heat_cell(x, y, cell_w, cell_h, v, bound, f"{_pct(v, 2)}\n{months[j]} {year}")
            )
        # Year column: compounded; partial years flagged.
        mask = np.asarray(dates.year) == year
        yv = float(np.prod(1.0 + series.values[mask]) - 1.0)
        partial = year in cy.partial
        x = x0 + cell_w * 12
        label = f"{_pct(yv, 1)}{'*' if partial else ''}"
        tip = f"{_pct(yv, 2)}\n{year}{' (partial year)' if partial else ''}"
        parts.append(
            f'<rect class="cell yearcell{" partial" if partial else ""}" x="{x + 3:.1f}" '
            f'y="{y + 1:.1f}" width="{cell_w - 4:.1f}" height="{cell_h - 2:.1f}" rx="2" '
            f'tabindex="0" data-tip="{escape(tip, quote=True)}"/>'
        )
        parts.append(_text(x + cell_w / 2, y + cell_h / 2 + 4, label, "celltext"))
    # Symmetric diverging legend.
    ly = top + cell_h * len(years) + 20
    lx0, lx1 = x0, x0 + 260.0
    stops = "".join(
        f'<stop offset="{o}" stop-color="var({c})"/>'
        for o, c in (("0", "--loss"), ("0.5", "--neutral"), ("1", "--gain"))
    )
    parts.append(f'<defs><linearGradient id="ofs-div">{stops}</linearGradient></defs>')
    parts.append(
        f'<rect x="{lx0:.1f}" y="{ly:.1f}" width="{lx1 - lx0:.1f}" height="8" rx="2" '
        'fill="url(#ofs-div)"/>'
    )
    parts.append(_text(lx0, ly + 22, _pct(-bound), "tick", "start"))
    parts.append(_text((lx0 + lx1) / 2, ly + 22, "0%", "tick"))
    parts.append(_text(lx1, ly + 22, _pct(bound), "tick", "end"))
    parts.append("</svg>")
    caption = (
        f"{_period_caption(report)}. Every month is shown; empty cells are periods without a "
        f"return. The color scale is symmetric (±{_pct(bound, 1, signed=False)}, the largest "
        "absolute month), so equal gains and losses are equally saturated. The Year column "
        "compounds the months; * marks a partial year."
    )
    rows = tuple(
        (str(y), *[_pct(table[(y, m)], 2) if (y, m) in table else "" for m in range(1, 13)])
        for y in years
    )
    svg = _svg_set_desc("".join(parts), caption)
    return Chart("monthly_heatmap", "returns", title, caption, svg, ("Year", *months), rows)


def _heat_cell(x: float, y: float, w: float, h: float, v: float, bound: float, tip: str) -> str:
    share = min(1.0, abs(v) / bound)
    pole = "--gain" if v >= 0 else "--loss"
    pct = round(share * 100)
    text_cls = "celltext strong" if share >= 0.55 else "celltext"
    return (
        f'<rect class="cell" x="{x + 1:.1f}" y="{y + 1:.1f}" width="{w - 2:.1f}" '
        f'height="{h - 2:.1f}" rx="2" style="fill:color-mix(in oklab, var({pole}) {pct}%, '
        f'var(--neutral))" tabindex="0" data-tip="{escape(tip, quote=True)}"/>'
        + _text(x + w / 2, y + h / 2 + 4, _num(v * 100, 1), text_cls)
    )


def histogram_chart(report: FactsheetReport) -> Chart:
    title = "Distribution of returns"
    r = report.returns.values
    n = r.shape[0]
    if n < 5 or float(np.ptp(r)) == 0.0:
        return Chart(
            "histogram",
            "distribution",
            title,
            "",
            unavailable_reason="At least 5 non-identical returns are needed.",
        )
    conv = report.assumptions.get("charts")
    q75, q25 = np.quantile(r, [0.75, 0.25])
    iqr = float(q75 - q25)
    span = float(np.ptp(r))
    width = 2 * iqr / n ** (1 / 3) if iqr > 0 else span / int(conv["histogram_min_bins"])
    bins = int(
        np.clip(math.ceil(span / width), conv["histogram_min_bins"], conv["histogram_max_bins"])
    )
    width = span / bins
    # Align bin edges at zero so gains and losses never share a bin.
    # Integer multiples of the width, so the zero edge is exactly 0.0 and a zero
    # return always falls in the first non-negative bin.
    k0 = math.floor(float(r.min()) / width)
    k1 = max(math.floor(float(r.max()) / width) + 1, k0 + 1)
    if k0 * width > float(r.min()):  # guard floating-point rounding: every return counted
        k0 -= 1
    if k1 * width <= float(r.max()):
        k1 += 1
    edges = np.arange(k0, k1 + 1, dtype=np.float64) * width
    counts, edges = np.histogram(r, bins=edges)
    x0, x1 = MARGIN_LEFT, WIDTH - 24.0
    y_top, y_bot = MARGIN_TOP + 10, MARGIN_TOP + PLOT_HEIGHT
    mean, sd = float(np.mean(r)), float(np.std(r, ddof=1))
    grid = np.linspace(edges[0], edges[-1], 200)
    normal = n * width * np.exp(-0.5 * ((grid - mean) / sd) ** 2) / (sd * math.sqrt(2 * math.pi))
    top_count = max(float(counts.max()), float(normal.max()))
    xscale = LinearScale(float(edges[0]), float(edges[-1]), x0, x1)
    yscale = LinearScale(0.0, top_count * 1.12, y_bot, y_top)
    ticks = [t for t in nice_ticks(0.0, top_count * 1.12) if t <= top_count * 1.12]
    parts = [_svg_open(y_bot + MARGIN_BOTTOM, title, "")]
    for t in ticks:
        parts.append(_hline(yscale(t), x0, x1, "grid"))
        parts.append(_text(x0 - 8, yscale(t) + 4, f"{t:.0f}", "tick", "end"))
    gap = 1.0
    for c, a, b in zip(counts, edges[:-1], edges[1:], strict=True):
        if c == 0:
            continue
        xa, xb = xscale(float(a)) + gap, xscale(float(b)) - gap
        css = "--gain" if a >= -1e-15 else "--loss"
        tip = f"{c} return(s)\n{_pct(float(a), 2)} to {_pct(float(b), 2)}"
        parts.append(
            f'<path class="bar" style="--c:var({css})" '
            f'd="{_bar_path(xa, max(xb - xa, 1.0), yscale(0.0), yscale(float(c)))}" '
            f'tabindex="0" data-tip="{escape(tip, quote=True)}"/>'
        )
    npath = _path([xscale(float(g)) for g in grid], [yscale(float(v)) for v in normal])
    parts.append(f'<path class="line thin" style="stroke:var(--ink-2)" d="{npath}"/>')
    # Zero line (the x axis carries the 0% tick) and the historical VaR marker, whose
    # label sits on the loss side of its line so it never collides with the zero line.
    if edges[0] <= 0.0 <= edges[-1]:
        parts.append(_vline(xscale(0.0), y_top, y_bot, "baseline"))
    var95 = report.metrics.get("var_historical_95")
    if var95 is not None and var95.value is not None and edges[0] <= var95.value <= edges[-1]:
        xv = xscale(float(var95.value))
        parts.append(_vline(xv, y_top, y_bot, "marker"))
        parts.append(
            _text(xv - 4, y_top + 10, f"VaR 95% {_pct(float(var95.value))}", "note", "end")
        )
    parts.append(_hline(y_bot, x0, x1, "axis"))
    x_ticks = [
        t for t in nice_ticks(float(edges[0]), float(edges[-1]), 7) if edges[0] <= t <= edges[-1]
    ]
    decimals = 0 if all(abs(t * 100 - round(t * 100)) < 1e-9 for t in x_ticks) else 1
    for t in x_ticks:
        parts.append(_text(xscale(t), y_bot + 18, _pct(t, decimals, signed=False)))
    parts.append("</svg>")
    caption = (
        f"{_period_caption(report)}. All {n} returns are counted "
        f"(sum of bars = {int(counts.sum())}); "
        f"no outliers are removed. {len(counts)} bins of {_pct(width, 2, signed=False)}, edges "
        "aligned at "
        "0%. The thin curve is a normal distribution with the same mean and volatility; bars "
        "beyond it reveal fat tails."
    )
    rows = tuple(
        (f"{_pct(float(a), 2)} to {_pct(float(b), 2)}", str(int(c)))
        for c, a, b in zip(counts, edges[:-1], edges[1:], strict=True)
    )
    return Chart(
        "histogram",
        "distribution",
        title,
        caption,
        _svg_set_desc("".join(parts), caption),
        ("Return range", "Count"),
        rows,
    )


def _rolling_chart(report: FactsheetReport, kind: str) -> Chart:
    ctx = _context(report)
    is_vol = kind == "volatility"
    cid = "rolling_volatility" if is_vol else "rolling_return"
    section = "volatility" if is_vol else "consistency"
    title = (
        "Rolling one-year volatility (annualized)"
        if is_vol
        else "Rolling one-year return (every start date)"
    )
    if report.returns.periods_per_year is None:
        return Chart(
            cid,
            section,
            title,
            "",
            unavailable_reason=("Rolling one-year windows need a regular observation frequency."),
        )
    # The same one-year window as the rolling-year metrics (decision 0024).
    window = round(ctx.ppy * float(report.assumptions.get("rolling.window_years")))
    r = report.returns.values
    if r.shape[0] < max(window, 2) + 1 or (is_vol and window < 2):
        return Chart(
            cid,
            section,
            title,
            "",
            unavailable_reason=(
                f"At least {max(window, 2) + 1} observations are needed for two or more one-year "
                "windows."
            ),
        )
    if ctx.diagnostics.impossible_return_count and not is_vol:
        return Chart(
            cid,
            section,
            title,
            "",
            unavailable_reason=("Returns below -100% make compounded windows meaningless."),
        )
    if is_vol:
        windows = np.lib.stride_tricks.sliding_window_view(r, window)
        ddof = int(report.assumptions.get("dispersion.ddof"))
        ys = np.std(windows, axis=1, ddof=ddof) * math.sqrt(ctx.ppy)
    else:
        ys, _ = ctx.rolling_year_returns  # identical to the rolling-year metrics
    xs_all, labels_all, dated = _x_positions(report)
    xs = xs_all[window:]
    labels = labels_all[window:]
    origin = None
    if dated and report.returns.dates is not None:
        origin = report.returns.dates[window - 1]
    caption = (
        f"{_period_caption(report)}. Each point is the "
        + ("annualized volatility" if is_vol else "compounded return")
        + f" of the {window} observations ending on that date; all {len(ys)} windows are "
        "shown. Windows overlap, so neighbouring points share most of their data."
        + (_smoothing_note(report) if is_vol else "")
    )
    svg = _line_chart(
        title=title, desc=caption, xs=xs, x_labels=labels,
        lines=[_Line("--series-1", "volatility" if is_vol else "one-year return", ys)],
        y_fmt="pct_level" if is_vol else "pct", include_zero=True, baseline=0.0,
        baseline_label=None,
        report=report, dated=dated, x_origin=origin,
    )  # fmt: skip
    rows = tuple((labels[i], _pct(float(v), 2, signed=not is_vol)) for i, v in enumerate(ys))
    return Chart(cid, section, title, caption, svg, ("Window end", title.split(" (")[0]), rows)


def benchmark_chart(report: FactsheetReport) -> Chart:
    title = "Growth of 1 over the benchmark overlap"
    if report.benchmark_returns is None:
        return Chart(
            "benchmark_growth",
            "benchmark",
            title,
            "",
            unavailable_reason="No benchmark was supplied.",
        )
    from openfactsheet.compare.alignment import align_benchmark

    aligned = align_benchmark(report.returns, report.benchmark_returns)
    if aligned.n < 2:
        return Chart(
            "benchmark_growth",
            "benchmark",
            title,
            "",
            unavailable_reason="Fewer than 2 aligned periods.",
        )
    if np.any(aligned.fund < -1.0) or np.any(aligned.bench < -1.0):
        return Chart(
            "benchmark_growth",
            "benchmark",
            title,
            "",
            unavailable_reason="Returns below -100% make the wealth paths meaningless.",
        )
    wf = np.concatenate([[1.0], np.cumprod(1.0 + aligned.fund)])
    wb = np.concatenate([[1.0], np.cumprod(1.0 + aligned.bench)])
    dates = aligned.dates
    if dates is not None:
        days = (dates - dates[0]).days.to_numpy().astype(np.float64)
        gap = float(np.median(np.diff(days))) if len(days) > 1 else 30.0
        xs = np.concatenate([[-gap], days])
        labels = ["overlap start", *[_date(d) for d in dates]]
    else:
        xs = np.arange(aligned.n + 1, dtype=np.float64)
        labels = ["start", *[f"period {i}" for i in range(1, aligned.n + 1)]]
    b = aligned.diagnostics
    caption = (
        f"Aligned periods only: {b.overlap_start or 'undated'} to {b.overlap_end or 'undated'}, "
        f"{b.aligned_observations} periods ({_pct(b.fund_coverage, 0, signed=False)} of the fund "
        "history). Both lines start at 1.0 immediately before the first common period, on one "
        "linear scale. The full fund history is in the Growth of 1 chart."
    )
    fund_name = report.name
    bench_name = b.name
    origin = None
    if dates is not None:
        origin = dates[0] + pd.Timedelta(days=float(xs[0]))
    # _x_axis_dated reads the fund dates; draw with a temporary view of the aligned dates.
    svg = _line_chart(
        title=title, desc=caption, xs=xs, x_labels=labels,
        lines=[_Line("--series-1", fund_name, wf), _Line("--series-2", bench_name, wb)],
        y_fmt="num", include_zero=False, baseline=1.0, baseline_label=None,
        report=_with_dates(report, dates), dated=dates is not None, x_origin=origin,
    )  # fmt: skip
    rows = tuple((labels[i], _num(float(wf[i]), 4), _num(float(wb[i]), 4)) for i in range(len(xs)))
    return Chart(
        "benchmark_growth", "benchmark", title, caption, svg, ("Date", fund_name, bench_name),
        rows, legend=(("--series-1", fund_name), ("--series-2", bench_name)),
    )  # fmt: skip


def _with_dates(report: FactsheetReport, dates: pd.DatetimeIndex | None) -> FactsheetReport:
    """A shallow stand-in exposing aligned dates to the shared x-axis helper."""
    from dataclasses import replace

    if dates is None:
        return report
    returns = replace(report.returns, values=np.zeros(len(dates)), dates=dates)
    return replace(report, returns=returns)


def build_charts(report: FactsheetReport) -> list[Chart]:
    """All canonical charts, in report order. Unavailable charts carry their reason."""
    return [
        wealth_chart(report),
        calendar_year_chart(report),
        monthly_heatmap(report),
        _rolling_chart(report, "volatility"),
        underwater_chart(report),
        histogram_chart(report),
        _rolling_chart(report, "return"),
        benchmark_chart(report),
    ]
