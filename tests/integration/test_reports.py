from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import openfactsheet as ofs
from openfactsheet.exceptions import BenchmarkAlignmentError, InputError
from tests.conftest import FIXTURES, fixture_series, monthly


@pytest.fixture(scope="module")
def report() -> ofs.FactsheetReport:
    fund, bench = fixture_series("benchmark_case_fund"), fixture_series("benchmark_case_benchmark")
    return ofs.analyze(fund, benchmark=bench, name="Fund")


def test_json_is_deterministic_and_nan_free(report: ofs.FactsheetReport) -> None:
    text = report.to_json()
    assert "NaN" not in text
    assert "Infinity" not in text
    data = json.loads(text)
    assert data["canonical"] is True
    assert data["provenance"]["methodology_version"] == ofs.METHODOLOGY_VERSION
    assert len(data["provenance"]["input_sha256"]) == 64
    assert data["benchmark"]["alignment"]["aligned_observations"] == 96
    assert len(data["metrics"]) == len(report.metrics)
    assert data["returns"][0]["date"] == "2016-07-31"


def test_json_written_to_file(report: ofs.FactsheetReport, tmp_path: Path) -> None:
    path = tmp_path / "factsheet.json"
    report.to_json(path)
    assert json.loads(path.read_text(encoding="utf-8"))["name"] == "Fund"


def test_all_renderers_include_canonical_sections(report: ofs.FactsheetReport) -> None:
    for text in (report.summary(), report.to_markdown(), report.to_html()):
        for section in (
            "Input",
            "Data-quality",
            "Drawdowns",
            "Tail behavior",
            "Benchmark",
            "Factor analysis",
            "Assumptions",
        ):
            assert section.lower() in text.lower(), section
        assert "Maximum drawdown" in text


def test_canonical_report_has_fourteen_sections(report: ofs.FactsheetReport) -> None:
    text = report.summary()
    assert "\n14. ASSUMPTIONS & CAVEATS" in text
    assert "\n15. " not in text
    md = report.to_markdown()
    assert "## 14. Assumptions & caveats" in md
    assert "Serial dependence & smoothing" in md
    # Statistical-confidence metrics are rendered in section 12.
    section12 = md.split("## 12. Statistical confidence")[1].split("## 13.")[0]
    assert "| Probabilistic Sharpe Ratio (vs 0) |" in section12
    assert "| Minimum track record length |" in section12


def test_html_escapes_names(tmp_path: Path) -> None:
    rep = ofs.analyze(monthly([0.01, 0.02, -0.01]), name="<script>x</script>")
    html = rep.to_html(tmp_path / "f.html")
    assert "<script>x" not in html
    assert (tmp_path / "f.html").exists()


def test_markdown_table_rows(report: ofs.FactsheetReport) -> None:
    md = report.to_markdown()
    assert "| Sharpe ratio |" in md
    assert "## Notes" in md


def test_metrics_frame(report: ofs.FactsheetReport) -> None:
    frame = report.metrics.to_frame()
    assert frame.loc["beta", "status"] == "applicable"


def test_returns_are_inspectable(report: ofs.FactsheetReport) -> None:
    s = report.returns_frame()
    assert isinstance(s, pd.Series)
    assert len(s) == 102


def test_frequency_mismatch_is_an_error() -> None:
    fund = monthly([0.01, 0.02, -0.01, 0.0])
    bench = pd.Series([0.01] * 4, index=pd.date_range("2020-03-31", periods=4, freq="QE"))
    with pytest.raises(BenchmarkAlignmentError):
        ofs.analyze(fund, benchmark=bench)


def test_undated_pair_aligned_by_position_with_warning() -> None:
    rep = ofs.analyze([0.01, 0.02, -0.01, 0.0], benchmark=[0.01, 0.01, -0.02, 0.01])
    assert rep.benchmark_summary is not None
    assert "position" in rep.benchmark_summary.alignment_method
    with pytest.raises(BenchmarkAlignmentError):
        ofs.analyze([0.01, 0.02, -0.01], benchmark=[0.01, 0.01])


def test_compare_is_not_a_ranking_and_uses_identical_methodology() -> None:
    cmp = ofs.compare(
        {
            "Hedge fund": FIXTURES / "smoothed_hedge_fund.csv",
            "Fund": FIXTURES / "monthly_fund_10y.csv",
        }
    )
    table = cmp.table()
    assert list(table.columns) == ["name", "Hedge fund", "Fund"]
    assert {r.methodology_version for r in cmp.reports.values()} == {ofs.METHODOLOGY_VERSION}
    assert cmp.common_period == ("2017-01-31", "2024-12-31")
    assert cmp.common_period_reports is not None
    assert cmp.common_period_reports["Fund"].returns.n == 96
    assert "Not a ranking" in cmp.summary()
    assert cmp.track_records().loc["Hedge fund", "smoothing_risk"] == "high"
    json.loads(cmp.to_json())


def test_compare_common_period_keeps_benchmark_scale() -> None:
    """A percent benchmark must not be re-read as decimals in the common-period analysis."""
    rng = np.random.default_rng(0)
    idx = pd.date_range("2018-01-31", periods=72, freq="ME")
    bench_pct = pd.Series(rng.normal(0.8, 4.0, 72), index=idx, name="Index")
    a = pd.Series(0.2 * bench_pct.to_numpy() / 100 + rng.normal(0.002, 0.01, 72), index=idx)
    b = pd.Series(rng.normal(0.004, 0.02, 60), index=idx[12:])
    cmp = ofs.compare({"A": a, "B": b}, benchmark=bench_pct)
    assert cmp.common_period_reports is not None
    common = cmp.common_period_reports["A"]
    assert common.benchmark_input_summary is not None
    assert common.benchmark_input_summary.return_scale == "detected_percent"
    beta = common.metrics["beta"].value
    assert beta is not None
    assert beta == pytest.approx(0.2, abs=0.05)
    assert common.input_summary.return_scale == cmp.reports["A"].input_summary.return_scale
    assert "restricted to the common period" in common.input_summary.to_text()


def test_compare_dataframe_columns() -> None:
    df = pd.DataFrame(
        {"A": [0.01, 0.02, -0.01, 0.0], "B": [0.0, 0.01, 0.02, -0.01]},
        index=pd.date_range("2020-01-31", periods=4, freq="ME"),
    )
    cmp = ofs.compare(df)
    assert set(cmp.reports) == {"A", "B"}
    assert cmp.common_period_reports is None  # identical periods
    with pytest.raises(InputError):
        ofs.compare({"only": df["A"]})


def test_load_then_analyze_preserves_diagnostics() -> None:
    series = ofs.load(FIXTURES / "monthly_fund_10y.csv")
    assert isinstance(series, ofs.ReturnSeries)
    rep = ofs.analyze(series)
    assert rep.input_summary.source_type == "csv"
    assert rep.name == "monthly_fund_10y"
