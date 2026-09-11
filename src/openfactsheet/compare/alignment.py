"""Fund/benchmark alignment (decision 0012). Missing returns are never filled.

* Both dated, same regular frequency: monthly/quarterly/yearly observations are
  matched by calendar period (so month-start and month-end conventions align);
  daily/weekly by exact date. Only the intersection is used and the loss of
  observations is disclosed.
* Both dated, different frequencies: :class:`BenchmarkAlignmentError`
  (no resampling in methodology 0.1.0).
* Neither dated: aligned by position only when lengths match.
* Exactly one dated: when lengths match, the undated series is assumed to share
  the dated series' timestamps (warned); otherwise an error.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cached_property

import numpy as np
import numpy.typing as npt
import pandas as pd

from openfactsheet.exceptions import BenchmarkAlignmentError, UndefinedMetric
from openfactsheet.models.input import ObservationFrequency, ReturnSeries
from openfactsheet.models.report import BenchmarkDiagnostics

_PERIOD_CODES = {
    ObservationFrequency.MONTHLY: "M",
    ObservationFrequency.QUARTERLY: "Q",
    ObservationFrequency.YEARLY: "Y",
}


@dataclass(frozen=True)
class OLSResult:
    """CAPM-style regression ``fund = alpha + beta * benchmark + e`` (statsmodels OLS)."""

    alpha: float
    beta: float
    alpha_se: float | None
    beta_se: float | None
    alpha_t: float | None
    beta_t: float | None
    alpha_pvalue: float | None
    beta_pvalue: float | None
    r_squared: float
    residual_std: float | None
    n: int


def _finite_or_none(x: float) -> float | None:
    return float(x) if math.isfinite(float(x)) else None


@dataclass(frozen=True, eq=False)
class AlignedBenchmark:
    fund: npt.NDArray[np.float64]
    bench: npt.NDArray[np.float64]
    dates: pd.DatetimeIndex | None
    diagnostics: BenchmarkDiagnostics
    periods_per_year: float | None

    @property
    def n(self) -> int:
        return int(self.fund.shape[0])

    @cached_property
    def active(self) -> npt.NDArray[np.float64]:
        return self.fund - self.bench

    @cached_property
    def ols(self) -> OLSResult:
        if self.n < 3:
            raise UndefinedMetric("At least 3 aligned observations are required for regression.")
        if float(np.ptp(self.bench)) == 0.0:
            raise UndefinedMetric(
                "Benchmark returns are constant over the aligned periods; beta is undefined."
            )
        import statsmodels.api as sm

        x = sm.add_constant(self.bench, has_constant="add")
        fit = sm.OLS(self.fund, x).fit()
        params = np.asarray(fit.params, dtype=np.float64)
        dof = self.n - 2
        bse = np.asarray(fit.bse, dtype=np.float64) if dof > 0 else np.array([np.nan, np.nan])
        tvals = np.asarray(fit.tvalues, dtype=np.float64) if dof > 0 else np.array([np.nan, np.nan])
        pvals = np.asarray(fit.pvalues, dtype=np.float64) if dof > 0 else np.array([np.nan, np.nan])
        resid_std = math.sqrt(float(fit.ssr) / dof) if dof > 0 else math.nan
        return OLSResult(
            alpha=float(params[0]),
            beta=float(params[1]),
            alpha_se=_finite_or_none(bse[0]),
            beta_se=_finite_or_none(bse[1]),
            alpha_t=_finite_or_none(tvals[0]),
            beta_t=_finite_or_none(tvals[1]),
            alpha_pvalue=_finite_or_none(pvals[0]),
            beta_pvalue=_finite_or_none(pvals[1]),
            r_squared=float(fit.rsquared),
            residual_std=_finite_or_none(resid_std),
            n=self.n,
        )


def _keys(series: ReturnSeries, code: str | None) -> pd.Index:
    assert series.dates is not None
    if code is not None:
        return pd.Index(series.dates.to_period(code))
    return pd.Index(series.dates.normalize())


def _fmt(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%d")


def align_benchmark(fund: ReturnSeries, bench: ReturnSeries) -> AlignedBenchmark:
    warnings: list[str] = []
    fr, br = fund.values, bench.values

    if fund.dates is not None and bench.dates is not None:
        f_freq, b_freq = fund.frequency, bench.frequency
        if f_freq.is_regular and b_freq.is_regular and f_freq != b_freq:
            raise BenchmarkAlignmentError(
                f"Fund is {f_freq.value} but benchmark is {b_freq.value}. OpenFactsheet does not "
                "resample returns in methodology 0.1.0; supply a benchmark at the fund's frequency."
            )
        # One key type for both series: the calendar period of whichever series has a
        # period-based frequency (the other may be irregular because of gaps).
        period_freq = f_freq if f_freq in _PERIOD_CODES else b_freq
        code = _PERIOD_CODES.get(period_freq)
        fk, bk = _keys(fund, code), _keys(bench, code)
        if fk.has_duplicates or bk.has_duplicates:
            raise BenchmarkAlignmentError(
                "Several observations fall in the same calendar period; they cannot be aligned "
                "by period without choosing between them."
            )
        common = fk.intersection(bk)
        f_pos = fk.get_indexer(common)
        b_pos = bk.get_indexer(common)
        order = np.argsort(f_pos)
        f_pos, b_pos = f_pos[order], b_pos[order]
        dates = pd.DatetimeIndex(fund.dates[f_pos])
        method = f"calendar {period_freq.value} period" if code is not None else "exact date"
        aligned_f, aligned_b = fr[f_pos], br[b_pos]
    elif fund.dates is None and bench.dates is None:
        if fund.n != bench.n:
            raise BenchmarkAlignmentError(
                f"Undated fund ({fund.n} observations) and benchmark ({bench.n}) have different "
                "lengths; supply dates so they can be aligned explicitly."
            )
        dates = None
        method = "by position (both series undated)"
        aligned_f, aligned_b = fr, br
        warnings.append(
            "Neither series has dates; observations were paired by position. Verify that both "
            "cover exactly the same periods."
        )
    else:
        if fund.n != bench.n:
            raise BenchmarkAlignmentError(
                "Only one of fund and benchmark has dates and their lengths differ; supply dates "
                "for both."
            )
        dates = fund.dates if fund.dates is not None else bench.dates
        undated = "benchmark" if bench.dates is None else "fund"
        method = f"by position ({undated} undated; assumed to share the other series' dates)"
        aligned_f, aligned_b = fr, br
        warnings.append(
            f"The {undated} series has no dates; it was assumed to cover the same periods."
        )

    n_aligned = int(aligned_f.shape[0])
    if n_aligned < fund.n:
        warnings.append(
            f"{fund.n - n_aligned} fund observation(s) have no matching benchmark return and are "
            "excluded from benchmark-relative metrics (never filled)."
        )
    if n_aligned == 0:
        warnings.append("Fund and benchmark have no periods in common.")

    diag = BenchmarkDiagnostics(
        name=bench.name,
        fund_observations=fund.n,
        benchmark_observations=bench.n,
        aligned_observations=n_aligned,
        fund_only_periods=fund.n - n_aligned,
        benchmark_only_periods=bench.n - n_aligned,
        overlap_start=_fmt(dates[0]) if dates is not None and n_aligned else None,
        overlap_end=_fmt(dates[-1]) if dates is not None and n_aligned else None,
        alignment_method=method,
        warnings=tuple(warnings),
    )
    return AlignedBenchmark(
        fund=np.array(aligned_f, dtype=np.float64),
        bench=np.array(aligned_b, dtype=np.float64),
        dates=dates,
        diagnostics=diag,
        periods_per_year=fund.periods_per_year,
    )
