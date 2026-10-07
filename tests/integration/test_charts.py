"""Canonical charts (decision 0026): availability, honesty rules and determinism."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

import openfactsheet as ofs
from openfactsheet.metrics.context import MetricContext
from openfactsheet.report.charts import (
    Chart,
    LinearScale,
    build_charts,
    nice_ticks,
)
from openfactsheet.report.tables import drawdown_episode_table
from tests.conftest import fixture_series, monthly

CHART_IDS = (
    "wealth",
    "calendar_years",
    "monthly_heatmap",
    "rolling_volatility",
    "underwater",
    "histogram",
    "rolling_return",
    "benchmark_growth",
)


@pytest.fixture(scope="module")
def bench_report() -> ofs.FactsheetReport:
    fund, bench = fixture_series("benchmark_case_fund"), fixture_series("benchmark_case_benchmark")
    return ofs.analyze(fund, benchmark=bench, name="Fund")


@pytest.fixture(scope="module")
def fund_report() -> ofs.FactsheetReport:
    return ofs.analyze(fixture_series("monthly_fund_10y"))


def _by_id(report: ofs.FactsheetReport) -> dict[str, Chart]:
    return {c.id: c for c in build_charts(report)}


def _has_non_finite(svg: str) -> bool:
    return re.search(r"(?<![a-z])(nan|inf)(?![a-z])", svg.lower()) is not None


def test_every_chart_is_drawn_or_explained(bench_report: ofs.FactsheetReport) -> None:
    charts = build_charts(bench_report)
    assert tuple(c.id for c in charts) == CHART_IDS
    for c in charts:
        assert c.svg, c.id  # this fixture supports every canonical chart
        assert c.caption, c.id
        assert c.table_rows, c.id  # a data table accompanies every drawn chart
        assert not _has_non_finite(c.svg), c.id


def test_no_benchmark_chart_without_benchmark(fund_report: ofs.FactsheetReport) -> None:
    chart = _by_id(fund_report)["benchmark_growth"]
    assert chart.svg == ""
    assert chart.unavailable_reason == "No benchmark was supplied."
    assert "benchmark_growth" not in fund_report.charts()
    # The benchmark section itself explains why it is not applicable.
    assert "id='chart-benchmark_growth'" not in fund_report.to_html()


def test_wealth_chart_spans_full_history(fund_report: ofs.FactsheetReport) -> None:
    chart = _by_id(fund_report)["wealth"]
    n = fund_report.returns.n
    assert len(chart.table_rows) == n + 1  # inception plus every period
    assert chart.table_rows[0] == ("inception", "1.0000")
    ctx = MetricContext(
        returns=fund_report.returns,
        diagnostics=fund_report.diagnostics,
        methodology=fund_report.assumptions,
    )
    assert chart.table_rows[-1][1] == f"{ctx.cache.wealth[-1]:.4f}"


def test_underwater_chart_matches_max_drawdown(fund_report: ofs.FactsheetReport) -> None:
    chart = _by_id(fund_report)["underwater"]
    mdd = fund_report.metrics["max_drawdown"].value
    assert mdd is not None
    assert f"max {'−' if mdd < 0 else ''}{abs(mdd) * 100:.1f}%" in chart.svg


def test_histogram_counts_every_return(bench_report: ofs.FactsheetReport) -> None:
    chart = _by_id(bench_report)["histogram"]
    assert sum(int(row[1]) for row in chart.table_rows) == bench_report.returns.n
    conv = bench_report.assumptions.get("charts")
    assert conv["histogram_min_bins"] <= len(chart.table_rows) <= conv["histogram_max_bins"] + 1
    # Bin edges are aligned at zero: no bin straddles 0%.
    edges = [row[0] for row in chart.table_rows]
    assert any(e.endswith(" to 0.00%") for e in edges)


def test_heatmap_scale_is_symmetric(bench_report: ofs.FactsheetReport) -> None:
    chart = _by_id(bench_report)["monthly_heatmap"]
    bound = float(np.max(np.abs(bench_report.returns.values)))
    assert f"±{bound * 100:.1f}%" in chart.caption
    # Every observed month is in the data table.
    cells = sum(1 for row in chart.table_rows for c in row[1:] if c)
    assert cells == bench_report.returns.n


def test_partial_years_are_flagged(bench_report: ofs.FactsheetReport) -> None:
    chart = _by_id(bench_report)["calendar_years"]
    assert "2016*" in chart.svg  # the fixture starts in July 2016
    assert "bar partial" in chart.svg
    assert ("2016 (partial)", "+2.52%") in chart.table_rows or any(
        row[0] == "2016 (partial)" for row in chart.table_rows
    )


def test_rolling_return_chart_equals_rolling_metrics(bench_report: ofs.FactsheetReport) -> None:
    chart = _by_id(bench_report)["rolling_return"]
    assert len(chart.table_rows) == bench_report.returns.n - 12 + 1
    best = bench_report.metrics["best_rolling_year"].value
    worst = bench_report.metrics["worst_rolling_year"].value
    assert best is not None
    assert worst is not None
    values = [float(v.replace("−", "-").rstrip("%")) / 100 for _, v in chart.table_rows]
    assert max(values) == pytest.approx(best, abs=5e-5)
    assert min(values) == pytest.approx(worst, abs=5e-5)


def test_rolling_volatility_is_unsigned(bench_report: ofs.FactsheetReport) -> None:
    chart = _by_id(bench_report)["rolling_volatility"]
    assert all(not v.startswith(("+", "−")) for _, v in chart.table_rows)


def test_benchmark_chart_uses_aligned_overlap_only(bench_report: ofs.FactsheetReport) -> None:
    chart = _by_id(bench_report)["benchmark_growth"]
    b = bench_report.benchmark_summary
    assert b is not None
    assert len(chart.table_rows) == b.aligned_observations + 1
    assert chart.table_rows[0][1:] == ("1.0000", "1.0000")
    assert len(chart.legend) == 2


def test_html_is_self_contained_and_deterministic(bench_report: ofs.FactsheetReport) -> None:
    html = bench_report.to_html()
    assert html == bench_report.to_html()
    assert "<script src" not in html
    assert "<link" not in html
    # Nothing is fetched when the page is opened: no external subresource, no CDN.
    assert not re.search(r"src=['\"]https?://", html)
    assert "@import" not in html
    assert "url(http" not in html
    for cid in CHART_IDS:
        assert f"id='chart-{cid}'" in html


def test_html_links_out_only_to_the_documentation(bench_report: ofs.FactsheetReport) -> None:
    """The only external addresses are documentation links the reader may follow (0035)."""
    html = bench_report.to_html()
    external = re.findall(r"href='(https?://[^']+)'", html)
    assert external
    assert all(u.startswith("https://github.com/bagnascotrader/openfactsheet/") for u in external)
    # Every one of them is an anchor the reader clicks, never a loaded resource.
    assert len(re.findall(r"<a [^>]*href='https", html)) == len(external)


def test_charts_method_returns_svg(bench_report: ofs.FactsheetReport) -> None:
    svgs = bench_report.charts()
    assert set(svgs) == set(CHART_IDS)
    assert all(s.startswith("<svg") and s.endswith("</svg>") for s in svgs.values())


@pytest.mark.parametrize(
    "series",
    [
        pytest.param(monthly([0.01, -0.02, 0.015, 0.005, -0.01, 0.03], "2025-01-31"), id="six"),
        pytest.param(pd.Series([0.01, -0.02, 0.015, 0.005, -0.01, 0.03]), id="undated"),
        pytest.param(monthly([0.0] * 30), id="all_zero"),
        pytest.param(monthly([0.01] * 30), id="constant"),
        pytest.param(monthly([0.02]), id="single"),
        pytest.param(
            pd.Series(
                np.random.default_rng(3).normal(0.001, 0.01, 300),
                index=pd.bdate_range("2023-01-02", periods=300),
            ),
            id="daily",
        ),
        pytest.param(
            pd.Series(
                np.random.default_rng(4).normal(0.002, 0.02, 120),
                index=pd.date_range("2022-01-07", periods=120, freq="W-FRI"),
            ),
            id="weekly",
        ),
        pytest.param(
            pd.Series(
                [0.08, -0.12, 0.2, 0.05, 0.11],
                index=pd.date_range("2019-12-31", periods=5, freq="YE"),
            ),
            id="yearly",
        ),
    ],
)
def test_charts_never_crash(series: pd.Series) -> None:
    report = ofs.analyze(series)
    charts = build_charts(report)
    for c in charts:
        assert c.svg or c.unavailable_reason, c.id
        assert not _has_non_finite(c.svg), c.id
    html = report.to_html()
    assert "Growth of 1 since inception" in html


def test_heatmap_only_for_monthly() -> None:
    weekly = pd.Series(
        np.random.default_rng(5).normal(0.002, 0.02, 120),
        index=pd.date_range("2022-01-07", periods=120, freq="W-FRI"),
    )
    chart = _by_id(ofs.analyze(weekly))["monthly_heatmap"]
    assert chart.svg == ""
    assert chart.unavailable_reason is not None


def test_episode_table_is_deepest_first(fund_report: ofs.FactsheetReport) -> None:
    table = drawdown_episode_table(fund_report)
    assert table is not None
    assert table.total == len(fund_report.drawdown_episodes)
    limit = fund_report.assumptions.get("charts.episode_table_rows")
    assert len(table.rows) == min(limit, table.total)
    depths = [float(row[4].rstrip("%")) for row in table.rows]
    assert depths == sorted(depths)
    mdd = fund_report.metrics["max_drawdown"].value
    assert mdd is not None
    assert table.rows[0][4] == f"{mdd:.2%}"
    for text in (fund_report.summary(), fund_report.to_markdown(), fund_report.to_html()):
        assert "Drawdown episodes" in text


def test_episode_table_without_drawdowns() -> None:
    table = drawdown_episode_table(ofs.analyze(monthly([0.01] * 12)))
    assert table is not None
    assert table.rows == ()
    assert "No drawdown episodes" in table.note


def test_nice_ticks_and_scale() -> None:
    assert nice_ticks(0.0, 1.0) == [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    assert 0.0 in nice_ticks(-0.12, 0.0)
    assert 0.0 in nice_ticks(-0.3, 0.3)
    s = LinearScale(0.0, 10.0, 100.0, 0.0)
    assert s(0.0) == 100.0
    assert s(10.0) == 0.0
    assert LinearScale(1.0, 1.0, 0.0, 10.0)(1.0) == 5.0
